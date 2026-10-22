# Run the revised study

All real-data notebooks can run in **Google Colab**. Satellite processing executes on **Earth Engine**, and tabular model fitting executes in Colab. A CPU runtime is sufficient to start; GPU XGBoost is optional and has not been verified in this authoring environment. Random Forest uses CPU.

## First action: a small real pilot

Open [notebook 01 in Colab](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/01_gee_inventory_and_pilot_export.ipynb). The setup cell clones the research branch and installs the helper package. Authorize your own Earth Engine account. The non-secret Cloud project ID defaults to `gee-projects-475506`, as in your original notebook; replace it if needed. Never share passwords, tokens, or service-account keys.

The inventory checks actual SMAP coverage, resolves district names, lists the target grid and available relative orbits. Set `RELATIVE_ORBIT` to one of the listed integer orbit numbers and inspect coverage. Set `START_PILOT_EXPORT=True` to launch a **four-cell, seven-day pilot**. This is a software/data-feasibility sample, not a representative ecological sample.

Watch the task at <https://code.earthengine.google.com/tasks>. Find the completed CSV in Drive's `CHT_SM_v2_exports` folder. Use notebook 03's pilot section to inspect it. Before scaling up, confirm plausible target/predictor values, QA meanings, acquisition metadata, actual EVI, both raw/RTC radar and nonzero useful support. A successful task alone does not establish scientific data quality.

## Notebook order

| Notebook | Purpose | Where and prerequisites |
|---|---|---|
| `00_offline_software_check.ipynb` | Check training, calibration, freeze, evaluation and gap tests using explicitly fictional arrays | Colab or local CPU; no GEE account needed |
| `01_gee_inventory_and_pilot_export.ipynb` | Verify product/date/grid/districts; choose orbit; launch pilot | Colab + authorized GEE account |
| `02_gee_multiyear_export.ipynb` | Submit resumable batches of monthly full-data tasks | Colab + GEE; pilot must succeed first |
| `03_data_audit_and_freeze.ipynb` | Audit real rows, QA, coverage and support; write analysis protocol | Colab CPU; pilot/full CSVs from Drive |
| `04_colab_training.ipynb` | Train baselines and RF/XGBoost sensor ablations, select on validation, calibrate separately | Colab CPU or compatible optional GPU; complete full export |
| `05_locked_evaluation_and_gap_tests.ipynb` | Final metrics, artificial-gap tests, subgroup/paired comparisons and flagged reconstruction | Frozen completed run; explicitly enable final testing |
| `06_optional_spatial_transfer.ipynb` | Predeclared joint new-place/new-year experiment with approximate 35 km buffer | Choose geography before test inspection; can be infeasible in the small domain |

Notebook 06 is optional and should be designed **before** opening final-test results in notebook 05. If chosen after viewing results, label it exploratory. It deliberately refuses a buffer that leaves too few fitting cells.

## Period and splits

The default is **2017–2022**, using one documented SMAP product version: `NASA/SMAP/SPL3SMP_E/005`. This avoids silently combining `/005` and `/006` or assuming `/006` has 2021 observations. Inventory must confirm the actual account-visible collection. Do not silently switch versions when a query is empty.

* Training: 2017–2019.
* Model selection: 2020.
* Uncertainty calibration: 2021.
* Final test: 2022.

These are prospective baseline choices, not optimized year selections. A longer period/newer reprocessing is possible after a documented version/coverage strategy is established. Do not select years after inspecting final test errors. A fixed 2019 MODIS land-cover layer describes forest fraction for stratification and as a covariate; it does not reconstruct annual forest change. This is retrospective analysis, not an operational forecast.

## Collect the full export

Notebook 02 plans 72 monthly tasks and starts only a few per run. `START_FULL_EXPORTS` is off by default. Earth Engine compute/task quotas apply; fine-scale terrain normalization can take time. Review failures before resubmission. Task IDs and configuration are saved in your Drive work folder. If a task fails, retain its error; do not assume that adding more models fixes an export or quality problem.

Move completed files to:

```text
MyDrive/CHT_SM_v2/
  study_config.json
  target_grid.csv
  inventory.json
  full_export_tasks.json
  exports/
    chtsm_v2_full_201701.csv
    chtsm_v2_full_201702.csv
    ... all completed parts/months ...
  runs/
```

Retain all CSV parts if Drive splits a task. Do not mix pilot files, duplicate downloads or original v1 CSVs. Configuration IDs and exporter-code IDs detect mixed processing settings. A full-calendar assertion distinguishes incomplete exports from genuinely missing satellite values.

If the pilot shows insufficient QA-passing SMAP forest observations, reconsider the domain/target before spending resources on all tasks. Cells with no suitable reference cannot acquire true labels merely through interpolation.

## Training and outputs

The default comparison fits two algorithms × three feature groups × three seeds, plus mean, cell/month seasonal and ERA5 linear baselines: **21 saved models**. Two fixed capacity candidates per learned model are selected using validation macro-cell RMSE. All preprocessing is fit on training rows only. Test outcomes are never supplied for early stopping.

Use a new `RUN_NAME` for a deliberate new configuration. Existing non-empty run folders are protected. Resume of a partial fitting run is not implemented; preserve it and start a separately named run with documented settings. Source, input and model hashes protect the final snapshot. Loading a joblib model is safe only for trusted files generated by this pipeline.

Review your question, settings, comparisons and interpretation limits, then enable `FREEZE_FOR_FINAL_TEST`. This creates a **local analysis freeze**, not external preregistration. Notebook 05 separately requires `RUN_FINAL_TEST=True`; do not enable it during tuning.

Final outputs include per-model/cell scores, date-block uncertainty, paired radar-versus-climate comparisons, forest-fraction/slope/season summaries, artificial-gap scores, all-model test predictions, and selected-model cell-level reconstruction. Original QA-passing values are preserved. Cells with too few training targets remain unfilled. Simple support/extrapolation flags accompany predictions.

Intervals use calibration-year **daily maximum absolute residuals** to preserve within-day spatial grouping. Daily exchangeability and stationarity are not established, so no unconditional coverage guarantee is claimed. Report empirical coverage and width, including sensitivity to time dependence and domain shift. Artificial masking of observed targets does not validate naturally missing forest conditions.

## How you can help

1. Run notebook 01 in your authorized account and complete the pilot.
2. Share the printed inventory, task status/error and pilot QA summary. The project ID is non-secret; login credentials are not needed in chat.
3. Check that the selected districts/grid and orbit make sense for your intended CHT study area.
4. If available, describe independent BMD/university/field records: station locations, dates/frequency, depth, units and calibration. Gravimetric and volumetric moisture cannot be compared without the appropriate conversion. Point observations also need a representativeness assessment for a coarse satellite footprint.

No field measurements are required to begin a careful satellite-product reconstruction study. Independent measurements are required for stronger claims about actual forest-soil moisture accuracy. A small new field campaign cannot retrospectively validate 2021 observations.

## Local checks

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gee,notebooks,train]'
python -m unittest discover -s tests -v
python scripts/check_notebooks.py
```

The original two notebooks and figures are historical v1 artifacts. Their code/figures are not revised v2 findings. Authenticated Earth Engine execution, real v2 training and independent field validation remain pending until the new exports are available.
