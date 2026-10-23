# Original gap-filling prototype (historical archive)

This directory preserves the starting `cht-soil-moisture-gapfilling` prototype and its prior figures and input summary. It is **not** the current corrected 2019–2022 evaluation.

| Historical material | Contents |
|---|---|
| [`original_2021_gapfilling.ipynb`](original_2021_gapfilling.ipynb) | Original analysis notebook as previously published |
| [`data/smap_daily_means.csv`](data/smap_daily_means.csv) | Original small CSV used by the prototype |
| [`figures/`](figures/) | Original demonstration/performance graphics |
| [`RESEARCH_AUDIT.md`](RESEARCH_AUDIT.md) | Historical peer-review-style audit of the original implementation |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Historical reproducibility checks and caveats |

Why preserve it? It documents how the research started, and permits future researchers to re-evaluate the original algorithm on a genuinely matched QA-controlled benchmark.

**Do not compare the original figures with Notebook 08's corrected RMSE as if they were produced with identical data, quality filters, splits or protocols.** Statements about physical soil moisture accuracy and driver causality require independent evidence. For the current methods/results see the [main README](../README.md).
