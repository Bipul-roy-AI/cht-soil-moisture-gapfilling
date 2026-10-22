# Verification evidence and limits

The revised workflow passed **19 unit/integration checks** in the authoring CPU environment. They cover:

* duplicate cell/date rejection, complete-calendar requirements, mixed versions/configurations, QA exclusion, physical log ratios and chronological split separation;
* training-only imputation and the invariance of fitted validation results when final-test targets are perturbed;
* hidden-target removal before temporal interpolation;
* date-cluster calibration and paired block-bootstrap identity;
* real RF/XGBoost fitting on fictional fixtures, separate calibration, freeze/reload, protected final evaluation and preservation of original observations;
* offline construction/serialization of the full Earth Engine export graph using the API library's mock algorithm registry.

All seven maintained notebooks validate against the notebook schema, and their **36 Python cells** parse. Notebook `00_offline_software_check.ipynb` was also executed end to end on CPU, including fitting, calibration, freeze, test evaluation, reconstruction and artificial-gap experiments. The [executed copy](software_check_executed.ipynb) contains clearly marked **fictional** outputs; it is not a Bangladesh result or method ranking.

The installed direct versions are recorded in [environment_tested.json](environment_tested.json). This is an environment snapshot, not a fully hash-locked transitive environment. Core software was tested with Python 3.12 and the CPU XGBoost distribution.

**Not yet verified:** authenticated Earth Engine asset availability, actual district-name resolution in the user's account, successful real pilot/full exports, runtime resource limits for CHT scenes, authenticated Colab/GPU execution, real v2 training, independent field validation or improved scientific performance. Graph serialization checks Python/API structure; it cannot establish server-side data correctness or a successful export.

The full real-data workflow intentionally requires the user's authorized account and reviewed exports. It does not substitute old regional labels or synthetic fixtures for missing real data. Final test gates are local research safeguards, not external preregistration or proof of statistical independence.
