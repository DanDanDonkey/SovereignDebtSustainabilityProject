# Sovereign Debt Sustainability Analysis

Interactive dashboard for analyzing government debt trajectories using a calibrated debt dynamics model with Monte Carlo simulation.

**[Live Demo →](https://dantedorr.github.io/sovereign-dsa/)**

## Overview

This tool projects sovereign debt/GDP ratios under different fiscal scenarios, following the IMF's Debt Sustainability Analysis framework used in Article IV consultations.

### Features

- **27 countries** across Developed, EM Investment Grade, EM High Yield, and Frontier markets
- **Monte Carlo simulation**: 500 paths with stochastic macro shocks
- **Regime-switching dynamics**: Interest rates respond endogenously to debt levels
- **Reform scenarios**: Compare baseline vs. gradual/moderate/aggressive fiscal adjustment
- **Key metrics**: Debt-stabilizing primary balance, fiscal gap, 10-year projections

## Methodology

### Debt Dynamics Equation

```
dₜ = dₜ₋₁ × (1 + r) / (1 + g) − pb
```

Where:
- `d` = debt-to-GDP ratio
- `r` = effective interest rate (regime-dependent)
- `g` = nominal GDP growth
- `pb` = primary balance

### Monte Carlo Simulation

The model runs 500 simulations with stochastic shocks:
- **Growth**: Mean-reverting around baseline, volatility calibrated by country type
- **Inflation**: Mean-reverting, higher volatility for EM/Frontier
- **Primary balance**: Mean-reverting with fiscal shock uncertainty

Uncertainty bands show the 10th-90th percentile range across simulations.

### Regime Switching

Countries transition between three regimes based on debt thresholds:

| Regime | Characteristics |
|--------|-----------------|
| Low Debt | Base interest rate, no growth penalty |
| Medium Debt | Rising risk premium |
| High Debt | Elevated rates, growth drag, forced fiscal adjustment |

## Calibration Sources

All parameters are calibrated from empirical literature, not estimated from country-specific data.

### Debt Thresholds

| Classification | Warning | Critical | Source |
|---------------|---------|----------|--------|
| Developed | 90% | 120% | Maastricht (60%), R&R literature (90%) |
| EM Investment Grade | 55% | 70% | IMF LIC-DSF "strong" capacity |
| EM High Yield | 40% | 55% | IMF LIC-DSF "medium" capacity |
| Frontier | 35% | 55% | IMF LIC-DSF "weak/medium" |

**Note**: The IMF SRDSF (2022) explicitly moved away from fixed thresholds to continuous risk metrics. These are used as conventional benchmarks.

### Interest Rate Sensitivity

| Source | Finding |
|--------|---------|
| Baldacci & Kumar (2010) | ~1.7 bps per 1pp debt/GDP for advanced G20 |
| Hausmann et al. (Harvard) | ~20 bps per 10pp debt/GDP for emerging markets |
| Ben Salem & Castelletti (2016) | Higher sensitivity during stress periods |

### Volatility (Standard Deviations)

Calculated from IMF WEO historical data (2000-2024):

| Category | Growth σ | Inflation σ | PB σ |
|----------|----------|-------------|------|
| Developed | 1.8% | 1.2% | 1.5% |
| EM IG | 2.8% | 2.5% | 1.8% |
| EM HY | 3.5% | 6.0% | 2.2% |
| Frontier | 3.2% | 5.0% | 2.0% |

## Data Sources

- **IMF World Economic Outlook** (October 2024) - Macro data
- **IMF LIC-DSF Guidance Note** (2018) - Threshold calibration
- **IMF SRDSF Staff Guidance** (2022) - Framework methodology

## Limitations

- Regime thresholds and interest rates are **calibrated**, not estimated from data
- Volatility parameters based on historical averages by country group
- No modeling of debt currency composition or rollover risk
- Does not capture tail events, sudden stops, or contagion
- Japan requires special treatment due to unique institutional factors
- Mean reversion speed and growth-debt feedback are modeling choices

## Local Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Deployment

### Vercel (Recommended)

Just connect the repo at vercel.com - it auto-detects Vite and deploys.

### GitHub Pages

1. Update `base` in `vite.config.js` to match your repo name
2. Build: `npm run build`
3. Deploy `dist/` folder to `gh-pages` branch

## References

- Baldacci, E. & Kumar, M. (2010). "Fiscal Deficits, Public Debt, and Sovereign Bond Yields." IMF Working Paper 10/184.
- Ben Salem, M. & Castelletti, B. (2016). "Determinants of sovereign bond yields." CEPR VoxEU.
- Blanchard, O. (2019). "Public Debt and Low Interest Rates." AER.
- Hausmann, R. et al. (2023). "Debt Levels, Debt Composition, and Sovereign Spreads." Harvard CID.
- IMF (2018). "Guidance Note on the Bank-Fund Debt Sustainability Framework for Low Income Countries."
- IMF (2022). "Staff Guidance Note on the Sovereign Risk and Debt Sustainability Framework."
- Reinhart, C. & Rogoff, K. (2010). "Growth in a Time of Debt." AER (thresholds disputed).

## License

MIT

---

*Built for educational purposes. Not financial advice.*
