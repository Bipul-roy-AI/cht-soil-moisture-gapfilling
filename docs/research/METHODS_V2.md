# Methods and remaining evidence limits

Research question: under which forest-fraction, terrain, rainfall and observation-gap conditions does terrain-normalized Sentinel-1 add skill to climate-based reconstruction of a SMAP product in CHT target cells?

The target is an actual AM SMAP value with the chosen GEE asset's simplified QA pass flag, at a fixed target-grid cell/date. Raw values and QA are retained even when the target is excluded. Missing-target reasons distinguish absence/nodata from retrieval QA rejection; they do not identify RFI or a physical failure mechanism. The inspected GEE ingestion pipeline collapses native quality bitfields, so native HDF5 diagnostic flags require separate handling.

CHT district polygons replace the exploratory rectangle. Selected grid centres lie within the districts; full coarse footprints can cross district/country boundaries. Predictors summarize the full target-cell support. This centre-based population must be reported, with border/support sensitivity considered before area-specific conclusions. The enhanced product's nominal 9 km grid posting is not independent 9 km physical resolution. GEE ingests a geographically reprojected source; export uses the actual asset's projection/transform rather than asserting native EASE-Grid coordinates are retained.

Sentinel-1 linear-power VV/VH are composited over preceding 12 days, with explicit pass/relative orbit. A pinned, attributed angular terrain-normalization routine supplies a volume-scattering model and layover/shadow masks. Raw and corrected features share acquisition identities and valid masks. Real area-weighted reductions first average the fine grid to an intermediate grid, then to target support; a coarse default projection is not substituted for true aggregation. Mean power becomes dB, and polarization ratio in dB is VH_dB−VV_dB. The correction is a hypothesis/ablation and not guaranteed to improve results. See the pinned third-party provenance.

EVI is the actual MOD13A2 band, with SummaryQA=0, not renamed NDVI. Its 16-day composite must end before the target date, with age/coverage recorded. ERA5 precipitation uses preceding 1/3/7/14-day windows in mm, preceding temperature and surface-soil-water variables. Its native support is retained during nearest reprojection to the target grid. Cyclic day-of-year predictors replace a raw monotonic DOY. DEM/slope and a declared static 2019 forest fraction are aggregated. TWI is omitted until a consistent hydrologic derivation is supplied. Forest fraction is not canopy density or biomass.

Predictor timestamps are past-only, but the complete workflow uses retrospective reanalyses, maps and products with processing latency. It is therefore a retrospective reconstruction experiment, not a validated real-time forecast. ERA5 soil moisture is an input/baseline; agreement with ERA5 is not independent validation. L4 assimilation and CCI sensor overlap also require an explicit dependency audit before being called independent references.

The six-year split separates model fitting, selection, interval calibration and final evaluation. Median imputation and missing indicators are fitted inside the training pipeline. Validation-only model selection uses mean per-cell RMSE. Every declared seed is evaluated; deployment selection of one model is also based on validation, not the best test seed. No test early stopping is used. Optional geographic transfer excludes approximate nearby target-cell centres; small-domain and overlapping-footprint limitations remain explicit.

Uncertainty calibration uses one maximum absolute residual per calibration date. Nominal daily simultaneous coverage would require exchangeable day clusters; temporal dependence and later-year/domain change can violate this. The output reports empirical coverage and uses calendar-block bootstrap diagnostics with stated assumptions. These intervals do not include SMAP reference bias or establish coverage on naturally missing conditions.

Artificial gaps hide target values before temporal baselines are computed. Persistence and retrospective interpolation have access to retained observations; the exogenous learned models use their fixed predictors. Their information sets and shared scored coverage are reported. Longer 7/14-day gaps are stress tests unless actual native-cell missingness supports them. More sophisticated state updating, DCT/water-balance models, block-length sensitivity, native RFI diagnostics and independent field evaluation remain further research extensions, not claimed implemented results.

The original approximately 50% regional absence fraction cannot identify RFI. Low model R² or low SHAP attribution cannot establish a physical C-band limitation. The revised experiment evaluates conditional predictive contribution and its limits, without a causal sensor-physics claim.

Relevant verified literature:

* Zhang et al. (2025), *Journal of Hydrology* 653, 132762: https://doi.org/10.1016/j.jhydrol.2025.132762
* Mao et al. (2019), *Water Resources Research*: https://doi.org/10.1029/2019WR024902
* Beale et al. (2025), *Ecohydrology*: https://doi.org/10.1002/eco.70024
* Preimesberger et al. (2025), *Earth System Science Data*: https://doi.org/10.5194/essd-17-4305-2025
* Vollrath et al. (2020): https://doi.org/10.3390/rs12111867
* Mullissa et al. (2021): https://doi.org/10.3390/rs13101954
* Roberts et al. (2017), structured validation: https://doi.org/10.1111/ecog.02881

See `related_literature.csv` for the reviewed references, publication type, evidence access and scope caveats. No claim of an exhaustive review or first-ever study is made.
