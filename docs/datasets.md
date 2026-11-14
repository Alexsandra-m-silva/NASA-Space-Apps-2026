# Fontes de dados — Climate Guardian

Testado em 14/11/2026. "OK" = endpoint respondeu; não significa que o dado foi validado para o recorte.

## Recorte e impacto (base do Pareto 80%)

| Fonte | Uso | Acesso | Status |
|---|---|---|---|
| Atlas Digital de Desastres no Brasil (Sedec/MIDR, Ceped/UFSC) | Ocorrências, danos humanos, danos materiais e prejuízos 1991–2025 por município e COBRADE | [downloads](https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml): `BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.xlsx` (aba *Valores Originais*) | OK, processado em `pipeline/atlas_pareto.py` |
| IPCA — BCB SGS 433 | Correção monetária até o último mês publicado | `api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json` | OK |
| IBGE Localidades + Malhas v3 | Códigos IBGE, geometria municipal (GeoJSON) para AOI | `servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}` | OK |
| IBGE SIDRA (Censo 2022, tabela 4709) | População, para normalizar prejuízo per capita | `apisidra.ibge.gov.br/values/t/4709/n6/{cod}/v/93/p/2022` | OK |

## Observação da Terra (série temporal de área inundada)

| Fonte | Uso | Acesso | Status |
|---|---|---|---|
| NISAR L2 GCOV (V1 e PROVISIONAL_V1) | Área inundada por passagem (HH gamma0) | earthaccess / CMR | OK. Blumenau: 3 granules V1 + 27 provisórios → série curta |
| OPERA DSWx-S1 (NASA/JPL) | Máscara de água a 30 m do Sentinel-1, para alongar a série e calibrar o limiar NISAR | earthaccess `OPERA_L3_DSWX-S1_V1` | OK. Blumenau: 449 granules desde 22/08/2024 |
| MapBiomas Água | Superfície de água mensal desde 1985 (Landsat): histórico longo e sazonalidade | [plataforma](https://plataforma.agua.mapbiomas.org/) / GEE | Site OK; exportação por município a confirmar |
| GPM IMERG Late daily (GES DISC) | Chuva entre passagens (exógena) | earthaccess `GPM_3IMERGDL` v07 | Já no pipeline |
| CHIRPS v2.0 daily (UCSB CHC) | Chuva diária desde 1981, para treino longo | `data.chc.ucsb.edu/products/CHIRPS/v2.0/global_daily/` | OK |
| ANA HidroWeb / telemetria | Nível e vazão de rios (exógena forte para cheias) | `telemetriaws1.ana.gov.br/ServiceANA.asmx` (SOAP/XML) | Serviço OK; série precisa do código certo da estação |
| GloFAS (Copernicus CEMS) | Vazão simulada/prevista, onde não há estação | EWDS (cadastro) | Redireciona para login; não testado |

## Accountability e políticas

| Fonte | Uso | Status |
|---|---|---|
| TSE Dados Abertos (CKAN) | Prefeitos e vereadores eleitos em 2024 | OK |
| Câmara dos Deputados API v2 | Deputados por UF, proposições | OK |
| Senado Dados Abertos | Senadores em exercício, matérias | OK (XML) |
| LexML (SRU) | Leis e decretos (ex.: planos de contingência, defesa civil) | OK |
| Portal da Transparência API | Transferências federais de defesa civil por município | OK (exige chave gratuita) |
| OpenAlex | Evidência científica | OK |
| SGB/CPRM — setorização de áreas de risco | Polígonos de risco alto/muito alto por município | RIGEO OK; GeoSGB não respondeu |
| AdaptaBrasil (MCTI) | Índices de risco de inundação por município | API retornou 403; usar exportação do site |
| CEMADEN | Municípios monitorados, pluviômetros | Mapa OK; API REST testada não respondeu |
