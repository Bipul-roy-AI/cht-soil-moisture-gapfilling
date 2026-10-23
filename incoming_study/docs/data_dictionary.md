# Data dictionary (to complete during extraction)

The original Shapefile includes `adm2_name`, `adm2_pcode`, and `area_sqkm`. No exports have been generated.

Planned observation-table columns (exact names are provisional):

| Column | Meaning | Provenance |
| --- | --- | --- |
| `date` | Acquisition/composite date; define temporal matching explicitly | SMAP / extraction |
| `grid_id` | Stable native SMAP grid-cell identifier | SMAP geometry |
| `district` | Spatially intersected district; cells may cross borders | CHT boundary |
| `sm_raw` | Original SMAP surface-soil-moisture estimate | SMAP |
| `sm_quality` | Retrieved QA bit field / decoded acceptance flag | SMAP |
| `target_sm` | QA-accepted observation; otherwise missing | Processing |
| `precip_mm` | Rainfall over declared accumulation interval | CHIRPS |
| `forest_fraction` | Share of high-resolution land-cover class inside cell | LULC |
| `sar_vv_db`, `sar_vh_db` | SAR backscatter and its acquisition metadata | Sentinel-1 |

For every output field, later add temporal support, spatial support, units, resampling/aggregation, masking, null conventions and source version.
