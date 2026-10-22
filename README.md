# CHT Soil Moisture Reconstruction — revised research notebooks

Research question: **When does terrain-normalized Sentinel-1 add predictive skill to climate-based reconstruction of SMAP over the Chittagong Hill Tracts?**

**Status:** seven revised notebooks and reusable helpers are provided for a new study. The offline software path is checked using explicitly fictional data. Authenticated Earth Engine exports, real v2 training and independent field validation are pending. No improved Bangladesh accuracy is claimed.

## Start in Colab

Open [**01: inventory and pilot export**](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/01_gee_inventory_and_pilot_export.ipynb). Authorize your own Earth Engine account, review the printed inventory, choose a relative orbit, then launch the small pilot. The project ID defaults to the non-secret ID in the original notebook; change it if needed. Do not share credentials.

Run [**00: fictional offline software check**](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/00_offline_software_check.ipynb) first if you want to verify the local training/evaluation path without satellite exports.

| Notebook | What it does | Colab |
|---|---|---|
| [00 offline check](notebooks/00_offline_software_check.ipynb) | Fictional fixtures only; train/calibrate/freeze/evaluate/gap-test | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/00_offline_software_check.ipynb) |
| [01 inventory/pilot](notebooks/01_gee_inventory_and_pilot_export.ipynb) | Verify SMAP dates/grid, district names and SAR orbit; seven-day pilot | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/01_gee_inventory_and_pilot_export.ipynb) |
| [02 full export](notebooks/02_gee_multiyear_export.ipynb) | Small batches of monthly real-data tasks, saved task ledger | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/02_gee_multiyear_export.ipynb) |
| [03 data audit](notebooks/03_data_audit_and_freeze.ipynb) | QA, missingness/support audit, complete-calendar check, protocol | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/03_data_audit_and_freeze.ipynb) |
| [04 training](notebooks/04_colab_training.ipynb) | Baselines, RF/XGBoost sensor ablations, separate calibration | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/04_colab_training.ipynb) |
| [05 locked evaluation](notebooks/05_locked_evaluation_and_gap_tests.ipynb) | Final metrics, gap tests, subgroup/paired errors, support flags | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/05_locked_evaluation_and_gap_tests.ipynb) |
| [06 optional spatial transfer](notebooks/06_optional_spatial_transfer.ipynb) | Predeclared geographic holdout with approximate exclusion buffer | [Open](https://colab.research.google.com/github/Bipul-roy-AI/cht-soil-moisture-gapfilling/blob/research-notebooks-v2/notebooks/06_optional_spatial_transfer.ipynb) |

**Where to train:** Colab CPU is sufficient to start these tabular models. A compatible GPU XGBoost runtime is optional; Random Forest uses CPU. GEE performs satellite processing in the user's authorized account. Fine-scale terrain normalization can take substantial export time, so complete the pilot before launching multi-year tasks.

Read the [full run guide](docs/research/RUN_GUIDE.md) for Drive folder layout, task recovery, required user steps and limitations. Choose any optional spatial holdout before final-test inspection.

## Main corrections

* Genuine target-grid **cell/date** labels; no regional mean copied to multiple pixels.
* Verified single-version period: `/005`, 2017–2022, subject to live inventory confirmation. No silent `/005`/`/006` splice.
* Train 2017–2019; validate 2020; calibrate intervals 2021; final test 2022.
* Actual QA-screened MODIS EVI; 1 km product documented correctly.
* Linear-power SAR aggregation, physically defined log ratio, pinned terrain normalization, common raw/RTC masks, recorded acquisition age/coverage.
* Target-grid aggregation, district geometry, explicit missing/QA states, export configuration and source fingerprints.
* Train-only imputation; validation-only model selection; no test early stopping.
* All declared seeds, climate-only versus raw/RTC radar comparisons, artificial-gap temporal baselines, interval coverage/width and support flags.
* Cells with insufficient training reference remain unfilled. Uncertainty and causal-interpretation limits are explicit.

## What data you need

The notebooks obtain public SMAP, Sentinel-1, ERA5-Land, MODIS vegetation/land cover, terrain and district-boundary inputs. The old feature CSV and old daily regional series cannot replace the new cell/date export. A complete exported calendar is checked before full training.

Independent BMD/university/field measurements are optional for beginning a **satellite-product reconstruction benchmark**, and important for stronger claims about actual forest-soil moisture. Record measurement depth, timing, units and calibration, and assess point-to-footprint representativeness. No CHT station inventory or field ground truth is bundled.

The defaults are retrospective: previous-timestamp predictors do not imply operational availability because reanalyses, annual maps and composites have production delays. Forest fraction is not canopy density. Availability/QA flags do not establish RFI causes. SMAP is the reconstruction reference, not independent field truth.

## Local installation and verification

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gee,notebooks,train]'
python -m unittest discover -s tests -v
python scripts/check_notebooks.py
```

The offline CPU verification used the `xgboost-cpu` distribution; Colab can retain its compatible existing XGBoost installation. See [methods](docs/research/METHODS_V2.md), the [run guide](docs/research/RUN_GUIDE.md), [software verification](docs/research/SOFTWARE_CHECKS.md), and [reviewed literature](docs/research/related_literature.csv).

## Historical notebooks

`Project_1.ipynb`, `cht_soil_moisture_gapfilling.ipynb`, `data/smap_daily_means.csv` and the old `results/` figures are retained as **v1 exploratory artifacts**. They do not establish v2 performance. The original README is preserved under [legacy_readme.md](docs/research/legacy_readme.md); its physical interpretations and reported metrics should not be treated as validated findings of the revised workflow. Start new work from `notebooks/`.

## Attribution

The vendored angular terrain-normalization routine is attributed to [gee_s1_ard](https://github.com/adugnag/gee_s1_ard), pinned commit `39207cb4998c9c80c27af3d8a62debe7ab41e7c7`. Its MIT licence and provenance are retained under `third_party/gee_s1_ard/` and with the package.

Mullissa et al. (2021): https://doi.org/10.3390/rs13101954; Vollrath et al. (2020): https://doi.org/10.3390/rs12111867. The research design also draws on the verified gap-filling and structured-validation references listed in [METHODS_V2.md](docs/research/METHODS_V2.md). Publication readiness depends on the real data and validation; no acceptance or accuracy improvement is guaranteed.
