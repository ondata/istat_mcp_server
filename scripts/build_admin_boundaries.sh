#!/usr/bin/env bash
# Scarica i limiti amministrativi ISTAT 2026 e produce TopoJSON per
# comuni, province e regioni in resources/geo/
#
# Input CRS: EPSG:32632 (WGS 84 / UTM zone 32N)
# Output: GeoJSON EPSG:4326 singlepart (tmp) + TopoJSON (resources/geo)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$REPO_ROOT/tmp"
GEO_DIR="$REPO_ROOT/resources/geo"
ZIP_URL="https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip"
ZIP_FILE="$TMP_DIR/Limiti01012026_g.zip"
EXTRACT_DIR="$TMP_DIR/Limiti01012026_g"

mkdir -p "$TMP_DIR"
[ -d "$GEO_DIR" ] || mkdir -p "$GEO_DIR"

# --- download ---
echo "Download ZIP ISTAT..."
curl -L "$ZIP_URL" -o "$ZIP_FILE"

# --- estrazione ---
echo "Estrazione ZIP..."
unzip -q -o "$ZIP_FILE" -d "$EXTRACT_DIR"

# --- layer: nome → path shapefile ---
declare -A LAYERS=(
  ["comuni"]="$EXTRACT_DIR/Com01012026_g/Com01012026_g_WGS84.shp"
  ["province"]="$EXTRACT_DIR/ProvCM01012026_g/ProvCM01012026_g_WGS84.shp"
  ["regioni"]="$EXTRACT_DIR/Reg01012026_g/Reg01012026_g_WGS84.shp"
)

for NAME in "${!LAYERS[@]}"; do
  SHP="${LAYERS[$NAME]}"
  GEOJSON="$TMP_DIR/${NAME}.geojson"
  TOPOJSON="$GEO_DIR/${NAME}.topojson"

  echo "Processing $NAME..."

  # EPSG:32632 → GeoJSON EPSG:4326 singlepart
  ogr2ogr \
    -f GeoJSON \
    -s_srs EPSG:32632 \
    -t_srs EPSG:4326 \
    -explodecollections \
    "$GEOJSON" \
    "$SHP"

  # GeoJSON → TopoJSON (fedele, nessuna semplificazione)
  mapshaper "$GEOJSON" -o format=topojson "$TOPOJSON"

  echo "  → $TOPOJSON"
done

echo "Done."
