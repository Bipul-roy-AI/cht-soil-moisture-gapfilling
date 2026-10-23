# CHT Forest Ecohydrology and Machine Learning

Local-first Jupyter research workspace for Bandarban, Khagrachhari, and Rangamati (Chittagong Hill Tracts, Bangladesh).

**Status:** Project template. No satellite exports or trained models are included. The analysis protocol is a proposal until we finish the pilot inventory and data checks.

## 1. Start on your own computer

1. Extract the downloadable ZIP into a convenient location (for example `Documents/Research/`). Keep the whole folder together.
2. Install **Python 3.11** on your computer if needed. The commands below use the standard Python virtual environment; Miniforge/Conda is also suitable.
3. Open a terminal or command prompt **inside this project folder**.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --user --name cht-ecohydro --display-name "Python (CHT ecohydrology)"
.\.venv\Scripts\python.exe -m jupyter lab
```

Windows Command Prompt: use the same `.venv\Scripts\python.exe` commands; remove the leading `./` or `.\` if necessary.

macOS / Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name cht-ecohydro --display-name "Python (CHT ecohydrology)"
.venv/bin/python -m jupyter lab
```

Select the `Python (CHT ecohydrology)` kernel in JupyterLab.

**First notebook:** `notebooks/00_study_area_and_boundary.ipynb`.

**Second notebook:** `notebooks/01_gee_connection_check.ipynb`. This second notebook connects to Earth Engine only after you run its authorization cell. The project identifier is already configured.

If Python 3.11 is not on your computer, install that version first or adapt the command to your installed compatible Python. Do not blindly install packages into your system Python.

## 2. Files and folder roles

```text
cht-forest-ecohydrology-ml/
├── configs/
│   └── study_config.json         # Central choices, dates, GEE project ID
├── data/
│   ├── boundaries/              # Original three-feature shapefile; DO NOT overwrite
│   ├── raw/gee_exports/         # Unmodified downloaded GEE tables
│   ├── interim/                 # QA and intermediate data
│   ├── processed/               # Model-ready tables
│   └── external/                # Optional later station/field data
├── docs/
│   ├── research_protocol.md     # Proposed scope and decisions to finalize
│   └── data_dictionary.md      # Column definitions as we create outputs
├── notebooks/
│   ├── 00_study_area_and_boundary.ipynb
│   ├── 01_gee_connection_check.ipynb
│   ├── 02_satellite_inventory.ipynb
│   ├── 03_data_extraction_and_quality.ipynb
│   ├── 04_exploratory_ecohydrology.ipynb
│   ├── 05_machine_learning.ipynb
│   ├── 06_gap_validation_and_uncertainty.ipynb
│   └── 07_figures_and_results.ipynb
├── outputs/
│   ├── figures/                 # Plots for reporting
│   ├── maps/                    # Final maps
│   ├── tables/                  # Final metrics and summary tables
│   ├── models/                  # Fitted estimators / reproducibility records
│   └── reports/                 # Research summaries
├── src/cht_eco/                 # Reusable Python functions (later)
├── logs/                        # Exports and run logs
└── requirements.txt
```

The notebooks numbered **02–07 are research-stage placeholders**. We will implement them sequentially after checking the study area and data availability; they are not yet complete analyses.

## 3. Uploaded administrative boundary

The files in `data/boundaries/` are preserved copies of the attached shapefile components, **not a dissolved boundary**. The shapefile contains three features:

- Bandarban (source `adm2_pcode`: `BD2003`)
- Khagrachhari (`BD2046`)
- Rangamati (`BD2084`)

The `.prj` declares **WGS 84 geographic coordinates** (longitude/latitude). The source includes an `area_sqkm` attribute, but final geodesic/projected areas and geometry validity still need verification in notebook 00. Do **not** calculate polygon area directly in latitude-longitude degrees.

Notebook 00 creates a dissolved union in memory for regional calculations, **without changing the district features or original files**.

## 4. Earth Engine configuration

The Earth Engine Cloud Project is stored once in `configs/study_config.json`:

`axial-paratext-491911-b6`

Future notebooks should load this identifier from the JSON config and initialize with `ee.Initialize(project=...)`; they should not copy or hard-code another account's project ID.

You'll need to register/verify your own Google Cloud project for Earth Engine access and authorize it on your machine. The project ID is not a password or a credential.

## 5. Research workflow

1. Validate district polygons and create a map.
2. Confirm Earth Engine authentication using your Cloud Project.
3. Inspect SMAP/Sentinel-1/CHIRPS/ERA5 coverage before scheduling exports.
4. Export a small pilot, perform quality checks, and only then decide on a full export.
5. Compare baseline models with Random Forest and XGBoost using time-blocked tests and artificial gaps.
6. Investigate observed/reconstructed soil moisture alongside rainfall, vegetation, terrain, and forest fraction.
7. Export figures/tables with careful limitations. **No claim of independent ground accuracy without independent field data.**

The initial proposal uses 2017-01-01 to 2022-12-31 to keep the SMAP product generation consistent; the date range is configurable and should be finalized following the inventory.

## 6. Research integrity and file management

- Preserve `data/boundaries/` and `data/raw/` unchanged.
- All downloads and intermediate tables stay on your computer. The ZIP does **not** upload data, authenticate Earth Engine, train a model, or make Git commits by itself.
- Git should normally track code, protocols, configuration and selected lightweight figures, **not full satellite exports, local credentials, or large trained models**. The included `.gitignore` helps.
- When an experiment is finished, record package versions (`python -m pip freeze`), the config used, source dataset versions and software commit identifier before publication.
- Any source boundary license and attribution must be checked before public redistribution; no provenance/license was established from the attachment alone.

