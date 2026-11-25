# Imagen del ETL Agroeco-EU (Eurostat -> pandas -> PostgreSQL)
#
# La construye y publica GitHub Actions (.github/workflows/ci.yaml) en
# ghcr.io con la versión de appVersion (charts/agroeco-etl/Chart.yaml).
# Construcción local (desde la raíz del repositorio):
#   docker build --build-arg ETL_VERSION=0.2.1 -t agroeco-etl:0.2.1 etl/

# Base ligera y con versión fijada: Debian 13 (trixie) mínima con Python 3.14
FROM python:3.14.10-slim-trixie

# - Sin archivos .pyc (el sistema de archivos será de solo lectura en Kubernetes)
# - Salida sin búfer: los logs aparecen al momento en kubectl logs
# - pip sin caché ni aviso de versión: imagen más pequeña y logs más limpios
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Usuario sin privilegios con UID/GID numéricos fijos (Kubernetes puede
# verificar runAsNonRoot solo si el usuario es numérico)
RUN groupadd --system --gid 10001 etl \
 && useradd --system --uid 10001 --gid etl --no-create-home --home-dir /app --shell /usr/sbin/nologin etl

WORKDIR /app

# Dependencias primero: esta capa se reutiliza mientras requirements.txt no cambie
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código del ETL (propiedad de root y de solo lectura para el usuario etl)
COPY sql/ sql/
COPY src/ src/
COPY main.py .

# Carpeta de datos raw/processed. En Kubernetes se monta encima un emptyDir.
RUN mkdir /datos && chown etl:etl /datos
ENV ETL_DIR_DATOS=/datos

USER 10001:10001

# Versión del ETL, visible en la primera línea del log. Va al final para que
# cambiarla no invalide la caché de las capas anteriores (dependencias de pip).
ARG ETL_VERSION=desconocida
ENV ETL_VERSION=${ETL_VERSION}

ENTRYPOINT ["python", "main.py"]
