# Arquitetura — previsão de desertificação validada pelo NISAR

Versão 0.1 · 14/11/2026 · Substitui o escopo de inundação (mantido como histórico em `docs/literatura_nisar.md` e `pipeline/atlas_pareto.py`).

## 1. Tese e pergunta

**Tese:** a degradação de terras no semiárido avança com o aquecimento e com o uso do solo, e precisa de política pública de mitigação.

**Pergunta do modelo:** quais áreas dos 6 núcleos de desertificação vão entrar em degradação no próximo período, segundo o indicador ODS 15.3.1? E o NISAR confirma fisicamente as áreas que os satélites históricos apontam como degradadas?

| Papel | Fonte | Por quê |
|---|---|---|
| **Estabelece** a degradação (histórico) | MODIS NDVI 2000+, Landsat/HLS, MapBiomas, CHIRPS, SoilGrids | Séries longas exigidas pelo ODS 15.3.1 (baseline 15 anos) |
| **Faz a ponte** em banda L | Mosaicos anuais JAXA PALSAR/PALSAR-2 (2007–2010, 2015–2024, 25 m, gratuitos) | Mesmo comprimento de onda do NISAR, dando continuidade histórica do HV |
| **Valida** (presente) | NISAR GCOV (HV), L3 SME2 (umidade do solo), L2 GUNW (coerência InSAR) | Sinal físico independente do óptico |

## 2. Recorte

Os 6 núcleos oficiais (Atlas das Áreas Susceptíveis à Desertificação, MMA 2007): Gilbués-PI, Irauçuba-CE, Inhamuns-CE, Jaguaribe-CE, Cabrobó-PE, Seridó-RN/PB.

- Núcleo = conjunto de municípios. A geometria vem da malha IBGE (API v3) unindo os municípios de cada núcleo. **Pendente:** extrair a lista oficial de municípios do Atlas MMA 2007, porque não há shapefile oficial para download.
- Unidade de análise: célula de 250 m (grade MODIS). Agregação para município e núcleo na interface.

Cobertura NISAR verificada no CMR em 14/11/2026 (bbox aproximado de cada núcleo):

| Núcleo | GCOV V1 | GCOV provisório | GUNW provisório | SME2 provisório |
|---|---|---|---|---|
| Inhamuns | 8 | 103 | 94 | 101 |
| Jaguaribe | 6 | 58 | 53 | 57 |
| Gilbués | 6 | 52 | 46 | 52 |
| Seridó | 3 | 48 | 42 | 48 |
| Irauçuba | 4 | 37 | 34 | 37 |
| Cabrobó | 4 | 21 | 19 | 21 |

Os GCOV provisórios de Gilbués vão de jun a out/2026, ou seja, cobrem a estação seca.

## 3. Alvo: ODS 15.3.1 (metodologia UNCCD / Trends.Earth)

Três subindicadores por célula, combinados por **one-out-all-out** (se um degrada, a célula está degradada):

| Subindicador | Cálculo | Fonte |
|---|---|---|
| Produtividade | Trajetória (tendência Mann-Kendall do NDVI integrado anual, corrigida por chuva via RESTREND/RUE), estado (período recente vs baseline) e desempenho (vs vizinhos de mesma classe) | MOD13Q1 + CHIRPS |
| Cobertura | Transições degradantes (ex.: vegetação nativa → pastagem → solo exposto) | MapBiomas Coleção 10 |
| Carbono do solo | SOC de referência × fatores de mudança de uso | SoilGrids 250 m + MapBiomas |

Períodos: baseline 2001–2015 e relatórios 2016–2019 e 2020–2023, como a UNCCD. O período previsto é 2024–2027.

**Separar seca de desertificação.** NDVI cai em ano seco sem haver degradação. A correção por chuva (RESTREND/RUE) com CHIRPS é obrigatória, senão o modelo aprende "seca", não "degradação".

## 4. Modelo de previsão (adaptado do Simemap)

Base: `parceria_simemap/backend/analytics/energy_forecast.py`. Reaproveitamos a disciplina do Simemap: nenhum atributo vê o futuro, avaliação walk-forward por origem e modelos de referência ingênuos.

| Simemap | Desertificação |
|---|---|
| Série horária por placa | Série anual (e trimestral para NDVI) por célula |
| Lags 24…336 h | Lags de 1…5 anos de NDVI, RUE e chuva |
| Calendário (hora, fim de semana) | Fase ENSO, anomalia de chuva (SPI-12), ano |
| Alvo: potência (W) | Alvo 1: classe ODS 15.3.1 no próximo período (classificação). Alvo 2: NDVI integrado do próximo ano (regressão) |
| Baselines: mesmo horário de ontem/semana | Baselines: persistência da classe atual e tendência linear |
| `XGBRegressor` profundidade 2–4 | `XGBClassifier` / `XGBRegressor` profundidade 2–4, pesos por recência |

Atributos por célula: NDVI e lags, tendência e RUE; chuva CHIRPS e SPI; transições MapBiomas; SOC; declividade (Copernicus DEM); HV PALSAR anual e sua tendência; umidade SMAP (9 km, contexto).

Validação temporal: treinar até o período t e prever t+1, com origens em 2015, 2019 e 2023. Validação espacial: deixar um núcleo fora (leave-one-núcleo-out) para testar se o modelo generaliza.

## 5. Validação pelo NISAR

O NISAR não entra no treino. Ele testa se as classes previstas e observadas têm assinatura física coerente:

| Sinal NISAR | Hipótese em célula degradada | Teste |
|---|---|---|
| HV GCOV (gamma0, dB) | Menor (menos biomassa lenhosa da Caatinga) | Diferença de médias e AUC degradado vs estável; continuidade com a tendência HV do PALSAR-2 |
| Umidade do solo SME2 | Seca mais rápido após chuva (menor retenção) | Taxa de secagem entre passagens após evento CHIRPS |
| Coerência InSAR GUNW (12 dias) | Maior (solo exposto e estável) | Diferença de medianas e AUC |

Critério de sucesso: AUC > 0,7 em pelo menos 2 dos 3 sinais. Abaixo disso, reportamos como resultado negativo.

Cuidados:
- PALSAR-2 e NISAR têm calibrações diferentes. Comparar tendências e classes, não valores absolutos.
- SME2 e GUNW ainda são provisórios. Filtrar granules parciais e máscaras de validade (lição do estudo de Dhaka).
- O NISAR cobre jun–out/2026 (seca). Isso é bom para solo exposto e coerência, mas ruim para o contraste de umidade após chuva. Por isso, usar as passagens de novembro em diante.

## 6. Impacto e políticas (módulos mantidos)

- **Atlas, seca:** refazer o Pareto com COBRADE 14110/14120 restrito aos municípios dos núcleos (prejuízo IPCA, como em `pipeline/atlas_pareto.py`).
- **Políticas:** Lei 13.153/2015 (Política Nacional de Combate à Desertificação), PAB-Brasil 2024, planos estaduais (PAEs), Garantia-Safra, Operação Carro-Pipa (Portal da Transparência).
- **Responsáveis:** prefeitos 2024 (TSE), secretarias estaduais de meio ambiente, MMA/DCDE.
- **X:** rascunho copiável, publicado só após aprovação humana.

## 7. Docker compose

| Serviço | Imagem | Papel |
|---|---|---|
| `dg-db` | `postgis/postgis:16-3.4` | Dados, geometrias, resultados, fila de posts |
| `dg-app` | Python 3.12 + Streamlit | Mapa dos núcleos, classes ODS, previsão, validação NISAR, recomendações, aprovação de posts |
| `dg-worker` | Python 3.12 (mesma imagem) | Ingestão (earthaccess, CHIRPS, MapBiomas, PALSAR), cálculo ODS, treino e predição XGBoost, validação NISAR |

Dados brutos ficam num volume `data/` (não vão para o Postgres). O banco guarda agregados por célula e período.

## 8. Modelo de dados

```
cores(id, name, uf, geom)                                   -- 6 núcleos
municipalities(ibge_code, name, uf, core_id, geom, pop_2022)
cells(id, core_id, ibge_code, geom, slope, soc_ref)          -- grade 250 m

-- séries
cell_annual(cell_id, year, ndvi_int, rain_mm, spi12, rue, landcover, hv_palsar_db, sm_smap)
cell_quarterly(cell_id, quarter, ndvi_mean, rain_mm)

-- ODS 15.3.1
sdg_period(cell_id, period, productivity, landcover, soc, sdg_class)   -- -1 degradado, 0 estável, 1 melhora

-- previsão
model_runs(id, model, trained_until, params, metrics_json, created_at)
predictions(run_id, cell_id, period, p_degraded, pred_class, pred_ndvi)

-- NISAR
nisar_scenes(granule_id, product, track, frame, acquired_at, core_id, valid_fraction)
nisar_cell_obs(scene_id, cell_id, hv_db, soil_moisture, coherence)
nisar_validation(run_id, core_id, signal, auc, effect_size, n_cells, notes)

-- impacto e accountability
drought_events(protocolo, ibge_code, date, cobrade, loss_ipca_brl, affected)
policies(id, level, name, law_ref, url, verified_at)
authorities(id, ibge_code, role, name, agency, source_url, verified_at)
recommendations(id, core_id, category, action, evidence_json, limitations)
social_posts(id, recommendation_id, text, status, approved_by, approved_at, posted_url)
```

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Lista oficial de municípios dos núcleos não está em formato aberto | Extrair do PDF do Atlas MMA 2007 e documentar |
| MapBiomas e PALSAR são mais fáceis no Google Earth Engine | Confirmar se a equipe tem conta GEE; se não, baixar os mosaicos JAXA e o MapBiomas por download direto |
| Volume do MODIS 250 m em 6 núcleos × 25 anos | Recortar por bbox no download (earthaccess + rioxarray) |
| NISAR provisório | Reportar a versão do produto e os filtros de qualidade junto de cada número |

## 10. Fase 0 — teste da tese (antes de qualquer modelo)

Pergunta: **o NISAR enxerga a mesma degradação que os satélites de série longa?**

1. **Recorte** (`pipeline/nucleos.py`): 31 municípios em 6 núcleos, geometria IBGE. Não há delimitação oficial aberta; a fonte de cada lista está em `data/processed/nucleos_fontes.json`.
2. **Rótulo de referência sem NISAR** (`pipeline/gee_reference.py`, GEE), em ~3.000 pontos por núcleo a 250 m:
   - RESTREND: NDVI anual (MODIS 2001–2025) explicado pela chuva (CHIRPS). Resíduo com tendência negativa e Mann-Kendall p < 0,05 = **degradado**.
   - MapBiomas 2000 → 2023 e tendência HV PALSAR-2 2015–2024 entram como atributos de controle.
3. **NISAR nos mesmos pontos** (próximo script): HV do GCOV (mediana da estação seca de 2026), coerência do GUNW e umidade do SME2.
4. **Teste:**
   - AUC e Cliff's delta de cada sinal NISAR, degradado vs estável.
   - **Estratificado por classe MapBiomas.** Sem isso, o teste só reconhece "pastagem vs Caatinga", e não degradação.
   - Spearman entre o HV do NISAR e a tendência HV do PALSAR-2 (continuidade em banda L).
5. **Decisão:** AUC ≥ 0,7 em ≥ 2 sinais dentro das classes → tese sustentada, seguimos para o modelo. Caso contrário, reportamos o resultado negativo e revemos os sinais.
