# Revisão de literatura — tese e uso do NISAR

Levantamento em 14/11/2026. Tese: **desastres hídricos estão aumentando com o aquecimento global, e são necessárias políticas públicas de mitigação/adaptação.** Restrição: a evidência observacional central é o NISAR.

## 1. Evidência para a tese (clima → chuva extrema → cheias)

| Fonte | O que sustenta | Força |
|---|---|---|
| IPCC AR6 WGI, Regional Fact Sheet Central and South America | No Sudeste da América do Sul (SES), aumento da precipitação média e extrema observado desde os anos 1960 (**confiança alta**). Para NES e SSA, aumento projetado de chuva extrema e cheias pluviais a partir de 2 °C (confiança média). | Alta, avaliação de consenso |
| World Weather Attribution (2024), cheias do RS em abr–mai/2024 | Mudança do clima tornou o evento ~2× mais provável e 6–9% mais intenso; El Niño contribuiu; falhas de infraestrutura, desmatamento e urbanização ampliaram impactos. Período de retorno 100–250 anos no clima atual. | Alta, estudo de atribuição de evento |
| Silva, Marchezini, Mikosz et al., *Environmental Research Letters* (2026), "Water-related disasters in Brazil: an assessment from 1991 to 2024" | ~60 mil registros S2iD/Atlas; 91,5% dos municípios com ao menos um evento; ≥ USD 123,89 bi em perdas; Sul concentra dano de inundações. | Alta para impacto; **não** sustenta tendência sozinho (ver ressalva) |
| Springer, *Earth Systems and Environment* (2026), cheias no Sul do Brasil, S2iD 1991–2024 | Todos os municípios estudados com tendência de aumento na frequência de chuva extrema; 67% das grandes cheias por chuva acumulada. | Média, regional |
| Vestena & Acquaotta, EMS 2024 | Tendências de cheias e chuva intensa em RS, SC e PR com S2iD 1991–2023. | Resumo de congresso |

**Ressalva crítica para a narrativa:** o aumento no número de registros do Atlas/S2iD é em parte efeito de notificação. O artigo da ERL mostra que municípios com registro passaram de 29% (2013) para 88% (2024), e cerca de 1.660 municípios não têm defesa civil estruturada. Portanto:
- usar Atlas/S2iD para **onde** e **quanto** dói (recorte, prejuízo);
- usar IPCC/WWA e séries de chuva (CHIRPS, GPM) para **por que está aumentando**;
- não afirmar "os desastres triplicaram" só com contagem de registros.

## 2. NISAR aplicado a cheias e áreas úmidas

Contexto: o NISAR (NASA-ISRO, L-band 24 cm e S-band) estava em validação científica até o meio de 2026; o GCOV validado (`NISAR_L2_GCOV_V1`) saiu em nov/2026. Logo, quase não há literatura revisada por pares com dados reais do NISAR. O que existe:

### Com dados reais do NISAR (2026, não revisados por pares)
| Trabalho | Recorte | Método | Uso para nós |
|---|---|---|---|
| NASA SVS #5661 (ago/2026) | Cheias de Moçambique, bacias Limpopo/Incomati, passagens 05 e 17/jan/2026 | GCOV, composição HH/HV/razão; água aberta escura, floresta inundada em magenta (double bounce) | Exemplo oficial de antes/depois com GCOV; mesma lógica do `detect_change.py`. Sem métricas de acurácia. |
| Relatório Assam University (2026) | Cheias em 5 distritos do Alto Assam, Índia | GCOV HVHV, 22/jul/2026 | Mapa de extensão em contexto de monção |
| `nisar-dhaka-flood-mapping` (GitHub) | Bangladesh, jun–out/2026 | NISAR L vs Sentinel-1 C | Manuscrito em preparação; a v2 corrigiu a v1 por amostras inválidas em granule parcial. **Lição: filtrar frames parciais e máscara de validade.** |
| Repositórios InGARSS 2026 YP Hackathon (Bihar) | Planície do Ganges, 31/ago–12/set/2026 | GCOV L + S, mudança em duas datas, fusão de frequências | Referência de pipeline de hackathon parecido com o nosso |

### Preparação para o NISAR (dados simulados ou L-band equivalente)
| Trabalho | Contribuição |
|---|---|
| NISAR Science Users' Handbook (JPL, 2019) | Requisito de mapear inundação globalmente ~2× a cada 12 dias; seções de Wetlands/Inundation; resposta urgente com latência de horas |
| NISAR Applications — Floods (NASA) | Casos de uso para cheias, incluindo água sob vegetação (Furacão Harvey) |
| ATBD de inundação de áreas úmidas (ASF OpenSARLab, NISAR Early Adopters Workshop 2024) | Classes água aberta / vegetação inundada (HH double bounce) / não classificado; limiares precisam calibração local |
| Workflow de produtos de ecossistemas NISAR (OSTI 2441094) | Simulação com UAVSAR/ALOS-2 → GCOV → produtos L3 de inundação |
| Adeli et al. 2021, *Earth and Space Science* | UAVSAR como proxy do NISAR; RF 81,9% / SVM 74,3% em áreas úmidas |
| Remote Sensing of Environment 2025 (OSTI 3407909) | InSAR L-band detecta vegetação inundada onde o double bounce é fraco |
| *Remote Sensing* 18(8):1172 (2026) | PALSAR-1/2 como proxy do NISAR para volume inundado em áreas úmidas de maré; >80% a 1 ha |
| Bourgeau-Chavez, webinar NAWM jun/2026 | Estado do mapeamento de áreas úmidas com NISAR; grande liberação de dados prevista para ~nov/2026 |

### L-band no Brasil (ALOS/PALSAR, base para a física do NISAR)
- Amazônia: dinâmica de cheia em várzea com SAR multitemporal (*Remote Sensing of Environment*, 2007); extensões máx./mín. de inundação na Bacia Amazônica 2014–2017 com ALOS-2 ScanSAR; L-band detecta água sob floresta.
- Pantanal: mapeamento de habitats e dinâmica de cheia com ALOS/PALSAR + RADARSAT-2; Sentinel-1 no Pantanal Norte (*Water* 18(7):778, 2026).
- RS 2024: os mapeamentos encontrados usam Sentinel-1, VIIRS e PlanetScope; **nenhum com L-band**. É uma lacuna que o projeto pode ocupar.

## 3. Implicações para o projeto

1. **Novidade:** não achamos estudo com NISAR em cheias no Brasil. Ser o primeiro recorte brasileiro com GCOV é um argumento forte para os critérios de relevância.
2. **Método defensável:** limiar em HH com mudança antes/depois (como o SVS da NASA), mais classe de vegetação inundada (double bounce HH, ATBD), mais máscara de frames parciais (lição de Dhaka).
3. **Série temporal:** o NISAR sozinho dá poucos pontos. Literatura e disponibilidade justificam calibrar contra OPERA DSWx-S1 e alongar com MapBiomas Água, deixando o NISAR como observação de referência.
4. **Narrativa:** clima (IPCC/WWA) → chuva extrema → cheia observada pelo NISAR → prejuízo (Atlas) → política pública.

## Fontes
- IPCC AR6 WGI Regional Fact Sheet — Central and South America: https://www.ipcc.ch/report/ar6/wg1/downloads/factsheets/IPCC_AR6_WGI_Regional_Fact_Sheet_Central_South_America.pdf
- WWA, cheias no Sul do Brasil 2024: https://www.worldweatherattribution.org/climate-change-made-the-floods-in-southern-brazil-twice-as-likely
- FAPESP sobre o artigo da ERL: https://agencia.fapesp.br/58618
- Springer, cheias no Sul do Brasil: https://link.springer.com/article/10.1007/s41748-026-01111-9
- Vestena & Acquaotta, EMS 2024: https://meetingorganizer.copernicus.org/EMS2024/EMS2024-1132.html
- NASA SVS Moçambique/NISAR: https://svs.gsfc.nasa.gov/5661
- Relatório cheias de Assam 2026: https://www.aus.ac.in/wp-content/uploads/2026/08/Report_Flood_2026_Assam-University.pdf
- Bangladesh NISAR vs Sentinel-1: https://github.com/fmad121581-hub/nisar-dhaka-flood-mapping
- Bihar InGARSS: https://github.com/davnish/nisar-surface-water-bihar , https://github.com/MEENIGAVENKATESWARLU/NISAR-LS-Band-Floodplain-Water-Mapping
- NISAR Science Users' Handbook: https://assets.science.nasa.gov/content/dam/science/missions/nisar/nisar-jpl/pdf/NISAR_FINAL_9-6-19.pdf
- NISAR Applications — Floods: https://assets.science.nasa.gov/content/dam/science/missions/nisar/nisar-jpl/pdf/NISAR_Applications_Floods.pdf
- ATBD áreas úmidas (notebook): https://github.com/ASFOpenSARlab/NISAR-Early-Adopters-Workshop-Oct-2024/blob/main/NISAR_ATBD_wetlands.ipynb
- OSTI workflow ecossistemas: https://www.osti.gov/biblio/2441094
- Adeli et al. 2021: https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021EA001742
- InSAR L-band vegetação inundada: https://www.osti.gov/pages/biblio/3407909-exploring-potential-using-band-insar-mapping-flooded-vegetation-tropical-wetlands
- Volume inundado PALSAR como proxy: https://doi.org/10.3390/rs18081172
- Webinar NAWM: https://nawm.org/pdf_lib/wmc_webinar/bourgeau_chavez_061026.pdf
- Amazônia SAR multitemporal: https://www.sciencedirect.com/science/article/abs/pii/S0034425706004585
- Amazônia ALOS-2 2014–2017: https://www.researchgate.net/publication/340880521
- Pantanal Sentinel-1: https://www.mdpi.com/2073-4441/18/7/778

## 4. Desertificação e perda de costa (levantamento de 14/11/2026)

### Desertificação / secas
- **Nenhum estudo com NISAR em desertificação ou terras secas encontrado.**
- O mais próximo é o produto oficial de **umidade do solo do NISAR** (L3 SME2, beta e provisório, 200 m; meta 0,06 m³/m³), avaliado num estudo na Hungria (beta, 2026) e pela ISRO (100 m, caso semiárido no oeste da Índia, ainda em cal/val).
  - https://www.earthdata.nasa.gov/data/catalog/asf-nisar-l3-sme2-provisional-v1-1
  - https://www.researchgate.net/publication/413565742_Soil_moisture_estimation_based_on_the_new_NISAR_Beta-version_Radar_Imagery
  - https://www.isro.gov.in/NisarData_soil_moisture_products.html
- Brasil: núcleos de desertificação (Gilbués-PI, Irauçuba-CE, Inhamuns-CE, Cabrobó-PE, Seridó-RN/PB) são estudados sobretudo com óptico (NDVI/Landsat). Radar só aparece num trabalho SBGFA 2024 em Petrolina.
- Atlas: 33.493 registros de estiagem/seca (14110/14120), o maior grupo em prejuízo nominal.

### Costa / nível do mar
- **Nenhum estudo com NISAR sobre erosão costeira ou linha de costa encontrado.**
- NISAR + subsidência: NASA mapeou a subsidência da Cidade do México com dados iniciais do NISAR (2026) e cita o uso em comunidades costeiras, onde subsidência e subida do mar se somam. https://www.nasa.gov/missions/nisar/us-indian-space-mission-maps-extreme-subsidence-in-mexico-city/
- Costa da Califórnia (NASA, 2026): InSAR 2015–2023 (não NISAR); NISAR entrará via OPERA. https://www.nasa.gov/missions/nisar/nasa-led-study-pinpoints-areas-sinking-rising-along-california-coast/
- Áreas úmidas costeiras: requisito do NISAR de mapear inundação em áreas úmidas costeiras a 1 ha a cada 12 dias com ≥80% de acurácia (Lamb et al., Remote Sensing 18:1172, 2026, com PALSAR como proxy).
- Método: InSAR de subsidência → subida relativa do mar precisa de rigor (referência vertical, GNSS). https://www.researchgate.net/publication/388281186
- Brasil: InSAR costeiro concentrado em Maceió (subsidência por mineração de sal; Remote Sensing 17:3974, 2025). Panorama da Erosão Costeira (MMA/Procosta): erosão em 60–65% do litoral N/NE. https://revistapesquisa.fapesp.br/a-progressiva-destruicao-das-praias-brasileiras/
- Atlas: 250 registros de erosão costeira/marinha (11410) e 284 de erosão de margem fluvial (11420).

### Avaliação para o hackathon
- Inundação é onde o NISAR tem requisito de missão, ATBD e os primeiros casos com dados reais. É o tema mais defensável.
- Seca: viável usar a umidade do solo NISAR, mas o produto ainda é provisório e não é desertificação (processo de décadas).
- Costa: o NISAR mede subsidência (InSAR) e área úmida costeira inundada, não erosão de linha de costa diretamente; seria preciso séries longas.
