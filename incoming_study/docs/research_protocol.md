# Research protocol — proposal, not frozen

## Working question

How accurately can missing SMAP observations over the three Chittagong Hill Tracts districts be reconstructed from remotely sensed and meteorological predictors, and what seasonal/forest-related patterns are visible in the observed and reconstructed records?

## Study region

Bandarban, Khagrachhari, and Rangamati. Maintain their individual features for district summaries and dissolve them in-memory for a regional area of interest. Verify polygon topology, area and boundary source/license.

## Initial period

2017-01-01 through 2022-12-31, subject to initial data inventory. Historical SMAP enhanced L3 `/005` only within this first period; newer `/006` data require a separately evaluated version transition.

## Target

QA-passing SMAP AM surface-soil-moisture observations at the *enhanced product's native grid posting*, not independent ground soil moisture. Preserve grid IDs, validity flags, original raw values and acquisition dates.

## Planned predictor groups

1. Climate plus terrain: rainfall histories, meteorological conditions, elevation, slope and aspect.
2. Add vegetation/forest context: vegetation indices, LAI and forest fraction.
3. Add Sentinel-1, only after orbit/angle/terrain QA and a feature-group ablation test.

All feature timestamp rules must be declared before extraction. A retrospective gap reconstruction may use data available after the hidden timestamp; a causal/past-only analysis may not. Do not mix the two information sets in model comparisons.

## Planned evaluation

- Compare persistence, climatology, meteorological-only, Random Forest, and XGBoost.
- Separate time-blocked train/validation/calibration/test periods.
- Report MAE, RMSE, bias, R2, coverage, and seasonal behavior.
- Artificially hide measured SMAP blocks (for example 1, 3, 7, 14 days) to evaluate gap reconstruction; compare methods only on common test locations/dates.
- Group correlated neighboring SMAP grid cells cautiously; enhanced grid spacing is not the physical footprint resolution. Only use a spatial holdout where scientifically feasible.
- Record performance stratified by wet/dry season, forest fraction and terrain category.

## Forest ecohydrology scope

Describe rainfall–observed SMAP lag, seasonal moisture persistence, vegetation associations, terrain gradients and evapotranspiration-product context. Mark analyses using filled values separately. Never interpret associations as causal forest impacts without independent supporting evidence.

## Mandatory stopping point

Remote sensing cannot independently verify physical field-scale soil-water content, interception, throughfall, infiltration, root-zone storage, transpiration fluxes, recharge, or runoff. These claims require appropriately matched in-situ observations or independent validation. Do not publish unsupported claims.

## To decide before full processing

- Geometry validity, area, footprint overlap and observational counts.
- SMAP QA and missingness inclusion rules.
- Sentinel-1 orbit and radiometric terrain-treatment strategy.
- Exact split dates, feature timing and missing-gap simulation design.
- Data access/source citation licenses and Earth Engine compute feasibility.
