# toll2osm
Extracts toll stations from NVDB.

### Usage ###

<code>python toll2osm.py [autopass]</code>

Produces a _bomstasjoner.osm_ file containing all the toll stations in NVDB.

Add optional <code>autopass</code> option to get toll stations from Autopass (for referencce, no fee information). Currently not operational.

After the file has been generated, update OSM using [update2osm](https://github.com/NKAmapper/update2osm).

### Reference ###

* [Statens Vegvesen - Bompenger](https://www.vegvesen.no/trafikkinformasjon/reiseinformasjon/bompenger).
* [AutoPASS](https://www.autopass.no).
