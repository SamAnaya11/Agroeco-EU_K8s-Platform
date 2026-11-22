"""
almacenamiento.py
-----------------
Guarda los archivos de cada ejecución en una carpeta local. Sustituye a Azure
Blob Storage de la versión serverless, con los mismos dos "contenedores"
(raw y processed) como subcarpetas y la misma estructura por fecha:

    <dir_datos>/raw/2026-12-01/org_cropar.tsv
    <dir_datos>/raw/2026-12-01/fuente_datos.json
    <dir_datos>/processed/2026-12-01/dim_pais.csv
    ...

En Kubernetes <dir_datos> es un volumen emptyDir: existe mientras vive el pod
y se borra al terminar. El destino persistente de los datos es PostgreSQL;
estos archivos sirven para inspeccionar una ejecución mientras dura.
"""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

CARPETA_RAW = "raw"
CARPETA_PROCESSED = "processed"


def guardar(dir_datos: Path, carpeta: str, ruta: str, datos: bytes) -> None:
    """Guarda (o sobrescribe) un archivo en <dir_datos>/<carpeta>/<ruta>."""
    destino = dir_datos / carpeta / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    log.info(f"     Guardado {carpeta}/{ruta} ({len(datos) / 1024:,.0f} KB)")


def guardar_csv(dir_datos: Path, carpeta: str, ruta: str, df: pd.DataFrame) -> None:
    """Convierte un DataFrame en CSV (UTF-8, igual que el original) y lo guarda."""
    guardar(dir_datos, carpeta, ruta, df.to_csv(index=False).encode("utf-8"))
