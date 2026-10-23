# Reproducing and extending the analysis

## 1. Reproduce what is currently possible offline

```bash
python scripts/audit_availability.py
python scripts/plot_availability.py
python -m unittest discover -s tests -v
```

The script regenerates `results/availability_audit.json` and `results/availability_monthly.csv` solely from the versioned 300-date file. This measures **availability**, not model accuracy.

## 2. Re-export a trustworthy analysis table in Earth Engine

The 2-MB `Project_1.ipynb` and `cht_soil_moisture_gapfilling.ipynb` are historical exploratory notebooks, **not a clean linear reproduction pipeline**. Several mutually superseded models/exports share variable names. Do not run the destructive housekeeping cell 49 on valuable working files; it removes files outside a short allowlist.

Before fitting a new model:

1. For the 2021 period, use `NASA/SMAP/SPL3SMP_E/005` (not `/006`), and document exact dates, source version, AM/PM selection, `retrieval_qual_flag`, and the RFI/validity masks used. Record counts of available images and valid grid cells per day.
2. Build a daily calendar *independent of valid SMAP observations*, then calculate each day's predictors even when SMAP is absent. Otherwise target-driven filtering may exclude the very gap dates that require prediction.
3. Use the same verified CHT study polygon/forest mask and spatial support for labels and model features. Avoid assigning a regionwide mean to pixels and treating them as independent targets.
4. Export one row per calendar day for the regional-mean exploratory task, with `date,SMAP_SM,VV,VH,NDVI,PRECIP,PRECIP_LAG7,DEM,SLOPE,TWI,DOY` (or **genuinely extracted** `EVI`). Provide `SMAP_valid_pixel_count`, RFI/quality flags, radar acquisition age/count, landcover fraction, and predictor validity counts when possible.
5. Preserve true nulls. Do not use synthetic `-999` dB SAR, or convert all SMAP gaps to zero. If preserving the old `VHVV` field for archival reasons, do not train on it—the former feature divided two dB-valued backscatter bands.
6. Record whether data windows are retrospective or causal. A ±12-day SAR search uses future data and can support retrospective reconstruction, but not real-time prediction.

## 3. Leak-free XGBoost regional daily comparison

After retrieving the original, uncommitted predictor table (not supplied in Git), run:

```bash
python scripts/evaluate_temporal.py \
  --predictors data/cht_temporal_with_smap.csv \
  --targets data/smap_daily_means.csv \
  --test-start 2021-09-01
```

The script aggregates sampled predictors to one daily row, uses a chronological **train / validation / test** split, fits imputation only on training data, uses validation alone for early stopping, and compares a training-median baseline against climate-only, non-SAR and SAR-augmented XGBoost. It intentionally uses CPU and does not require CUDA. It writes `results/revalidation/evaluation.json` and `held_out_predictions.csv` if and only if the data and dependencies exist.

**Important:** this script isolates statistical leakage but does not repair an invalid Earth Engine export or establish ground truth. It cannot recover genuine EVI from NDVI values, correct SMAP sampling support retroactively, or resolve an incorrect source-version provenance. Re-extraction and metadata audit remain required. A single chronological split also does not substitute for multi-year validation.

## 4. Results interpretation

- Report **effective independent test dates** alongside every metric; do not substitute number of pixels.
- Compare full SAR model to no-SAR on the *same dates*. SHAP and native importance are descriptive, not causal.
- Do not report accuracy relative to in-situ soil moisture unless actual independent observations have been matched to the same spatial and temporal supports.
- Archive exact input checksums, code commit, package versions, split dates, model seed, selected iteration and a missingness/coverage table alongside newly generated figures.
