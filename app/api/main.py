"""API somente leitura dos resultados pré-calculados (PostGIS).

O worker (app.worker.publish) carrega os resultados; aqui só consultamos.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import hmac
import re

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
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


@app.get("/api/recomendacoes")
def recomendacoes():
    """Recomendações do agente Desert Sentinel para todos os municípios (geradas no servidor)."""
    row = _one("SELECT conteudo, publicado_em FROM documentos WHERE nome = 'recomendacoes'")
    if not row:
        raise HTTPException(404, "recomendações ainda não geradas; rode o agente (perfil 'agente' do compose)")
    return {"publicado_em": row["publicado_em"].isoformat(), "municipios": row["conteudo"]}


def _rec(chave: str) -> dict:
    row = _one("SELECT conteudo -> %s AS r FROM documentos WHERE nome = 'recomendacoes'", (chave,))
    if not row or row["r"] is None:
        raise HTTPException(404, "sem recomendação para este município")
    return row["r"]


@app.get("/api/recomendacoes/{chave:path}/email.html", response_class=HTMLResponse)
def email_preview(chave: str):
    """Pré-visualização do e-mail da recomendação (não envia nada)."""
    from app.notify.email import render
    return HTMLResponse(render(_rec(chave))[1])


class EnvioEmail(BaseModel):
    para: list[str]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/recomendacoes/{chave:path}/email")
def email_send(chave: str, corpo: EnvioEmail, x_admin_token: str | None = Header(default=None)):
    """Envia a recomendação por e-mail (Brevo). Exige o cabeçalho X-Admin-Token = EMAIL_ADMIN_TOKEN."""
    from app.notify.email import EmailError, render, send
    token = os.environ.get("EMAIL_ADMIN_TOKEN", "")
    if not token:
        raise HTTPException(503, "envio de e-mail desligado (EMAIL_ADMIN_TOKEN não configurado)")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, token):
        raise HTTPException(401, "token inválido")
    para = [e.strip() for e in corpo.para if EMAIL_RE.match(e.strip())]
    if not para or len(para) != len(corpo.para):
        raise HTTPException(422, "lista de e-mails inválida")
    subject, body, text = render(_rec(chave))
    try:
        msg_id = send(para, subject, body, text)
    except EmailError as e:
        raise HTTPException(502, str(e))
    return {"enviado": True, "para": para, "assunto": subject, "message_id": msg_id}


@app.get("/api/recomendacoes/{chave:path}")
def recomendacao(chave: str):
    return _rec(chave)


@app.get("/api/figuras/{nome}")
def figura(nome: str):
    if nome not in FIGURAS:
        raise HTTPException(404)
    return FileResponse(BUNDLE / nome, media_type="image/png")
