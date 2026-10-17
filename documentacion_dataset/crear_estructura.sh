#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DATASET_DIR="$PROJECT_ROOT/dataset"
SCHEMA_FILE="$SCRIPT_DIR/schema.sql"

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "Se requiere Python 3 para crear dataset/metadata.sqlite." >&2
  exit 1
fi

mkdir -p \
  "$DATASET_DIR/superior/abrigos" \
  "$DATASET_DIR/superior/blusas" \
  "$DATASET_DIR/superior/camisas" \
  "$DATASET_DIR/superior/chaquetas" \
  "$DATASET_DIR/superior/sueteres" \
  "$DATASET_DIR/inferior/faldas/FALDA-1" \
  "$DATASET_DIR/inferior/faldas/FALDA-2" \
  "$DATASET_DIR/inferior/pantalones" \
  "$DATASET_DIR/inferior/shorts" \
  "$DATASET_DIR/inferior_superior/vestido"

python3 - "$SCHEMA_FILE" "$DATASET_DIR/metadata.sqlite" <<'PY'
import sqlite3
import sys
from pathlib import Path

schema_path = Path(sys.argv[1])
database_path = Path(sys.argv[2])
schema = schema_path.read_text(encoding="utf-8")

with sqlite3.connect(database_path) as connection:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(prenda_imagen)")}
    if "etiqueta_fuente" not in columns:
        connection.execute("ALTER TABLE prenda_imagen ADD COLUMN etiqueta_fuente TEXT")
    foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    if foreign_keys_enabled != 1:
        raise RuntimeError("No se pudieron activar las claves foráneas de SQLite.")
PY

printf '%s\n' "Estructura del dataset y base SQLite verificadas/creadas."
