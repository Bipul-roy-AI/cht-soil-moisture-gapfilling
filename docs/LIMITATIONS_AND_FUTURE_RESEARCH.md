# Limitations and future research agenda

## What is finished

The project has completed a satellite-derived data inventory; SMAP quality/availability diagnostics; 2017–2022 forest ecohydrology product-support review; a 2019–2022 SMAP feature/target export; and temporal plus limited geographic evaluation of baselines, Random Forest and XGBoost. The selected experiment has a locked 2022 test record and supporting data manifests.

**The evidence supports reconstruction of held-out, QA-accepted SMAP retrievals, not verification of true soil moisture.** This distinction should accompany every result excerpt, portfolio summary or presentation.

## Major constraints and how to improve them

| Constraint in present study | Scientific consequence | Future improvement |
|---|---|---|
| Only 17,653/248,400 sampled posting-dates QA accepted | Training/evaluation are highly selected by product QA and time/location | Document QA failure modes and sample across seasons, topography and cover |
| Accepted records from 39 SMAP grid postings | Limited spatial diversity; 9-km posts not sensor-independent footprints | Use footprint-aware predictor aggregation and independent geographic blocks |
| Evaluation target is SMAP itself | Model may reproduce a biased retrieval; no absolute physical accuracy estimate | Place calibrated probes at stratified 0–5 cm field sites near satellite overpasses |
| Test year restricted to 2022 | Future climate/land-cover transfer uncertain | Out-of-period and out-of-region blind evaluation; updated-product sensitivity |
| Sentinel-1 can respond to slope, geometry and vegetation | Predictive value is not proof of a moisture mechanism | Terrain/angle normalization studies, physics-informed interpretation and field observations |
| Joint wet-season EVI/ET coverage low and QA-screen sensitive | Cannot distinguish biological change from missing/unsupported observations reliably | Multi-sensor optical compositing, field canopy/ET monitoring and robust gap-sensitivity analysis |
| CHIRPS gridded rainfall lacks local evaluation here | District means may have local biases in mountainous terrain | Check rain gauges and elevation-dependent rainfall errors |
| MOD16 ET is modeled with uneven algorithm support | Cannot infer independent ET flux or forest water balance | Eddy-covariance, sap-flow or independent flux references |
| Source shapefile provenance/license unconfirmed | Public redistribution is inappropriate | Obtain officially documented boundary or permission, record original CRS/source |
| Early original notebook not re-evaluated under identical QA/splits | Historical accuracy figures cannot be compared directly to corrected scores | Run both methods on the same accepted inputs, splits and metrics |

## Minimum requirements before a stronger claim

1. **Independent, spatially distributed field moisture observations**, with instrument depth and acquisition times documented.
2. **Independent validation of the SMAP product itself**, so disagreement can be separated into retrieval, representation and prediction errors.
3. **Spatially blocked and temporally independent evaluation** that includes hard landscape conditions and uncertainty calibration.
4. **Appropriate scale handling** between fine radar/terrain predictors, grid postings and the broader microwave sensor support.
5. For forest-water questions, **measured rainfall and vegetation/water-flux observations**, not solely modeled satellite products.

Until these are collected, the project is ready for a transparent academic portfolio entry describing *satellite-product gap-reconstruction feasibility* and *quality-aware forest ecohydrology context*—not as a fully validated forest soil-moisture map or causal ecohydrological discovery.
