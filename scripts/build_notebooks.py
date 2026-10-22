"""Generate clean, executable research notebooks from maintained Python sources."""
from pathlib import Path
import ast
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
BOOT='''from pathlib import Path
import os, sys, subprocess, importlib.util, json
try:
    IN_COLAB = importlib.util.find_spec("google.colab") is not None
except ModuleNotFoundError:
    IN_COLAB = False
ROOT = next((p for p in [Path.cwd(), Path.cwd().parent, Path("/content/cht-soil-moisture-gapfilling")]
             if (p / "pyproject.toml").exists()), None)
if ROOT is None and IN_COLAB:
    ROOT = Path("/content/cht-soil-moisture-gapfilling")
    subprocess.run(["git", "clone", "--branch", "research-notebooks-v2", "--single-branch",
                    "https://github.com/Bipul-roy-AI/cht-soil-moisture-gapfilling.git", str(ROOT)], check=True)
if ROOT is None:
    raise RuntimeError("Open this notebook from the cloned repository, or run it in Colab.")
ROOT = ROOT.resolve()
if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", str(ROOT) + "[gee,notebooks]"], check=True)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
print("Project:", ROOT)
'''
DRIVE='''if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    WORK = Path("/content/drive/MyDrive/CHT_SM_v2")
else:
    WORK = ROOT / "work_v2"
WORK.mkdir(parents=True, exist_ok=True)
print("Persistent work folder:", WORK)
'''
LOAD='''from chtsm.data import read_config, load_exports, audit_frame, save_json
CONFIG_PATH = WORK / "study_config.json"
config = read_config(CONFIG_PATH)
# Move the monthly FULL exports from the Drive export folder into this folder.
# Pilot exports have a different prefix and must not be mixed into the full table.
EXPORT_DIR = WORK / "exports"
CSV_PATHS = sorted(EXPORT_DIR.glob("chtsm_v2_full_*.csv"))
if not CSV_PATHS:
    raise FileNotFoundError("Put completed monthly chtsm_v2_full_*.csv exports in WORK/exports first.")
frame = load_exports(CSV_PATHS, config)
'''

def write(name,title,body):
    nb=nbf.v4.new_notebook();cells=[nbf.v4.new_markdown_cell('# '+title)]
    for typ,text in body:
        if typ=='code':ast.parse(text);cells.append(nbf.v4.new_code_cell(text))
        else:cells.append(nbf.v4.new_markdown_cell(text))
    nb.cells=cells;nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
                                'language_info':{'name':'python'},'colab':{'name':name,'provenance':[]}}
    nbf.validate(nb);nbf.write(nb,ROOT/'notebooks'/name)

write('00_offline_software_check.ipynb','00 — Offline execution check: FICTIONAL data only',[
('markdown','This notebook checks the entire software path on generated arrays. It requires no Earth Engine login and produces **no Bangladesh scientific result**. CPU is sufficient. Real imagery, quality, geographic boundaries and GPU execution are not validated by this fixture.'),
('code',BOOT),
('code','''import tempfile
from chtsm.synthetic import make_fixture
from chtsm.models import fit_experiment, freeze_experiment, evaluate_final
from chtsm.gaps import run_gap_experiments
frame, config = make_fixture(ROOT / "configs/study_v2.json")
if importlib.util.find_spec("xgboost") is None:
    config["algorithms"] = ["random_forest"]
RUN = Path(tempfile.mkdtemp(prefix="cht_fictional_check_")) / "run"
metadata, validation_table = fit_experiment(frame, config, RUN, software_check=True)
print("FICTIONAL SOFTWARE CHECK ONLY")
print("Rows:", len(frame), "| validation-selected model:", metadata["selected_model"])
display(validation_table[["name", "validation_macro_cell_rmse"]])'''),
('code','''freeze_experiment(RUN, "Fictional software verification only; all prespecified methods; primary outcome macro-cell RMSE; no field or satellite observations.")
metrics, reconstruction = evaluate_final(frame, RUN, allow_final_test=True)
gaps = run_gap_experiments(frame, RUN, lengths=(1, 3), seeds=(42,))
assert reconstruction.loc[reconstruction.target_sm.notna(), "complete_sm"].equals(
    reconstruction.loc[reconstruction.target_sm.notna(), "target_sm"])
print("Training, calibration, freeze, evaluation, reconstruction and gap tests completed.")
print("Artifacts:", RUN)
print("No accuracy result from this notebook may be described as Bangladesh performance.")''')])

write('01_gee_inventory_and_pilot_export.ipynb','01 — Verify sources, choose an orbit, export a small real pilot',[
('markdown','Run this in **Google Colab** using your own authorized Earth Engine account. Start with CPU. The original repository project ID is supplied as a non-secret default. We use the version-005 single-product period **2017–2022** to avoid an unverified version splice. The notebook checks actual availability; it never silently falls back to a different product. GAUL district boundaries require name/licence review. No exports start until the final launch flag is changed.'),
('code',BOOT),('code',DRIVE),
('code','''from chtsm.data import read_config, save_json
config = read_config(ROOT / "configs/study_v2.json")
# This is the non-secret Cloud project ID used in your original notebook.
GEE_PROJECT_ID = "gee-projects-475506"  # Change if that project is no longer authorized.
import ee
ee.Authenticate()
ee.Initialize(project=GEE_PROJECT_ID)
from chtsm.gee import inventory
info, cells = inventory(config)
print(json.dumps(info, indent=2))
grid_features = cells.getInfo()["features"]
import pandas as pd
cell_table = pd.DataFrame([f["properties"] for f in grid_features])
display(cell_table[["cell_id", "lon", "lat"]])'''),
('markdown','Choose one relative orbit from the inventory and inspect its coverage. An orbit with many scenes may still have incomplete coverage. The pilot uses the first few grid cells as a software/data-feasibility check, not a representative forest sample. Later full exports cover every selected district grid centre.'),
('code','''RELATIVE_ORBIT = None  # Replace with one integer shown in relative_orbit_scene_counts.
if RELATIVE_ORBIT is None:
    raise ValueError("Choose an orbit from the printed inventory, set RELATIVE_ORBIT, then rerun this cell.")
config["relative_orbit"] = int(RELATIVE_ORBIT)
save_json(WORK / "study_config.json", config)
save_json(WORK / "inventory.json", info)
cell_table.to_csv(WORK / "target_grid.csv", index=False)
print("Saved the actual selected export configuration and grid.")'''),
('code','''from chtsm.gee import start_month_export
START_PILOT_EXPORT = False
if START_PILOT_EXPORT:
    pilot = start_month_export(config, "2021-06-01", "2021-06-08",
        folder="CHT_SM_v2_exports", prefix="chtsm_v2_pilot_20210601", pilot_cells=4)
    save_json(WORK / "pilot_task.json", pilot)
    print(pilot)
else:
    print("Set START_PILOT_EXPORT=True after reviewing the inventory and selected orbit.")'''),
('markdown','Monitor the task at https://code.earthengine.google.com/tasks. The CSV appears in your Google Drive folder `CHT_SM_v2_exports`. Before launching years of exports, check that the pilot contains plausible values, both raw and terrain-normalized SAR, real EVI, QA and acquisition IDs. Use notebook 03\'s pilot section. If it fails, share the task error and inventory/QA summary; do not send credentials. This authoring environment has not run an authenticated GEE export.')])

write('02_gee_multiyear_export.ipynb','02 — Launch resumable monthly full-data exports',[
('markdown','Run only after the pilot succeeds. Exporting six years with fine-scale terrain normalization can take substantial Earth Engine time. This notebook queues a few monthly tasks per run and records task IDs. Your account\'s task/compute quotas apply. It does not train a model or change the frozen study design.'),('code',BOOT),('code',DRIVE),
('code','''from chtsm.data import read_config, save_json
from chtsm.gee import month_windows, start_month_export
import ee
GEE_PROJECT_ID = "gee-projects-475506"
ee.Authenticate(); ee.Initialize(project=GEE_PROJECT_ID)
config = read_config(WORK / "study_config.json")
if config["relative_orbit"] is None:
    raise ValueError("Finish orbit selection in notebook 01 first.")
windows = month_windows(config)
print("Monthly tasks planned:", len(windows))
print(windows[:4], "...", windows[-2:])
ledger_path = WORK / "full_export_tasks.json"
ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
print("Tasks already recorded:", len(ledger))'''),
('code','''START_FULL_EXPORTS = False
NEXT_N_MONTHS = 3  # Launch small batches; monitor quota and completed outputs.
# Failed/cancelled tasks must be investigated. Remove ONLY their verified ledger
# entries before retrying so successful tasks are not accidentally duplicated.
existing = {r["start"] for r in ledger}
pending = [(a, b) for a, b in windows if a not in existing]
if START_FULL_EXPORTS:
    for start, end in pending[:NEXT_N_MONTHS]:
        prefix = "chtsm_v2_full_" + start[:7].replace("-", "")
        record = start_month_export(config, start, end, "CHT_SM_v2_exports", prefix)
        ledger.append(record)
        save_json(ledger_path, ledger)  # Persist after EACH successful submission.
        print("Submitted", prefix, record["task_id"])
else:
    print("Review pending tasks, then explicitly enable START_FULL_EXPORTS.")'''),
('code','''# Status only: no task is deleted or restarted automatically.
status = ee.data.getTaskStatus([r["task_id"] for r in ledger]) if ledger else []
for s in status:
    print(s.get("id"), s.get("state"), s.get("error_message", ""))'''),
('markdown','Move only completed `chtsm_v2_full_*.csv` files into `MyDrive/CHT_SM_v2/exports/`. Drive may split a large export into multiple CSV parts; retain every part with that prefix. Do not mix pilot exports, duplicate downloads, old NDVI-renamed tables, different orbit settings or product versions. Notebook 03 rejects duplicate cells/dates, mixed provenance and incomplete calendars. The complete export is required for the declared six-year study; reduce the study prospectively if resources require a smaller feasibility design.')])

write('03_data_audit_and_freeze.ipynb','03 — Audit real exports and document the analysis protocol',[
('markdown','Run after the pilot, then again after the full export completes. A successful structural audit does not prove physical accuracy, independent validation or RFI cause. The study target is a QA-passing SMAP product observation at a fixed target-grid cell/date, not a regional mean copied to multiple pixels.'),('code',BOOT),('code',DRIVE),
('code','''from chtsm.data import read_config, load_exports, audit_frame, save_json
config = read_config(WORK / "study_config.json")
# PILOT CHECK: set the actual downloaded pilot CSV path, or leave as None.
PILOT_CSV = None
if PILOT_CSV is not None:
    pilot = load_exports([Path(PILOT_CSV)], config)
    display(pilot[["date","cell_id","sm_raw","sm_qa","target_sm","missing_reason",
                   "raw_vv_db","rtc_vv_db","evi","sar_valid_fraction"]].head(30))
    print(pilot.missing_reason.value_counts())
    print("Pilot rows:", len(pilot), "| no full-calendar assertion at this stage.")'''),
('code',LOAD),
('code','''report = audit_frame(frame, config, require_complete=True)
save_json(WORK / "full_data_audit.json", report)
print(json.dumps(report, indent=2, default=str))
display(frame.groupby("split").agg(rows=("cell_id","count"), dates=("date","nunique"),
                                    usable_targets=("target_sm","count")))
# Counts vary by date: a mean over available pixels can change support.
availability = frame.groupby("date").target_sm.agg(["count", "size"])
availability["usable_fraction"] = availability["count"] / availability["size"]
availability.to_csv(WORK / "observed_support_by_date.csv")
import matplotlib.pyplot as plt
availability.usable_fraction.plot(figsize=(12,3), ylabel="Fraction of selected cells with usable SMAP", title="Availability audit — no cause attribution")
plt.show()'''),
('code','''# Inspect persistent missingness and sensor support BEFORE modelling.
cell_summary = frame.groupby("cell_id").agg(lon=("lon","first"),lat=("lat","first"),
    usable_fraction=("target_sm",lambda s:s.notna().mean()),forest_fraction=("forest_fraction","first"),
    slope_deg=("slope_deg","first"),mean_radar_coverage=("sar_valid_fraction","mean"))
cell_summary.to_csv(WORK / "cell_support_audit.csv")
display(cell_summary.sort_values("usable_fraction").head(20))
print("Revisit/coverage, QA rejection, and native diagnostic/RFI reasons need separate interpretation.")'''),
('markdown','Write the protocol before training or final-test inspection: target definition, primary macro-cell RMSE, planned algorithms/feature groups/seeds, gap lengths, comparison information sets, subgroup definitions and uncertainty method. The training notebook uses validation only for model selection, then a separate calibration year. Final evaluation requires a local freeze; this is not an external preregistration. If spatial transfer is planned, choose held-out cells based on geometry and predeclare it before opening final-test results.'),
('code','''PROTOCOL_NOTE = (
    "Primary task: retrospective reconstruction of QA-passing SMAP cell/date targets. "
    "Primary selection outcome: macro-cell RMSE on validation year only. "
    "Compare climate-only, climate+raw SAR and climate+RTC SAR across all declared seeds, "
    "with mean/seasonal/ERA5 baselines. Separate calibration year; final test year untouched. "
    "Artificial 1/3/7/14-day gaps are secondary analyses; long gaps are stress tests. "
    "No in-situ accuracy or physical-causation claim without independent evidence."
)
(WORK / "protocol_note.txt").write_text(PROTOCOL_NOTE + "\\n")
print(PROTOCOL_NOTE)''')])

write('04_colab_training.ipynb','04 — Train baselines and sensor-ablation models on Colab',[
('markdown','Use **Colab CPU** first. These tabular models do not require a GPU; a compatible GPU XGBoost installation is optional. Random Forest remains CPU-based. No real model is bundled. All preprocessing is fit on training inputs only; two declared model-capacity candidates use validation, and test outcomes are not used for early stopping.'),('code',BOOT),('code',DRIVE),('code',LOAD),
('code','''if importlib.util.find_spec("xgboost") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "xgboost>=2.1,<4"], check=True)
from chtsm.models import fit_experiment
DEVICE = "cpu"  # Optional "cuda" ONLY with a compatible GPU build/runtime.
RUN_NAME = "study_v2_temporal_001"  # New name for a deliberate configuration change.
RUN = WORK / "runs" / RUN_NAME
metadata, validation_table = fit_experiment(frame, config, RUN, device=DEVICE)
display(validation_table[["name", "validation_macro_cell_rmse", "seed"]])
print("Validation-selected reconstruction model:", metadata["selected_model"])
print("Saved models/configuration/calibration/data hashes:", RUN)'''),
('markdown','The default experiment fits RF and XGBoost for three feature groups and three seeds, plus three simple baselines. Report every seed; selecting a deployment model on validation does not justify reporting only its test seed. Existing run folders are protected. Resume during a partially completed fit is not implemented; retain the partial folder and use a new run name. Calibration uses daily maximum residual clusters; temporal exchangeability is not guaranteed and empirical test coverage must be reported.'),
('code','''from chtsm.models import freeze_experiment
FREEZE_FOR_FINAL_TEST = False
if FREEZE_FOR_FINAL_TEST:
    note = (WORK / "protocol_note.txt").read_text()
    freeze_experiment(RUN, note)
    print("Local protocol/run snapshot frozen. Final test remains in notebook 05.")
else:
    print("Review validation choices and protocol, then explicitly enable FREEZE_FOR_FINAL_TEST.")''')])

write('05_locked_evaluation_and_gap_tests.ipynb','05 — Locked final evaluation, realistic gap tests, and flagged reconstruction',[
('markdown','Only run final evaluation after the declared models/protocol have been frozen. This notebook verifies data, model and code hashes and protects existing outputs. Artificial-gap analysis is a secondary test on observed targets; no reference truth is created for naturally missing values. Field validation remains a separate study component.'),('code',BOOT),('code',DRIVE),('code',LOAD),
('code','''from chtsm.models import evaluate_final
RUN = WORK / "runs" / "study_v2_temporal_001"
RUN_FINAL_TEST = False
if not RUN_FINAL_TEST:
    raise RuntimeError("Final evaluation is disabled. Freeze the run and explicitly set RUN_FINAL_TEST=True when ready.")
metrics, reconstruction = evaluate_final(frame, RUN, allow_final_test=True)
import pandas as pd
summary = pd.DataFrame([{"model": name, "rmse": value["micro"]["rmse"],
                        "macro_cell_rmse": value["macro_cell_rmse"], "r2": value["micro"]["r2"],
                        "interval_coverage": value["empirical_interval_coverage"]}
                       for name, value in metrics.items()])
display(summary)
summary.to_csv(RUN / "final_test" / "summary.csv", index=False)'''),
('code','''from chtsm.gaps import run_gap_experiments
gap_results = run_gap_experiments(frame, RUN, lengths=(1,3,7,14), seeds=(42,123,2025))
gap_table = pd.DataFrame([{"gap_days": r["requested_gap_days"], "seed": r["seed"],
                         "model": name, "rmse": m["rmse"], "scored": r["common_scored_targets"]}
                        for r in gap_results for name, m in r["models"].items()])
display(gap_table.groupby(["gap_days", "model"]).rmse.agg(["mean","std"]))
gap_table.to_csv(RUN / "final_test" / "gap_summary.csv", index=False)'''),
('markdown','Persistence and linear interpolation receive the same retained satellite observations; hidden targets are removed before those baselines are computed. Interpolation can use future retained values because this is retrospective reconstruction. Learned models use only exogenous predictors. All methods are scored on the same recoverable reference coverage. Report this information-set distinction and the count of excluded edge cases.'),
('code','''import matplotlib.pyplot as plt
# Cell-level output avoids treating changing-coverage regional means as observations.
CELL_ID = reconstruction.cell_id.iloc[0]  # Choose a cell from your actual grid.
r = reconstruction[reconstruction.cell_id == CELL_ID]
fig, ax = plt.subplots(figsize=(12,4))
ax.plot(r.date, r.complete_sm, lw=1, color="steelblue", label="Selected-model completed product")
known = r.target_sm.notna(); ax.scatter(r.loc[known,"date"],r.loc[known,"target_sm"],s=7,color="black",label="QA-passing SMAP")
missing = r.is_reconstructed
ax.scatter(r.loc[missing,"date"],r.loc[missing,"complete_sm"],s=7,color="tomato",label="Reconstructed; reference unknown")
ax.set(title=f"SMAP product reconstruction — {CELL_ID}; not independent field validation", ylabel="m³/m³")
ax.legend();fig.tight_layout();fig.savefig(RUN / "final_test" / "example_cell.png", dpi=150);plt.show()
print("Unsupported cells:", reconstruction.loc[reconstruction.unsupported_cell,"cell_id"].nunique())
print("Range-extrapolation flags:", int(reconstruction.outside_training_ranges.sum()))
print("Files:", RUN / "final_test")'''),
('markdown','Before manuscript claims: examine per-cell, season, forest-fraction and slope scores, paired block-bootstrap sensor comparisons, multi-seed variability, interval coverage/width, and the effect of poor sensor availability. Forest fraction is not canopy density; current masks/QA do not diagnose RFI. Prediction ranges and support flags are diagnostics, not full out-of-distribution detection. Predictions are withheld for cells with too few training targets. Calibration-domain transfer and natural missing-condition accuracy remain unverified.')])

write('06_optional_spatial_transfer.ipynb','06 — Optional joint spatial/year transfer, chosen before final inspection',[
('markdown','This is an optional SECOND experiment. Choose geographic holdouts from grid geometry **before** viewing final results. If chosen after inspecting residuals, label the analysis exploratory. CHT is small relative to radiometer footprints: a 35 km centre-distance buffer may leave too little fitting data. The notebook stops in that case rather than claiming independent spatial validation. It tests joint new-place/new-year transfer; it does not isolate a causal geography effect.'),('code',BOOT),('code',DRIVE),('code',LOAD),
('code','''from chtsm.gaps import spatial_subset
from chtsm.models import fit_experiment, freeze_experiment
import copy
cells = frame.groupby("cell_id")[["lon","lat"]].first()
display(cells)
HELDOUT_CELLS = []  # Explicit target-cell IDs selected using geographic geometry.
BUFFER_KM = 35
spatial_frame, design = spatial_subset(frame, HELDOUT_CELLS, buffer_km=BUFFER_KM)
spatial_config = copy.deepcopy(config);spatial_config["spatial_design"] = design
RUN = WORK / "runs" / "study_v2_spatial_001"
metadata, table = fit_experiment(spatial_frame, spatial_config, RUN, device="cpu")
display(table[["name", "validation_macro_cell_rmse"]])
print(design)'''),
('code','''FREEZE_SPATIAL_RUN = False
if FREEZE_SPATIAL_RUN:
    freeze_experiment(RUN, "Joint new-place/new-year transfer on predeclared held-out cells; 35 km approximate centre buffer; macro-cell RMSE primary; calibration-domain transfer assessed empirically.")
    save_json(WORK / "spatial_design.json", design)
else:
    print("Review retained spatial support and protocol, then explicitly enable freeze.")'''),
('markdown','For this experiment use `spatial_frame` and its spatial run path in the evaluation functions from notebook 05. Calibration uses fitting-region cells; interval coverage on held-out geography is not guaranteed. The production support policy will flag/withhold reconstruction in unseen cells even though raw transfer predictions are evaluated for research. If a useful holdout is impossible, report temporal generalization and narrow spatial claims rather than weakening the buffer silently.')])
print('Generated',len(list((ROOT/'notebooks').glob('*.ipynb'))),'validated, output-free notebooks')
