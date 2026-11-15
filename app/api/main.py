"""API somente leitura dos resultados pré-calculados (PostGIS).

O worker (app.worker.publish) carrega os resultados; aqui só consultamos.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

BUNDLE = Path(os.environ.get("BUNDLE_DIR", Path(__file__).resolve().parents[1] / "bundle"))
pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=5, open=False,
                      kwargs={"row_factory": dict_row})
app = FastAPI(title="Climate Guardian — Desertificação", version="1.0",
              description="Resultados pré-calculados: degradação MODIS, validação NISAR, clima, suscetibilidade e SHAP.")
CAMADAS = {"suscetibilidade", "degradacao_modis", "pontos_nisar"}
FIGURAS = {"shap_detector_beeswarm.png", "shap_validador_beeswarm.png"}


@app.on_event("startup")
def _open():
    pool.open(wait=True, timeout=60)


def _one(sql: str, params=()):
    with pool.connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return row


@app.get("/api/health")
def health():
    row = _one("SELECT count(*) AS n FROM municipios")
    return {"status": "ok", "municipios": row["n"]}


@app.get("/api/meta")
def meta():
    row = _one("SELECT conteudo, publicado_em FROM documentos WHERE nome = 'meta'")
    if not row:
        raise HTTPException(503, "resultados ainda não publicados")
    return {**row["conteudo"], "publicado_em": row["publicado_em"].isoformat()}


@app.get("/api/municipios")
def municipios():
    row = _one("""
        SELECT json_build_object('type','FeatureCollection','features', coalesce(json_agg(json_build_object(
            'type','Feature','id',chave,'properties', resumo,'geometry', ST_AsGeoJSON(geom)::json)), '[]'::json)) AS fc
        FROM municipios""")
    return JSONResponse(row["fc"])


@app.get("/api/municipios/{chave:path}")
def municipio(chave: str):
    row = _one("SELECT resumo FROM municipios WHERE chave = %s", (chave,))
    if not row:
        raise HTTPException(404, "município não encontrado")
    return row["resumo"]


@app.get("/api/camadas/{camada}")
def camada(camada: str, municipio: str | None = None):
    if camada not in CAMADAS:
        raise HTTPException(404, f"camada desconhecida; use {sorted(CAMADAS)}")
    row = _one("""
        SELECT json_build_object('type','FeatureCollection','features', coalesce(json_agg(json_build_object(
            'type','Feature','properties', props,'geometry', ST_AsGeoJSON(geom, 5)::json)), '[]'::json)) AS fc
        FROM camadas WHERE camada = %s AND (%s::text IS NULL OR municipio LIKE %s || '%%')""",
               (camada, municipio, municipio))
    return JSONResponse(row["fc"])


@app.get("/api/shap/{modelo}")
def shap(modelo: str):
    row = _one("SELECT conteudo FROM documentos WHERE nome = %s", (f"shap_{modelo}_global",))
    if not row:
        raise HTTPException(404, "modelo desconhecido; use detector ou validador")
    return row["conteudo"]


@app.get("/api/figuras/{nome}")
def figura(nome: str):
    if nome not in FIGURAS:
        raise HTTPException(404)
    return FileResponse(BUNDLE / nome, media_type="image/png")
