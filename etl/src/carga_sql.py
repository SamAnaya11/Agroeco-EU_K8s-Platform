"""
carga_sql.py
------------
Crea las tablas en PostgreSQL a partir de sql/01_esquema.sql y carga en ellas
las tablas limpias. La lógica es la misma que en la versión de Azure SQL;
cambian el driver y algunos detalles de SQL:

    Azure SQL (mssql-python)              PostgreSQL (psycopg 3)
    ------------------------------------  ------------------------------------
    cadena de conexión en una variable    variables estándar de libpq: PGHOST,
    (SQL_CADENA_CONEXION)                 PGPORT, PGDATABASE, PGUSER, PGPASSWORD
    marcadores ?                          marcadores %s
    esquema dividido por líneas "GO"      un solo script (psycopg admite varias
                                          sentencias si no lleva parámetros)
    reintentos: la BD gratuita se pausa   reintentos: la BD puede estar
    (6 intentos x 30 s)                   arrancando o en failover (6 x 10 s)

Se mantiene igual:
    - Todo en UNA transacción. En PostgreSQL también los DROP y CREATE son
      transaccionales: si algo falla a mitad, el rollback deja las tablas y
      los datos de la carga anterior intactos.
    - Recuento final de filas por tabla.

Las credenciales nunca están en el código: en Kubernetes llegan desde un
Secret como variables de entorno.
"""

import logging
import os
import time
from pathlib import Path

import pandas as pd
import psycopg

from src.limpieza import ORDEN_TABLAS

log = logging.getLogger(__name__)

INTENTOS_CONEXION = 6        # 6 intentos x 10 s = hasta 1 minuto (cubre un failover)
ESPERA_SEGUNDOS = 10
TIEMPO_ESPERA_CONEXION = 15  # segundos máximos por cada intento de conexión

# Variables que libpq necesita sí o sí (PGPORT es opcional: 5432 por defecto)
VARIABLES_OBLIGATORIAS = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")


def comprobar_configuracion() -> None:
    """Falla al principio, antes de descargar nada, si falta alguna variable de conexión."""
    faltan = [v for v in VARIABLES_OBLIGATORIAS if not os.environ.get(v)]
    if faltan:
        raise RuntimeError(f"Faltan variables de entorno para conectar a PostgreSQL: {', '.join(faltan)}")


def descripcion_conexion() -> str:
    """Destino de la conexión para el log. Nunca incluye la contraseña."""
    return (f"{os.environ['PGUSER']}@{os.environ['PGHOST']}:"
            f"{os.environ.get('PGPORT', '5432')}/{os.environ['PGDATABASE']}")


def conectar() -> psycopg.Connection:
    """Abre la conexión con PostgreSQL, reintentando si el servidor aún no responde."""
    log.info(f"     Conectando a PostgreSQL ({descripcion_conexion()})")
    for intento in range(1, INTENTOS_CONEXION + 1):
        try:
            # Sin cadena de conexión: libpq toma host, base de datos, usuario y
            # contraseña de las variables PG* del entorno.
            return psycopg.connect(connect_timeout=TIEMPO_ESPERA_CONEXION,
                                   application_name="agroeco-etl")
        except psycopg.OperationalError as error:
            # Una contraseña incorrecta no se arregla esperando: se falla ya.
            if intento == INTENTOS_CONEXION or "password authentication failed" in str(error):
                raise
            log.warning(f"     No se pudo conectar (intento {intento}/{INTENTOS_CONEXION}). "
                        f"Reintento en {ESPERA_SEGUNDOS} s. Detalle: {str(error).strip()}")
            time.sleep(ESPERA_SEGUNDOS)


def filas_para_sql(df: pd.DataFrame) -> list[tuple]:
    """
    Convierte un DataFrame en una lista de tuplas para insertar en SQL (sin cambios).
      - astype(object) convierte los números de numpy en números de Python.
      - where(..., None) cambia los NaN (valores vacíos de pandas) por None,
        que el driver guarda como NULL.
    """
    limpio = df.astype(object).where(df.notna(), None)
    return list(limpio.itertuples(index=False, name=None))


def cargar(tablas: dict[str, pd.DataFrame], ruta_esquema: Path) -> dict[str, int]:
    """Crea el esquema, inserta todas las tablas y devuelve cuántas filas tiene cada una."""
    esquema = ruta_esquema.read_text(encoding="utf-8")

    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            # 1. Borrar y crear tablas y vista (script completo, sin parámetros)
            cursor.execute(esquema)
            log.info("     Esquema creado")

            # 2. Insertar los datos: primero dimensiones, después hechos
            for nombre in ORDEN_TABLAS:
                df = tablas[nombre]
                columnas = ", ".join(df.columns)
                marcadores = ", ".join(["%s"] * len(df.columns))
                cursor.executemany(f"INSERT INTO {nombre} ({columnas}) VALUES ({marcadores})",
                                   filas_para_sql(df))
                log.info(f"     {nombre:<16} -> {len(df):>6,} filas insertadas".replace(",", "."))

            # 3. Confirmar todo de una vez
            conexion.commit()

            # 4. Comprobación rápida (igual que en el original)
            recuento = {}
            for nombre in ORDEN_TABLAS:
                cursor.execute(f"SELECT COUNT(*) FROM {nombre}")
                recuento[nombre] = cursor.fetchone()[0]
        log.info(f"[OK] Carga en PostgreSQL terminada: {recuento}")
        return recuento

    except Exception:
        conexion.rollback()   # deja la base de datos como estaba antes
        log.error("     Error durante la carga: se deshacen todos los cambios (rollback)")
        raise
    finally:
        conexion.close()
