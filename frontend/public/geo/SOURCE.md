# China province boundaries

- File: `china-provinces.json`
- Source: DataV GeoAtlas `https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json`
- Retrieved: 2026-11 (see repository build scripts)
- Features: 34 province-level boundaries + South China Sea inset; the app renders data for the 31 mainland provinces only.
- Coordinates are the display copy published by DataV (GCJ-02 aligned), suitable for web visualization. For surveying, navigation, or legally authoritative boundaries, replace this file with an appropriately licensed source and re-run `scripts/build_geometry_sql.py`.

The same boundaries are loaded into PostGIS by `infra/initdb/03_geometry.sql`.
