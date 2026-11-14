"""Núcleos de desertificação: municípios + geometria IBGE.

Não há delimitação oficial única em formato aberto. Usamos o recorte mais
citado de cada núcleo e registramos a fonte. Trocar a lista aqui muda tudo
o que vem depois (GEE, NISAR, Atlas).

Geometria: API de malhas do IBGE v3 (malha municipal vigente).

Uso:
    python -m pipeline.nucleos
"""

from __future__ import annotations

import gzip
import json
import unicodedata
import urllib.request

from pipeline.config import DATA_PROCESSED, DATA_RAW

NUCLEOS = {
    "gilbues": {
        "nome": "Gilbués",
        "uf": ["PI"],
        "municipios": ["Gilbués", "Monte Alegre do Piauí"],
        "fonte": "Embrapa (2008), banco de dados geográficos de Gilbués e Monte Alegre do Piauí; "
                 "núcleo citado como ~15 municípios afetados direta ou indiretamente (PNCD), sem lista aberta.",
    },
    "serido": {
        "nome": "Seridó",
        "uf": ["RN"],
        "municipios": ["Currais Novos", "Acari", "Parelhas", "Equador", "Carnaúba dos Dantas",
                       "Caicó", "Jardim do Seridó", "Cruzeta"],
        "fonte": "NÃO VERIFICADA na fonte primária. Lista vinda de resumo de busca que atribui 7 municípios ao "
                 "PAN-Brasil (2004) + Cruzeta (PAE/RN 2010). O PAE/RN 2010, citado por Pereira Neto et al. (2024, "
                 "GeoInterações 8(1)), menciona Caicó, São José do Seridó e Parelhas. Confirmar no PAE/RN 2010.",
    },
    "iraucuba": {
        "nome": "Irauçuba / Centro-Norte",
        "uf": ["CE"],
        "municipios": ["Irauçuba", "Itapajé", "Miraíma", "Sobral", "Santa Quitéria", "Canindé"],
        "fonte": "Funceme (2015), citado por repositório UFC; ~12.200 km².",
    },
    "inhamuns": {
        "nome": "Inhamuns",
        "uf": ["CE"],
        "municipios": ["Tauá", "Independência", "Arneiroz"],
        "fonte": "Estudos UFC/Funceme sobre o núcleo dos Inhamuns.",
    },
    "jaguaribe": {
        "nome": "Médio Jaguaribe",
        "uf": ["CE"],
        "municipios": ["Alto Santo", "Iracema", "Jaguaretama", "Jaguaribara", "Jaguaribe",
                       "São João do Jaguaribe", "Solonópole"],
        "fonte": "Estudo de 2009 (médio e baixo Jaguaribe); sem lista oficial confirmada.",
    },
    "cabrobo": {
        "nome": "Cabrobó",
        "uf": ["PE"],
        "municipios": ["Cabrobó", "Belém do São Francisco", "Itacuruba", "Carnaubeira da Penha", "Floresta"],
        "fonte": "Recorte mais citado (PAN-Brasil); INSA inclui Parnamirim e Salgueiro e exclui Carnaubeira da Penha.",
    },
}

IBGE_MUN_UF = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
IBGE_MALHA_UF = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}"
                 "?intrarregiao=municipio&qualidade=intermediaria&formato=application/vnd.geo%2Bjson")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower().replace("-", " ").strip()


def _get(url: str, cache_name: str):
    cache = DATA_RAW / "ibge" / cache_name
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as r:
            body = r.read()
        if body[:2] == b"\x1f\x8b":  # a API do IBGE responde gzip mesmo sem pedir
            body = gzip.decompress(body)
        cache.write_bytes(body)
    return json.loads(cache.read_text(encoding="utf-8"))


def main() -> None:
    features, rows, missing = [], [], []
    for key, n in NUCLEOS.items():
        for uf in n["uf"]:
            muns = _get(IBGE_MUN_UF.format(uf=uf), f"municipios_{uf}.json")
            malha = _get(IBGE_MALHA_UF.format(uf=uf), f"malha_{uf}.geojson")
            by_name = {_norm(m["nome"]): str(m["id"]) for m in muns}
            geom_by_code = {str(f["properties"]["codarea"]): f["geometry"] for f in malha["features"]}
            for nome in n["municipios"]:
                code = by_name.get(_norm(nome))
                if not code or code not in geom_by_code:
                    missing.append(f"{nome}/{uf}")
                    continue
                rows.append({"nucleo": key, "nucleo_nome": n["nome"], "municipio": nome, "uf": uf, "ibge": code})
                features.append({
                    "type": "Feature",
                    "properties": {"nucleo": key, "nucleo_nome": n["nome"], "municipio": nome, "uf": uf, "ibge": code},
                    "geometry": geom_by_code[code],
                })
    if missing:
        raise SystemExit(f"Municípios não encontrados no IBGE: {missing}")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    (DATA_PROCESSED / "nucleos_municipios.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    (DATA_PROCESSED / "nucleos_fontes.json").write_text(
        json.dumps(NUCLEOS, ensure_ascii=False, indent=2), encoding="utf-8")
    for key in NUCLEOS:
        sel = [r for r in rows if r["nucleo"] == key]
        print(f"{key:10s} {len(sel):2d} municípios: " + ", ".join(f"{r['municipio']} ({r['ibge']})" for r in sel))


if __name__ == "__main__":
    main()
