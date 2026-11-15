"""Publica o pacote de resultados (app/bundle) no PostGIS.

Roda uma vez quando o compose sobe (serviço dg-worker) e termina. Idempotente:
recarrega tudo numa transação. A API só lê o que está aqui; nada é calculado no navegador.

Uso: python -m app.worker.publish
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psycopg

BUNDLE = Path(os.environ.get("BUNDLE_DIR", Path(__file__).resolve().parents[1] / "bundle"))

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS municipios (
    chave text PRIMARY KEY, nome text, uf text, ibge text, resumo jsonb,
    geom geometry(Geometry, 4326));
CREATE TABLE IF NOT EXISTS camadas (
    id bigserial PRIMARY KEY, camada text NOT NULL, municipio text, props jsonb,
    geom geometry(Geometry, 4326));
CREATE INDEX IF NOT EXISTS camadas_camada_idx ON camadas (camada, municipio);
CREATE INDEX IF NOT EXISTS camadas_geom_idx ON camadas USING gist (geom);
CREATE TABLE IF NOT EXISTS documentos (nome text PRIMARY KEY, conteudo jsonb, publicado_em timestamptz DEFAULT now());
"""

LAYERS = {
    "suscetibilidade": "suscetibilidade.geojson",
    "degradacao_modis": "degradacao_modis.geojson",
    "pontos_nisar": "pontos_nisar.geojson",
}


def _load(name: str):
    return json.loads((BUNDLE / name).read_text(encoding="utf-8"))


def _connect(url: str, tries: int = 30):
    for i in range(tries):
        try:
            return psycopg.connect(url)
        except psycopg.OperationalError:
            time.sleep(2)
    raise SystemExit("PostGIS não respondeu")


def main() -> None:
    url = os.environ["DATABASE_URL"]
    with _connect(url) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("TRUNCATE municipios, camadas RESTART IDENTITY")
        # As recomendações do agente (Desert Sentinel) são geradas no servidor e não estão no bundle:
        # preservadas aqui, a não ser que o bundle traga uma versão nova.
        cur.execute("DELETE FROM documentos WHERE nome <> 'recomendacoes'")

        resumo = {r["chave"]: r for r in _load("municipios_resumo.json")}
        for f in _load("municipios.geojson")["features"]:
            p = f["properties"]
            chave = f'{p["municipio"]}/{p["uf"]}'
            cur.execute("INSERT INTO municipios VALUES (%s,%s,%s,%s,%s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))",
                        (chave, p["municipio"], p["uf"], p.get("ibge"), json.dumps(resumo.get(chave), ensure_ascii=False),
                         json.dumps(f["geometry"])))

        for camada, arquivo in LAYERS.items():
            rows = [(camada, f["properties"].get("municipio"), json.dumps(f["properties"], ensure_ascii=False),
                     json.dumps(f["geometry"])) for f in _load(arquivo)["features"]]
            cur.executemany("INSERT INTO camadas (camada, municipio, props, geom) "
                            "VALUES (%s,%s,%s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))", rows)
            print(f"{camada}: {len(rows)} feições", flush=True)

        docs = ["meta.json", "shap_detector_global.json", "shap_validador_global.json"]
        if (BUNDLE / "recomendacoes.json").exists():  # gerado pelo agente Desert Sentinel (app.agent.sentinel)
            docs.append("recomendacoes.json")
        for nome in docs:
            cur.execute("INSERT INTO documentos (nome, conteudo) VALUES (%s,%s) ON CONFLICT (nome) DO UPDATE "
                        "SET conteudo = EXCLUDED.conteudo, publicado_em = now()",
                        (nome.removesuffix(".json"), json.dumps(_load(nome), ensure_ascii=False)))
        conn.commit()
    print("publicado:", len(resumo), "municípios", flush=True)


if __name__ == "__main__":
    main()
