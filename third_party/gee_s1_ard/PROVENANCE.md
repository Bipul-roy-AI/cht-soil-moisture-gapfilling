# Pinned terrain normalization source

Upstream: https://github.com/adugnag/gee_s1_ard

Commit: `39207cb4998c9c80c27af3d8a62debe7ab41e7c7`

Vendored file: upstream `python-api/terrain_flattening.py` copied without code changes to `src/chtsm/vendor/terrain_flattening.py`. The upstream MIT licence is retained here and with the package. Only this standalone terrain routine is imported; the upstream wrapper's automatic `ee.Initialize()` is not used.

Reference: Mullissa et al. (2021), https://doi.org/10.3390/rs13101954; adopted terrain-model reference: Vollrath et al. (2020), https://doi.org/10.3390/rs12111867.

Graph serialization is checked offline with Earth Engine's API test fixture. Server-side processing and suitability for the chosen CHT scenes still require a real authenticated pilot. This is angular model-based normalization, not an assertion of equivalence to every pixel-area RTC product or a guarantee of improved soil-moisture retrieval.
