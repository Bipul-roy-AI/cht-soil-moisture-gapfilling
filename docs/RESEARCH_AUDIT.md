# Scientific audit and interpretation (23 October 2026)

**Status: exploratory feasibility study, not yet externally validated or publication-ready.**
This audit distinguishes inspectable repository evidence from previous notebook outputs and untested explanations. No new model performance claims were obtained in this review.

## What is directly reproducible now

Run `python scripts/audit_availability.py`. The committed `data/smap_daily_means.csv` contains 300 consecutive calendar dates, 6 March–30 December 2021: 148 nonmissing regional daily means and 152 missing values (50.67%). The longest missing sequence is four days. `results/availability_monthly.csv` is generated directly from that file. These numbers describe **availability of a regional mean in this export**—not the fraction of missing grid cells across CHT, not the cause of missingness, and not a station-based accuracy assessment.

The legacy notebooks and README report holdout RMSE 0.0445 m³/m³ and R² 0.036, but the per-date predictor file `data/cht_temporal_with_smap.csv` is deliberately excluded from Git. The values cannot be independently reconstructed from committed data alone. Existing figures are **historical exploratory outputs** and should not be interpreted as newly revalidated figures.

## Blocking methodological findings

1. **Invalid test isolation.** `Project_1.ipynb` cells 33, 37 and 43 use `(X_test, y_test)` as XGBoost's `eval_set` while early stopping is active, and then report performance on that same test. Selection leaks test labels. Use a distinct chronological validation period for early stopping; score the test period once. The new `scripts/evaluate_temporal.py` implements this separation.
2. **Wrong collection for 2021.** Legacy notebooks request `NASA/SMAP/SPL3SMP_E/006` in 2021. The current Google Earth Engine catalog states data before 4 December 2023 belong to `NASA/SMAP/SPL3SMP_E/005`. A fresh 2021 Earth Engine extraction should use `/005` and record the retrieved product version, processing date and quality filtering. The enhanced SMAP product is **9-km gridded**; this is not 9-km independent information because the underlying L-band radiometer footprint is substantially coarser. Do not label it simply 36-km grid resolution.
3. **Non-independent spatial pseudo-replication.** The legacy pixel-level model joins the same regional daily SMAP mean to many sampled pixels per day (`Project_1.ipynb` cell 36). A per-pixel test RMSE in this setup does not validate pixel-scale soil moisture. Evaluate one mean prediction per *held-out date*, or rebuild true footprint-aligned pixel targets and use spatially grouped tests.
4. **Feature misidentification.** Cell 42 renames `NDVI` to `EVI` without computing EVI; cell 41 defines an EVI collection but does not redo the upstream CSV export. Treat old exported values as NDVI. Re-export if genuine EVI is required. The new evaluator preserves the actual feature name.
5. **SAR ratio issue.** Earth Engine `COPERNICUS/S1_GRD` VV and VH values are in dB. Directly dividing dB-valued VH by VV (cells 13, 24, 41) is not the linear-power VH/VV ratio. A difference (`VH_dB - VV_dB`) expresses the log power ratio and is computed in the evaluator; `VHVV` is excluded. Averaging dB values is not equivalent to averaging linear backscatter power.
6. **No proof of RFI dominance.** Fairly stable missingness across months cannot by itself diagnose radio-frequency interference; revisit, quality screening, precipitation/vegetation effects and sampling also matter. Check SMAP RFI and retrieval-quality flags explicitly against calendar availability before attributing causes.
7. **No demonstrated canopy mechanism.** Low model feature importance or small SHAP values for SAR show low *model use*, not that attenuation caused low skill. SAR information gain must be tested against an identical no-SAR model and preferably stratified by vegetation and acquisition lag. Sentinel-1 acquisition availability, slope and residual terrain effects require checks.
8. **Invalid accuracy benchmark.** Comparing model-to-SMAP RMSE to a purported ESA CCI `0.05 m³/m³` operational target does not establish accuracy. The SMAP mission `0.04 m³/m³` requirement concerns comparison to independent in-situ reference under its defined valid conditions and an unbiased error statistic, not reconstruction of its own product.
9. **Uncertainty mischaracterized.** Plots using `predicted ± holdout RMSE` are *not* calibrated prediction intervals or pixel-level uncertainty maps. Remove uncertainty language or replace with out-of-fold residual calibration, blocked bootstrap, and coverage diagnostics.
10. **Spatial and temporal scope.** The AOI is a rectangle `[91.6,21.5,92.6,23.8]`, not a verified administrative Chittagong Hill Tracts polygon or a dense-evergreen-forest mask. Only March–December 2021 is represented. Avoid generalizing to all CHT forests or other years without a validated forest mask and multi-year assessment.

## Supported conclusion versus hypothesis

| Existing statement | Scientifically defensible wording today |
| --- | --- |
| "RFI causes 50.7% missingness" | "50.7% of this recorded daily series is missing; the mechanisms require quality-flag analysis." |
| "SAR contributes only 15%" | "A previous model's reported feature-importance allocation is about 15%; incremental predictive skill is not established." |
| "C-band is physically unable to recover the signal" | "Dense canopy and topography plausibly limit C-band sensitivity; the mechanism is not isolated by this experiment." |
| "RMSE passes ESA operational accuracy" | "The reported RMSE is an agreement metric relative to SMAP, not independent surface-soil-moisture accuracy." |
| "Complete daily SMAP product" | "Exploratory reconstructions at regional-mean scale, conditional on predictor coverage and model validity." |

## Practical publication readiness criteria

- [ ] Regenerate predictors and targets from one documented, correct product version and explicit pixel-quality masks, saving a compact analysis-ready *daily* table with provenance, timestamps, units, footprint definitions and missing-feature flags.
- [ ] Verify 9-km grid / coarse footprint treatment; use a proper CHT polygon, forest-cover fractions and forest versus nonforest analysis.
- [ ] Run chronological train/validation/test and forward-chaining tests across multiple years; report effective independent **days** (not pixel-row counts), baseline skill, bias, MAE, RMSE, ubRMSE and R² with block-bootstrap uncertainty.
- [ ] Compare train-median, seasonal/climatological, persistence or water-balance baseline, ERA5-only, no-SAR and full-SAR models under exactly matching folds and availability masks.
- [ ] Analyze missing-not-at-random conditions using retrieval-quality, RFI, vegetation-water-content, freeze/water and observation-support flags rather than assuming the physical cause.
- [ ] Run data ablations for Sentinel-1 (including incidence angle, acquisition age, ascending/descending orbit and terrain-corrected alternatives) and sensitivity to 7-day precipitation and temporal windows.
- [ ] Run artificial-gap tests on observed SMAP dates with gap masks modeled on real missingness; distinguish these from real unseen gap predictions. Validate independently with ISMN/field probes where available, or label as SMAP-consistency validation only.
- [ ] Store versioned result tables, dated environment details, figures with captions, uncertainty assessment, and a machine-readable reference list. Evaluate 2021 versus recent missions/data separately.

## Peer-reviewed related work and official documentation

1. Zhang, C., et al. (2025). *Global-scale gap filling of satellite soil moisture products: Methods and validation*. **Journal of Hydrology, 653**, 132762. https://doi.org/10.1016/j.jhydrol.2025.132762 — original inspiration, primarily ERA5-based global bias correction / Random Forest comparisons; this repository is not a direct replication.
2. Mao, H., Kathuria, D., Duffield, N., & Mohanty, B. P. (2019). *Gap filling of high-resolution soil moisture for SMAP/Sentinel-1: A two-layer machine learning-based framework*. **Water Resources Research, 55**, 6986–7009. https://doi.org/10.1029/2019WR024902 — sensor-fusion and withheld-observation framework; [authors' code](https://github.com/HannaMao/Gap-Filling-of-Soil-Moisture).
3. Beale, K., Bras, R. L., & Romberg, J. (2025). *Low-rank gap filling and downscaling for SMAP soil moisture datasets*. **Ecohydrology, 18**, e70024. https://doi.org/10.1002/eco.70024 — empirical-orthogonal-function/low-rank alternative and validation; [code](https://github.com/excz/LowRankDownscalingSMAP).
4. Zhang, R., Kim, S., & Kim, H.-M. (2023). *Temporal gap-filling of 12-hourly SMAP soil moisture over the CONUS using water balance budgeting*. **Water Resources Research**. https://doi.org/10.1029/2023WR034457 — process-based baseline and independent validation; applicability to CHT requires testing.
5. [Google Earth Engine SMAP `/005` product catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL3SMP_E_005) and [`/006` catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL3SMP_E_006) — product date coverage and enhanced 9-km grid.
6. [NSIDC enhanced SMAP user guide](https://nsidc.org/sites/default/files/spl3smp_e-v005-userguide.pdf) and [SMAP product quality flags](https://nsidc.org/data/user-resources/help-center/how-do-i-interpret-surface-and-quality-flag-information-level-2-and-3-passive-soil-moisture-products).
7. [Earth Engine Sentinel-1 guidance](https://developers.google.com/earth-engine/guides/sentinel1) — dB backscatter and processing; [NASA SMAP algorithm basis](https://nsidc.org/sites/default/files/l2_sm_p_atbd_rev_g_final_oct2021_0.pdf) — science requirements and dense vegetation.
8. [NASA NISAR mission](https://science.nasa.gov/mission/nisar/) — NISAR launched in July 2025, with provisional L-band science data released in July 2026. Treat new L-band measurements as a **future comparison for this 2021 experiment**, not an unlaunched mission or a guaranteed soil-moisture solution.

### Study classification

At present: **unreviewed computational feasibility study**. It is suitable for a transparent research portfolio with clear caveats, a technical methods note, or a preregistered extension. A journal manuscript would require re-extraction and independent/robust validation before claiming soil-moisture retrieval accuracy, gap mechanisms or causal canopy effects.
