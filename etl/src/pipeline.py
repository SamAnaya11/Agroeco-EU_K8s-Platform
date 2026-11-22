"""
pipeline.py
-----------
Ejecuta todo el proceso en orden (igual que en la versión de Azure):

    1. Descargar los datos de Eurostat
    2. Guardarlos tal cual                      -> <ETL_DIR_DATOS>/raw/<fecha>/
    3. Limpiar y transformar (modelo estrella)
    4. Guardar las tablas limpias en CSV        -> <ETL_DIR_DATOS>/processed/<fecha>/
    5. Cargar las tablas en PostgreSQL

Cambios respecto a la versión de Azure:
    - Blob Storage -> carpeta local (en Kubernetes, un volumen emptyDir).
    - Azure SQL    -> PostgreSQL, configurado con las variables PG* de libpq.
    - ETL_CARGAR_BD=false ejecuta solo extracción y limpieza (equivale al
      modo --local del original, pero se controla desde la configuración).

Variables de entorno:
    ETL_DIR_DATOS   carpeta para raw/ y processed/   (por defecto: ./data)
    ETL_CARGAR_BD   true | false                     (por defecto: true)
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD   (solo si ETL_CARGAR_BD=true)

El punto de entrada es main.py.
"""

import logging
import os
from datetime import date
from pathlib import Path

from src import almacenamiento, carga_sql, descarga, limpieza

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
RUTA_ESQUEMA = RAIZ / "sql" / "01_esquema.sql"


def variable_booleana(nombre: str, por_defecto: bool) -> bool:
    """Lee una variable de entorno true/false. Un valor no reconocido es un error, no un 'false'."""
    valor = os.environ.get(nombre, "").strip().lower()
    if valor == "":
        return por_defecto
    if valor in ("true", "1", "yes", "si", "sí"):
        return True
    if valor in ("false", "0", "no"):
        return False
    raise ValueError(f"Valor no válido para {nombre}: {valor!r} (usa true o false)")


def ejecutar_pipeline() -> dict:
    """Ejecuta el pipeline completo y devuelve un resumen."""
    fecha = date.today().isoformat()   # nombre de la carpeta de esta ejecución
    dir_datos = Path(os.environ.get("ETL_DIR_DATOS", RAIZ / "data"))
    cargar_bd = variable_booleana("ETL_CARGAR_BD", True)

    log.info(f">>> Inicio del pipeline ({fecha}) | datos en {dir_datos} | "
             f"carga en PostgreSQL: {'sí' if cargar_bd else 'no'}")

    # Si hay que cargar y falta configuración, mejor saberlo antes de descargar
    if cargar_bd:
        carga_sql.comprobar_configuracion()

    # 1 y 2. Descarga -> raw/
    log.info(">>> 1. Descarga desde Eurostat")
    archivos_raw = descarga.descargar_todo()
    for tabla, contenido in archivos_raw.items():
        almacenamiento.guardar(dir_datos, almacenamiento.CARPETA_RAW, f"{fecha}/{tabla}.tsv", contenido)
    almacenamiento.guardar(dir_datos, almacenamiento.CARPETA_RAW, f"{fecha}/fuente_datos.json",
                           descarga.metadatos_fuente())

    # 3 y 4. Limpieza -> processed/
    log.info(">>> 2. Limpieza con pandas")
    tablas = limpieza.limpiar(archivos_raw)
    for nombre, df in tablas.items():
        almacenamiento.guardar_csv(dir_datos, almacenamiento.CARPETA_PROCESSED, f"{fecha}/{nombre}.csv", df)

    # 5. Carga en PostgreSQL
    if not cargar_bd:
        log.info(">>> 3. Carga en PostgreSQL omitida (ETL_CARGAR_BD=false)")
        filas = {nombre: len(df) for nombre, df in tablas.items()}
    else:
        log.info(">>> 3. Carga en PostgreSQL")
        filas = carga_sql.cargar(tablas, RUTA_ESQUEMA)

    log.info(">>> Pipeline terminado correctamente")
    return {"fecha": fecha, "carga_bd": cargar_bd, "filas": filas}
