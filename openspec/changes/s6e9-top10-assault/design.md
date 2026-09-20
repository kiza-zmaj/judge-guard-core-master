# Design: S6E9 Top-10 Assault Pipeline (Kaggle Cloud GPU Only)

## Context & Technical Approach
Closing the 0.00028 gap to Top 10 (0.94660) in Kaggle S6E9 requires eliminating known data-processing bugs and variance sources:
1. Fix negative-digit IEEE-754 corruption on `Annual_Income_USD` and `Daily_Commute_km`.
2. Restrict digit extraction to the true signal sources (`Annual_Income_USD` integer digits k=0..5) and raise `max_bin` to 1024.
3. Integrate Chris Deotte's latent generator formula as `base_margin` / `init_score`.
4. Run 10-Fold Stratified CV with multi-seed averaging (Seeds 42 & 101) to eliminate test estimation variance.
5. Apply deterministic boundary conditions and zero-tie ordinal ranking.
6. Generate 5 progressive submission candidates and submit sequentially via Kaggle CLI.

## Proposed Changes
- `research/kaggle_s6e9/kaggle_kernel/s6e9_kernel.py`: Complete overhaul for 10-fold multi-scale LightGBM, Lossguide XGBoost, multi-seed averaging, and physics boundaries.
- `research/kaggle_s6e9/monitor_and_submit_cloud.py`: Automated cloud poller and submission engine with JudgeGuard verification.

## Verification
- Syntax & type compilation
- Kaggle kernel push & cloud execution
- JudgeGuard 6-point submission file integrity check
- Automated sequential submission to Kaggle Leaderboard
