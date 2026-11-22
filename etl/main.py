"""
main.py
-------
Punto de entrada del ETL en el contenedor. Sustituye al temporizador de Azure
Functions: quien decide CUÁNDO se ejecuta es Kubernetes (un Job para una
ejecución puntual, un CronJob para la mensual). Este script ejecuta el
pipeline UNA sola vez y termina.

Código de salida (es lo que Kubernetes usa para saber cómo fue):
    0 -> todo correcto  -> el Job queda "Complete"
    1 -> error          -> el pod queda "Failed" y el Job reintenta según backoffLimit

Variables opcionales:
    ETL_NIVEL_LOG   DEBUG | INFO | WARNING | ERROR   (por defecto: INFO)
    PRUEBA_ALERTA   "1" provoca un fallo a propósito para probar la alerta
                    (mismo interruptor que en la versión de Azure)
"""

import json
import logging
import os
import sys

from src.pipeline import ejecutar_pipeline


def configurar_logs() -> None:
    """Logs a la salida estándar: Kubernetes los recoge y se leen con kubectl logs."""
    logging.basicConfig(
        level=os.environ.get("ETL_NIVEL_LOG", "INFO").upper(),
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
    )


def main() -> int:
    configurar_logs()
    log = logging.getLogger("main")

    if os.environ.get("PRUEBA_ALERTA") == "1":
        log.error("Fallo provocado a propósito para probar la alerta (PRUEBA_ALERTA=1)")
        return 1

    try:
        resumen = ejecutar_pipeline()
    except Exception:
        # Traza completa en el log y código de salida 1: el Job queda como fallido
        log.exception("El pipeline ha fallado")
        return 1

    log.info("Resumen: " + json.dumps(resumen, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
