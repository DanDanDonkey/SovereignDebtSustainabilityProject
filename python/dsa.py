"""
Debt Sustainability Analysis System
====================================
Reads country data from country_data.json

Usage:
    python dsa.py                        # List countries
    python dsa.py brazil                 # Single country
    python dsa.py brazil moderate        # With reform
    python dsa.py all                    # All countries
    python dsa.py category em_hy         # By category
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import os
import warnings
warnings.filterwarnings('ignore')

# Load data
DATA_FILE = os.path.join(os.path.dirname(__file__), 'country_data.json')
with open(DATA_FILE, 'r') as f:
    DATA = json.load(f)

REFORM_SCENARIOS = {
    'none': {'pb_improvement': 0.0, 'growth_boost': 0.0, 'rate_reduction': 0.0, 'name': 'No change'},
    'mild': {'pb_improvement': 0.75, 'growth_boost': 0.15, 'rate_reduction': 0.5, 'name': 'Gradual'},
    'moderate': {'pb_improvement': 1.5, 'growth_boost': 0.0, 'rate_reduction': 1.0, 'name': 'Significant'},
    'aggressive': {'pb_improvement': 2.5, 'growth_boost': -0.2, 'rate_reduction': 1.5, 'name': 'Major reform'},
}


def list_countries():
    """List all available countries by category."""
    print("\nAvailable countries:")
    for cat, countries in DATA['categories'].items():
        print(f"\n  {cat.upper()}:")
        print(f"    {', '.join(countries)}")
    return list(DATA['countries'].keys())


def get_country_data(country: str) -> Optional[pd.DataFrame]:
    """Load data for a country."""
    if country not in DATA['countries']:
        print(f"Country '{country}' not found.")
        return None
    
    raw = DATA['countries'][country]
    df = pd.DataFrame.from_dict(raw, orient='index')
    df.index = df.index.astype(int)
    df.index.name = 'year'
    df = df.sort_index()
    df['nominal_growth'] = ((1 + df['gdp_growth']/100) * (1 + df['inflation']/100) - 1) * 100
    return df


def get_regime_params(country: str) -> Dict:
    """Get regime parameters for a country based on classification."""
    classification = DATA['classifications'].get(country, 'em_ig')
    return DATA['regime_params'][classification]


def estimate_bvar(data: pd.DataFrame, lags: int = 1, lambda1: float = 0.1) -> Dict:
    """Estimate Bayesian VAR with Minnesota prior."""
    var_data = data[['gdp_growth', 'inflation', 'primary_balance']].dropna()
    var_data = var_data.rename(columns={'gdp_growth': 'growth', 'primary_balance': 'pb'})
    
    T, K = var_data.shape
    Y = var_data.values
    Y_reg = Y[lags:]
    T_eff = len(Y_reg)
    
    X = np.ones((T_eff, 1))
    for lag in range(1, lags + 1):
        X = np.hstack([X, Y[lags - lag : T - lag]])
    
    n_reg = 1 + K * lags
    beta_ols = np.linalg.lstsq(X, Y_reg, rcond=None)[0]
    resid = Y_reg - X @ beta_ols
    sigma_ols = np.std(resid, axis=0)
    
    # Prior
    beta_prior = np.zeros((n_reg, K))
    for i in range(K):
        beta_prior[1 + i, i] = 1.0
    
    prior_prec = np.zeros((n_reg, K))
    prior_prec[0, :] = 1e-6
    for lag in range(1, lags + 1):
        for j in range(K):
            for i in range(K):
                idx = 1 + (lag - 1) * K + j
                var = (lambda1 / lag) ** 2 if i == j else (lambda1 * 0.5 * sigma_ols[i] / (lag * sigma_ols[j])) ** 2
                prior_prec[idx, i] = 1.0 / var if var > 0 else 1e-6
    
    # Posterior
    beta_post = np.zeros((n_reg, K))
    for i in range(K):
        V_prior_inv = np.diag(prior_prec[:, i])
        V_data_inv = (X.T @ X) / (sigma_ols[i] ** 2)
        V_post = np.linalg.inv(V_prior_inv + V_data_inv)
        beta_post[:, i] = V_post @ (V_prior_inv @ beta_prior[:, i] + (X.T @ Y_reg[:, i]) / (sigma_ols[i] ** 2))
    
    sigma_post = np.cov((Y_reg - X @ beta_post).T)
    if sigma_post.ndim == 0:
        sigma_post = np.array([[sigma_post]])
    
    return {'coef': beta_post, 'sigma': sigma_post, 'data': var_data, 'lags': lags}


def simulate(bvar: Dict, debt0: float, country: str, years: int = 10, n_sims: int = 1000, reform: str = 'none') -> Dict:
    """Run regime-switching simulation."""
    np.random.seed(42)
    
    params = get_regime_params(country)
    ref = REFORM_SCENARIOS.get(reform, REFORM_SCENARIOS['none'])
    
    coef, sigma = bvar['coef'], bvar['sigma']
    data = bvar['data'].values
    lags = bvar['lags']
    K = 3  # growth, inflation, pb
    
    t_low, t_high = params['debt_thresholds']
    base_r = params['base_rates']
    r_sens = params['rate_sensitivity']
    g_adj = params['growth_adj']
    
    try:
        chol = np.linalg.cholesky(sigma * 0.35)
    except:
        chol = np.diag(np.sqrt(np.diag(sigma) * 0.35))
    
    init_macro = data[-lags:]
    debt_paths = np.zeros((n_sims, years + 1))
    debt_paths[:, 0] = debt0
    
    for sim in range(n_sims):
        macro = np.zeros((lags + years, K))
        macro[:lags] = init_macro
        debt = debt0
        
        for t in range(years):
            regime = 0 if debt < t_low else (1 if debt < t_high else 2)
            
            x = np.concatenate([[1.0], macro[lags + t - 1]])
            new = x @ coef + chol @ np.random.randn(K)
            
            new[0] = np.clip(new[0] + g_adj[regime] + ref['growth_boost'], -8, 12)
            new[1] = np.clip(new[1], 0, 60)
            reform_eff = ref['pb_improvement'] * min(t + 1, 7) / 7
            new[2] = np.clip(new[2] + reform_eff + (0.3 if regime == 2 else 0), -12, 8)
            macro[lags + t] = new
            
            r = (base_r[regime] - ref['rate_reduction'] * min(t + 1, 4) / 4 + max(0, (debt - t_low) * r_sens[regime])) / 100
            r = max(0.015, r)
            g = (1 + new[0]/100) * (1 + new[1]/100) - 1
            pb = new[2] / 100
            
            debt = max(0, min(250, (debt/100 * (1 + r) / (1 + g) - pb) * 100))
            debt_paths[sim, t + 1] = debt
    
    final = debt_paths[:, -1]
    pcts = {f'p{p}': np.percentile(debt_paths, p, axis=0) for p in [5, 10, 25, 50, 75, 90, 95]}
    
    return {
        'summary': pd.DataFrame({'year': range(years + 1), **pcts}),
        'p_above_100': np.mean(final > 100) * 100,
        'p_above_150': np.mean(final > 150) * 100,
        'p_high': np.mean(final > t_high) * 100,
        'thresholds': (t_low, t_high),
    }


def run_analysis(country: str, reform: str = 'none', show: bool = True):
    """Run full DSA for a country."""
    print(f"\n{'='*50}")
    print(f"{country.upper()} - {REFORM_SCENARIOS.get(reform, {}).get('name', reform)}")
    print('='*50)
    
    data = get_country_data(country)
    if data is None:
        return None
    
    print(f"Data: {len(data)} years ({data.index.min()}-{data.index.max()})")
    
    bvar = estimate_bvar(data)
    debt0 = data['debt_gdp'].iloc[-1]
    
    result = simulate(bvar, debt0, country, reform=reform)
    
    t_low, t_high = result['thresholds']
    print(f"\nInitial debt: {debt0:.1f}%")
    print(f"Thresholds: {t_low}% / {t_high}%")
    print(f"\nAfter 10 years:")
    print(f"  Median: {result['summary']['p50'].iloc[-1]:.1f}%")
    print(f"  90% CI: [{result['summary']['p5'].iloc[-1]:.1f}%, {result['summary']['p95'].iloc[-1]:.1f}%]")
    print(f"\nProbabilities:")
    print(f"  P(>{t_high}%): {result['p_high']:.0f}%")
    print(f"  P(>100%): {result['p_above_100']:.0f}%")
    print(f"  P(>150%): {result['p_above_150']:.0f}%")
    
    if show:
        plot_results(result, country, reform, debt0)
    
    return {'country': country, 'debt0': debt0, 'result': result}


def plot_results(result: Dict, country: str, reform: str, debt0: float):
    """Plot fan chart."""
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(11, 6))
    s = result['summary']
    x = range(2024, 2024 + len(s))
    
    ax.fill_between(x, s['p5'], s['p95'], alpha=0.2, color='steelblue')
    ax.fill_between(x, s['p10'], s['p90'], alpha=0.3, color='steelblue')
    ax.fill_between(x, s['p25'], s['p75'], alpha=0.4, color='steelblue')
    ax.plot(x, s['p50'], 'b-', lw=2.5, label='Median')
    
    t_low, t_high = result['thresholds']
    ax.axhline(t_high, color='red', ls=':', lw=2, alpha=0.7)
    ax.axhline(t_low, color='orange', ls=':', lw=2, alpha=0.7)
    
    title = f"{country.title()}: Debt Sustainability"
    if reform != 'none':
        title += f" ({REFORM_SCENARIOS[reform]['name']})"
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Debt (% GDP)')
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    txt = f"P(>{t_high}%): {result['p_high']:.0f}%\nP(>100%): {result['p_above_100']:.0f}%"
    ax.text(0.98, 0.05, txt, transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round', fc='white', alpha=0.9))
    
    plt.tight_layout()
    os.makedirs('output', exist_ok=True)
    fig.savefig(f'output/{country}_{reform}.png', dpi=150)
    print(f"Saved: output/{country}_{reform}.png")
    plt.close()


def run_all(category: str = None):
    """Run all countries (optionally filtered by category)."""
    if category and category in DATA['categories']:
        countries = DATA['categories'][category]
    else:
        countries = list(DATA['countries'].keys())
    
    results = []
    for c in countries:
        r = run_analysis(c, show=True)
        if r:
            res = r['result']
            results.append({
                'Country': c.title(),
                'Category': DATA['classifications'].get(c, ''),
                'Debt0': round(r['debt0'], 0),
                'Median': round(res['summary']['p50'].iloc[-1], 0),
                'P(>100%)': round(res['p_above_100'], 0),
            })
    
    df = pd.DataFrame(results).sort_values('P(>100%)', ascending=False)
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(df.to_string(index=False))
    df.to_csv('output/summary.csv', index=False)
    return df


def compare_reforms(country: str):
    """Compare reform scenarios for a country."""
    results = []
    for ref in REFORM_SCENARIOS:
        r = run_analysis(country, reform=ref, show=True)
        if r:
            results.append({
                'Scenario': REFORM_SCENARIOS[ref]['name'],
                'Median': round(r['result']['summary']['p50'].iloc[-1], 0),
                'P(>100%)': round(r['result']['p_above_100'], 0),
            })
    
    print("\n" + "="*50)
    print(f"{country.upper()}: REFORM COMPARISON")
    print("="*50)
    print(pd.DataFrame(results).to_string(index=False))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        list_countries()
        print("\nUsage: python dsa.py <country> [reform]")
        print("       python dsa.py all")
        print("       python dsa.py category <em_hy|em_ig|developed|frontier>")
    elif sys.argv[1] == 'all':
        run_all()
    elif sys.argv[1] == 'category' and len(sys.argv) > 2:
        run_all(sys.argv[2])
    elif sys.argv[1] == 'reforms' and len(sys.argv) > 2:
        compare_reforms(sys.argv[2])
    else:
        country = sys.argv[1]
        reform = sys.argv[2] if len(sys.argv) > 2 else 'none'
        if reform == 'all':
            compare_reforms(country)
        else:
            run_analysis(country, reform)
