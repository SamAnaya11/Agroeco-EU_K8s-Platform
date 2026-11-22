-- =====================================================================
-- 01_esquema.sql
-- Modelo en estrella de la base de datos (PostgreSQL)
--
-- Traducción de la versión T-SQL (Azure SQL) del proyecto serverless. Las
-- tablas, columnas, claves y la vista son las mismas; solo cambian los tipos
-- de datos y la sintaxis propia de cada motor:
--
--   T-SQL (Azure SQL)        PostgreSQL              Motivo
--   -----------------------  ----------------------  ------------------------------------
--   NVARCHAR(n)              VARCHAR(n)              PostgreSQL guarda todo el texto en
--                                                    UTF-8: no hay tipo "N" aparte
--   FLOAT                    DOUBLE PRECISION        mismo tipo (8 bytes), nombre explícito
--   BIT                      SMALLINT CHECK (0, 1)   BIT en PostgreSQL es una cadena de
--                                                    bits, no un booleano; se mantienen
--                                                    los valores 0/1 que genera la limpieza
--   lotes separados por GO   sin GO                  GO no es SQL (lo interpretan las
--                                                    herramientas cliente); psycopg
--                                                    ejecuta el script completo
--   DROP TABLE IF EXISTS     ... CASCADE             borra también lo que dependa de la
--                                                    tabla (claves foráneas, vista)
--
--                     ┌──< fact_superficie >── dim_cultivo
--      dim_pais 1 ────┼──< fact_pct_sau
--                     ├──< fact_operadores
--                     └──< fact_ganaderia
--
-- El ETL ejecuta este script dentro de la misma transacción que la carga:
-- si la carga falla, el rollback deshace también los DROP y CREATE.
-- =====================================================================

-- Se borra todo y se vuelve a crear en cada carga (igual que en el original).
DROP VIEW  IF EXISTS v_superficie_total;
DROP TABLE IF EXISTS fact_superficie CASCADE;
DROP TABLE IF EXISTS fact_pct_sau    CASCADE;
DROP TABLE IF EXISTS fact_operadores CASCADE;
DROP TABLE IF EXISTS fact_ganaderia  CASCADE;
DROP TABLE IF EXISTS dim_cultivo     CASCADE;
DROP TABLE IF EXISTS dim_pais        CASCADE;

-- ---------------------------------------------------------------------
-- Dimensiones
-- ---------------------------------------------------------------------
CREATE TABLE dim_pais (
    codigo_pais  VARCHAR(20)   NOT NULL PRIMARY KEY,   -- código Eurostat (ES, FR, EU27_2020...)
    pais         VARCHAR(100)  NOT NULL UNIQUE,
    es_agregado  SMALLINT      NOT NULL CHECK (es_agregado IN (0, 1))  -- 1 = total de la UE, 0 = país
);

CREATE TABLE dim_cultivo (
    codigo_cultivo  VARCHAR(20)   NOT NULL PRIMARY KEY, -- código Eurostat (O1000, W1000...)
    cultivo         VARCHAR(100)  NOT NULL UNIQUE,
    grupo           VARCHAR(50)   NOT NULL,
    nivel           VARCHAR(10)   NOT NULL CHECK (nivel IN ('total', 'grupo', 'cultivo'))
);

-- ---------------------------------------------------------------------
-- Hechos
-- ---------------------------------------------------------------------
CREATE TABLE fact_superficie (
    anio            INTEGER           NOT NULL,
    codigo_pais     VARCHAR(20)       NOT NULL REFERENCES dim_pais (codigo_pais),
    codigo_cultivo  VARCHAR(20)       NOT NULL REFERENCES dim_cultivo (codigo_cultivo),
    metodo          VARCHAR(15)       NOT NULL CHECK (metodo IN ('total', 'convertida', 'en_conversion')),
    superficie_ha   DOUBLE PRECISION  NOT NULL CHECK (superficie_ha >= 0),
    nota            VARCHAR(30),                       -- estimado, provisional...
    PRIMARY KEY (anio, codigo_pais, codigo_cultivo, metodo)
);

CREATE TABLE fact_pct_sau (
    anio               INTEGER           NOT NULL,
    codigo_pais        VARCHAR(20)       NOT NULL REFERENCES dim_pais (codigo_pais),
    pct_sau_ecologica  DOUBLE PRECISION  NOT NULL CHECK (pct_sau_ecologica BETWEEN 0 AND 100),
    nota               VARCHAR(30),
    PRIMARY KEY (anio, codigo_pais)
);

CREATE TABLE fact_operadores (
    anio           INTEGER      NOT NULL,
    codigo_pais    VARCHAR(20)  NOT NULL REFERENCES dim_pais (codigo_pais),
    tipo_operador  VARCHAR(50)  NOT NULL,
    numero         INTEGER      NOT NULL CHECK (numero >= 0),
    nota           VARCHAR(30),
    PRIMARY KEY (anio, codigo_pais, tipo_operador)
);

CREATE TABLE fact_ganaderia (
    anio         INTEGER      NOT NULL,
    codigo_pais  VARCHAR(20)  NOT NULL REFERENCES dim_pais (codigo_pais),
    especie      VARCHAR(50)  NOT NULL,
    cabezas      INTEGER      NOT NULL CHECK (cabezas >= 0),
    nota         VARCHAR(30),
    PRIMARY KEY (anio, codigo_pais, especie)
);

CREATE INDEX idx_superficie_cultivo ON fact_superficie (codigo_cultivo);

-- ---------------------------------------------------------------------
-- Vista de apoyo: superficie ecológica total por país y año
-- (en PostgreSQL CREATE VIEW no necesita ir sola en su lote)
-- ---------------------------------------------------------------------
CREATE VIEW v_superficie_total AS
SELECT
    s.anio,
    p.codigo_pais,
    p.pais,
    p.es_agregado,
    SUM(CASE WHEN s.metodo = 'total'         THEN s.superficie_ha END) AS total_ha,
    SUM(CASE WHEN s.metodo = 'convertida'    THEN s.superficie_ha END) AS convertida_ha,
    SUM(CASE WHEN s.metodo = 'en_conversion' THEN s.superficie_ha END) AS en_conversion_ha
FROM fact_superficie AS s
JOIN dim_pais        AS p ON p.codigo_pais = s.codigo_pais
WHERE s.codigo_cultivo = 'UAAXK0000'
GROUP BY s.anio, p.codigo_pais, p.pais, p.es_agregado;
