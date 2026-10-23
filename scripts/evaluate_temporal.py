"""Leakage-controlled *regional daily mean* validation of XGBoost.

Requires the original, uncommitted per-date predictor export; the committed
smap_daily_means.csv alone cannot reproduce the published model scores.
The final chronological test set is NEVER used for fitting or early stopping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def daily_features(predictors: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    """Avoid pseudo-replicated targets: one row and one label per date."""
    if "date" not in predictors or "date" not in targets or "SMAP_SM" not in targets:
        raise ValueError("Predictors need date; targets need date and SMAP_SM")
    a, b = predictors.copy(), targets.copy()
    a["date"] = pd.to_datetime(a["date"], errors="raise").dt.normalize()
    b["date"] = pd.to_datetime(b["date"], errors="raise").dt.normalize()
    b["SMAP_SM"] = pd.to_numeric(b["SMAP_SM"], errors="coerce")
    if b["date"].duplicated().any():
        raise ValueError("Target must have one regional SMAP mean per date")

    numeric = [col for col in a.select_dtypes(include="number").columns
               if col not in ("SMAP_SM", "VHVV")]
    # -999 and -1 were missing-data sentinels, not valid backscatter / NDVI.
    for col in ("VV", "VH"):
        if col in a:
            a.loc[a[col] <= -900, col] = np.nan
    if "NDVI" in a:
        a.loc[a["NDVI"] <= -1, "NDVI"] = np.nan
    if "EVI" in a:
        a.loc[a["EVI"] <= -1, "EVI"] = np.nan

    # The original VHVV is dB/dB, which is not a valid polarization ratio.
    # Difference in dB corresponds to log10(VH_linear / VV_linear).
    if {"VV", "VH"}.issubset(a.columns):
        a["VH_minus_VV_dB"] = a["VH"] - a["VV"]
        numeric.append("VH_minus_VV_dB")
    if not numeric:
        raise ValueError("No numeric predictor features found")
    daily = a.groupby("date", as_index=False)[numeric].mean()
    out = daily.merge(b[["date", "SMAP_SM"]], on="date", how="left", validate="one_to_one")
    return out.sort_values("date").reset_index(drop=True)


def chronological_split(data: pd.DataFrame, test_start: str, validation_fraction: float = 0.2):
    """Three disjoint sets of valid SMAP *dates*, not randomly shuffled pixels."""
    valid = data[data["SMAP_SM"].notna()].sort_values("date").copy()
    boundary = pd.Timestamp(test_start)
    development = valid[valid["date"] < boundary]
    test = valid[valid["date"] >= boundary]
    if len(development) < 15 or len(test) < 5:
        raise ValueError("Insufficient labeled dates for the requested chronological split")
    n_val = max(5, round(len(development) * validation_fraction))
    train, validation = development.iloc[:-n_val], development.iloc[-n_val:]
    assert train["date"].max() < validation["date"].min() < test["date"].min()
    return train, validation, test


def metrics(actual, predicted) -> dict:
    a, p = np.asarray(actual), np.asarray(predicted)
    return {
        "n_days": int(len(a)),
        "rmse_m3_m3": round(float(np.sqrt(mean_squared_error(a, p))), 6),
        "mae_m3_m3": round(float(mean_absolute_error(a, p)), 6),
        "bias_m3_m3": round(float(np.mean(p - a)), 6),
        "r2": round(float(r2_score(a, p)), 6),
    }


def evaluate(daily: pd.DataFrame, test_start: str, seed: int = 42):
    try:
        import xgboost as xgb
    except ImportError as error:
        raise RuntimeError("Install project requirements, including xgboost, before evaluation") from error

    train, val, test = chronological_split(daily, test_start)
    veg = "EVI" if "EVI" in daily else "NDVI" if "NDVI" in daily else None
    climate = [x for x in ("DOY", "PRECIP", "PRECIP_LAG7") if x in daily]
    ancillary = [x for x in ([veg] if veg else []) + ["DEM", "SLOPE", "TWI"] if x in daily]
    radar = [x for x in ("VV", "VH", "VH_minus_VV_dB") if x in daily]
    groups = {"climate_only": climate, "no_radar": climate + ancillary,
              "with_radar": climate + ancillary + radar}
    if not climate or not radar or not ancillary:
        raise ValueError("Need climate, environmental, and radar predictor columns for ablation")

    results = {
        "status": "recomputed; SMAP agreement only, not independent ground validation",
        "split": {"train_end": str(train["date"].max().date()),
                  "validation_start": str(val["date"].min().date()),
                  "test_start": str(test["date"].min().date()),
                  "train_dates": len(train), "validation_dates": len(val), "test_dates": len(test)},
        "baseline_train_median": metrics(test["SMAP_SM"],
                                         np.full(len(test), train["SMAP_SM"].median())),
        "models": {},
    }
    predictions = pd.DataFrame({"date": test["date"], "SMAP_SM": test["SMAP_SM"]})
    for name, features in groups.items():
        # Fit all preprocessing on TRAIN only; validation tunes stopping; TEST scores once.
        imp = SimpleImputer(strategy="median", keep_empty_features=True)
        x_train = imp.fit_transform(train[features])
        x_val = imp.transform(val[features])
        x_test = imp.transform(test[features])
        reg = xgb.XGBRegressor(
            n_estimators=600, max_depth=3, learning_rate=0.03,
            subsample=0.85, colsample_bytree=0.9,
            objective="reg:squarederror", tree_method="hist", device="cpu",
            random_state=seed, n_jobs=2, early_stopping_rounds=30,
            eval_metric="rmse",
        )
        reg.fit(x_train, train["SMAP_SM"], eval_set=[(x_val, val["SMAP_SM"])], verbose=False)
        pred = reg.predict(x_test)
        predictions[name] = pred
        results["models"][name] = {"features": features, "best_iteration": int(reg.best_iteration),
                                   **metrics(test["SMAP_SM"], pred)}
    return results, predictions


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictors", type=Path, required=True,
                   help="Original GEE predictor CSV; not tracked in Git")
    p.add_argument("--targets", type=Path, default=Path("data/smap_daily_means.csv"))
    p.add_argument("--test-start", default="2021-09-01")
    p.add_argument("--output-dir", type=Path, default=Path("results/revalidation"))
    args = p.parse_args()
    predictors = pd.read_csv(args.predictors)
    targets = pd.read_csv(args.targets)
    if "EVI" not in predictors and "NDVI" in predictors:
        print("NOTE: Using genuine NDVI. Rename is prohibited; re-export GEE EVI if desired.")
    daily = daily_features(predictors, targets)
    result, predictions = evaluate(daily, args.test_start)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    predictions.to_csv(args.output_dir / "held_out_predictions.csv", index=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
