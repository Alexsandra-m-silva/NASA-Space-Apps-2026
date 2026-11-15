# Modelo de degradação / desertificação validado pelo NISAR

Branch `modelo-desertificacao`. Código em `pipeline/`, resultados resumidos em `docs/resultados/`.
Dados brutos e processados ficam em `data/` (fora do git) e são regenerados pelos scripts.

## Configuração

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # EARTHDATA_USERNAME, EARTHDATA_PASSWORD (ASF DAAC autorizado), GEE_PROJECT
.venv/Scripts/earthengine authenticate
```

## Fluxo

| Etapa | Script | O que faz |
|---|---|---|
| Recorte | `nucleos.py`, `tese.py <area> points` | Municípios (malha IBGE) e pontos de amostra |
| Degradação MODIS | `poligonos.py gee <area>` | RESTREND 2001–2024 (NDVI − chuva CHIRPS), classes degradado / controle / melhora, polígonos 250 m |
| Degradação 30 m | `degradacao_30m.py download\|polygons` | Mesmo método com Landsat 5/7/8/9 (OLI harmonizado + calibração cruzada L7/L8) |
| Evidências | `evidencias.py download\|polygons` | Convergência a 30 m: desmatamento, solo exposto, pastagem de vigor baixo, queda de NDVI, fogo (MapBiomas Col. 10) |
| NISAR | `tese.py <area> nisar` | GCOV (HH/HV, jun–out/2026) lido direto da nuvem; features HV, HH, HV/HH, textura, variação temporal |
| Validação NISAR | `tese.py analyze-poligonos` | XGBoost, blocos espaciais de ~11 km: AUC 0,76 (14 municípios) |
| Clima | `clima_5.py` | Chuva, temperatura, ETP, aridez 1991–2024 (CHIRPS, ERA5-Land) |
| Suscetibilidade | `suscetibilidade_5.py` | Índice de 5 componentes, validado pelo NISAR (ρ = 0,49) |
| Correlações | `correlacoes_nisar.py`, `variacao_temporal.py` | NISAR × MapBiomas, MODIS, clima (estado e variação data a data) |
| Utilidade do NISAR | `modelo_previsao.py` | Ablação: NISAR soma +0,10 de AUC na detecção de conversão da Caatinga |
| Brasil, 12 meses | `brasil_previsao.py sample\|validate\|export\|download` | Modelo híbrido do Simemap (sinal de série temporal + gradient boosting), walk-forward, GeoTIFF nacional 1 km |

## Principais resultados

Ver `docs/resultados/RESULTADO_5_MUNICIPIOS.md`, `modelo_previsao.md`, `correlacoes_nisar.md` e `variacao_temporal.md`.

## Limites

- NISAR provisório e só estação seca de 2026 (desde jun/2026 sobre a área de estudo).
- O gabarito é tendência de NDVI e MapBiomas, não medição de campo; degradação vegetal ≠ desertificação comprovada.
- O mapa nacional usa MODIS, clima e MapBiomas; o NISAR é validado regionalmente na Caatinga.
- Lista de municípios dos núcleos montada a partir da literatura (sem shapefile oficial aberto).

## Aplicação (docker compose)

```bash
docker compose up --build -d     # http://localhost:8090  (WEB_PORT muda a porta)
```

Os modelos já rodaram: o `dg-worker` publica `app/bundle/` (resultados versionados, ~4 MB) no PostGIS e termina;
a `dg-api` (FastAPI) só lê; o `dg-web` (nginx) serve `web/modelo.html` e as páginas da equipe e encaminha `/api`.
Nada é calculado no navegador e não é preciso credencial para subir.

| Endpoint | Conteúdo |
|---|---|
| `/api/health`, `/api/meta` | estado e métricas principais |
| `/api/municipios`, `/api/municipios/{nome}/{uf}` | resumo por município (MODIS, NISAR, clima, suscetibilidade, SHAP) |
| `/api/camadas/{suscetibilidade,degradacao_modis,pontos_nisar}?municipio=` | GeoJSON |
| `/api/shap/{detector,validador}`, `/api/figuras/{nome}.png` | explicação global e gráficos SHAP |
| `/docs` | Swagger (documentação interativa da API) |
| `/comparar/` | Comparar e explicar: escolha o município, desenhe um retângulo; NDVI 2001–2024 descontada a chuva (RESTREND + Mann-Kendall), NISAR HV em dB, chuva e temperatura |

Reprocessar (exige `.env` com Earthdata e GEE):

```bash
docker compose --profile pipeline run --rm dg-pipeline python -m pipeline.shap_modelos
docker compose --profile pipeline run --rm dg-pipeline python -m pipeline.bundle
docker compose up -d --force-recreate dg-worker
```

### Cubos do "Comparar e explicar"

```bash
python -m pipeline.cubos_ndvi modis             # NDVI e chuva anuais 2001–2024 (GEE), grade 0,01°
python -m pipeline.cubos_ndvi nisar <slug>      # NISAR GCOV HV/HH em dB (Earthdata), uma órbita por município
python -m pipeline.cubos_ndvi build             # products/<slug>_ndvi.npz/.json e products/ndvi_index.json
```
