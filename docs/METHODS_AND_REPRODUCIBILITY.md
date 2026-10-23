# Methods and reproducibility

This is the current workflow for the Chittagong Hill Tracts (CHT) satellite soil-moisture reconstruction and forest ecohydrology context. It supersedes the archive's historical instructions.

## 1. Set up on Windows (separate from ArcGIS Pro)

Use a dedicated Python virtual environment so you do not change the ArcGIS Pro environment. The user's installed Python 3.13 may work with current wheels; some packages are version-sensitive, so create the environment and check installations before attempting an experiment. The environment actually recorded for the completed 2026-10-23 model run used scikit-learn 1.9.1 and XGBoost 3.4.1; the project requirements are not a locked environment.

Open **Command Prompt** in the cloned repository root:

```bat
python --version
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m ipykernel install --user --name cht-ecohydro --display-name "Python (CHT ecohydrology)"
.venv\Scripts\python.exe -m jupyter lab
```

In Jupyter select **Python (CHT ecohydrology)**, not the ArcGIS Pro kernel. If an install fails on Python 3.13, use a compatible Python 3.12/3.11 environment rather than modifying ArcGIS Pro.

## 2. Put your own boundary and exports in place

Create these local-only directories if absent:

```text
data/boundaries/
data/raw/gee_exports/
data/interim/
data/processed/
data/external/
```

Place your three-district shapefile at `data/boundaries/CHT_3_districts.shp`, with its accompanying `.shx`, `.dbf`, `.prj` and any `.cpg`. The field identified by `district_name_field` in `configs/study_config.json` must have the three expected district names. Do not assume that three input features are already dissolved. The boundary is not published here pending provenance/license verification.

The cloud project is configured as `axial-paratext-491911-b6`. You need valid Earth Engine authorization and access to this project, or must edit the config to use a project you control. No authentication token is stored in this repository.

## 3. Notebook sequence

| Run order | Notebook | Purpose | Dependencies / output |
|---|---|---|---|
| 1 | `00_study_area_and_boundary.ipynb` | Check district geometries, CRS and map | Boundary shapefile |
| 2 | `01_gee_connection_check.ipynb` | Authenticate and initialize Earth Engine | Authorized GEE project |
| 3 | `02_satellite_inventory.ipynb` | Inventory collections and observation counts | Earth Engine |
| 4 | `02B_smap_qa_spatial_diagnostics.ipynb` | AM/PM quality and geographic support | Earth Engine |
| 5 | `02C_smap_feasibility_and_landcover_diagnostics.ipynb` | Seasonal / terrain observation feasibility | Earlier output and Earth Engine |
| 6 | `03_data_extraction_and_quality.ipynb` | Pilot ecohydrology extraction | Earth Engine |
| 7 | `04_multiyear_forest_ecohydrology.ipynb` | 2017–2022 district-month panel | Earth Engine and local output tables |
| 8 | `05_quality_aware_forest_ecohydrology.ipynb` | Strict EVI and ET quality-support summaries | Notebook 04 tables |
| 9 | `06_quality_sensitivity_and_final_synthesis.ipynb` | Screen sensitivity, rainfall context | Notebook 04–05 tables |
| 10 | `07_full_2019_2022_production.ipynb` | Prepare/export 16 quarterly SMAP + predictor tables | Earth Engine task execution and CSV downloads |
| 11 | `08_corrected_smap_ml_experiments.ipynb` | Build QA-accepted training table, baselines, RF/XGB, tests | Exported quarterly CSV files in `data/raw/gee_exports/` |
| 12 | `09_integrated_results_and_research_story.ipynb` | Combine locked ML results with ecohydrology context | Completed 04–08 output tables |

**Important:** Notebook 07 starts Earth Engine export jobs; submission of a job does not immediately download the result to your computer. Wait for all completed tasks and place the expected 16 CSVs in `data/raw/gee_exports/` before running Notebook 08. The expected names and SHA256 checksums for the completed run are preserved in `outputs/tables/07_training_data_manifest.json`.

The completed training run's processed source was `data/processed/07_smap_ml_table.csv` (not tracked, because of size and research data stewardship). Notebook 08 records this table's SHA256 and the selected models in `outputs/tables/08_model_run_manifest.json`; if your source exports or dependencies change, do **not** expect bit-for-bit identical results. Explain differences and record new manifests.

## 4. Evaluation design

The prediction target is quality-accepted **SMAP AM retrieval**, not in-situ moisture. The analysis applies QA gates, constructs shared predictor groups, and evaluates four families:

1. Training-period overall mean and calendar-month baselines.
2. Regularized linear model (Ridge).
3. Random Forest.
4. XGBoost with climate/terrain/calendar, optional radar, optional vegetation.

The split is chronological: 2019–2020 train, 2021 validate/select, 2022 test. Reporting uses equal **date** weight when calculating error across the accepted rows. RMSE, MAE, bias and R² assess reconstruction of the satellite reference. A separate held-out-grid/future-date test checks some spatial transfer. Avoid evaluating on original QA-rejected cells as if satellite truth were known.

The model-run manifest records a date-resampled RMSE interval of approximately 0.0515–0.0592 m³/m³, but this describes **sample variation in errors against SMAP**, not a field-data confidence interval. Experimental test-band coverage also is not physical soil-moisture calibration.

## 5. Where results and figures live

- Final figures: `outputs/figures/`
- Tabular summaries and reproducibility records: `outputs/tables/`
- Integrated report: `outputs/reports/09_integrated_research_summary.md`
- Historical original experiment only: `legacy/`

Results are already published for inspection. Running everything again on your PC is **optional** unless you wish to extend the experiment, revise QA decisions or reproduce the 2026-10-23 run with the original input exports.

## 6. Research safeguards

- Preserve source polygon geometry, raw quarterly files and run manifests locally; never overwrite originals.
- Keep private credentials and unpublished boundary files out of Git.
- Cite product versions; SMAP v005 was selected for the 2019–2022 window. Do not silently swap to a newer processing version and compare metrics as if identical.
- Record git commit SHA, configuration, Python environment, raw-input SHA256 checksums and random seed for any new model run.
- Never call the model ground validated or claim a basin water balance without additional independent observations.
