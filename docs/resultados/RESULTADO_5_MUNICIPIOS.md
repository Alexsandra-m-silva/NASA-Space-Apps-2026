# Degradação vegetal (MODIS) validada pelo NISAR — 5 municípios

Municípios: Floresta/PE, Currais Novos/RN, Parelhas/RN (desertificação documentada) · Petrolina/PE, Casa Nova/BA (degradação ativa).

## Método
1. **MODIS MOD13Q1 2001–2024 (250 m) + chuva CHIRPS.** RESTREND: tendência do NDVI que a chuva não explica (Sen + Mann-Kendall).
   Degradado = queda significativa (p < 0,05); controle = sem tendência; melhora = alta significativa. Fora: água, urbano, mineração, usina solar, lavoura (MapBiomas 2024).
2. **NISAR GCOV (L-band, HH/HV, jun–out/2026).** Features por ponto: HV, HH, HV/HH, RVI, variação temporal, inclinação sazonal, textura.
3. **Gradient boosting (XGBoost)** separa degradado de controle. Validação por blocos espaciais de ~11 km (vizinhos nunca ficam um no treino e outro no teste). Limiar escolhido só no treino.

## MODIS: % da área de cada município

| Município | Área (km²) | Degradando | Melhorando | Estável |
|---|---|---|---|---|
| Petrolina/PE | 4.561 | **11,2%** | 6,8% | 34,2% |
| Casa Nova/BA | 9.646 | **5,8%** | 2,1% | 35,8% |
| Floresta/PE | 3.605 | 2,7% | 8,2% | 32,9% |
| Currais Novos/RN | 865 | 0,4% | 4,8% | 48,5% |
| Parelhas/RN | 513 | 0,1% | 33,0% | 13,9% |

Abaixo de ~2,5% a fração "degradando" é compatível com acaso (teste a 5% por pixel).

## NISAR confirma o MODIS?

| Município | Pontos degr./controle | Sensibilidade | Especificidade | AUC |
|---|---|---|---|---|
| Petrolina/PE | 199 / 102 | 78,9% | 53,9% | 0,743 |
| Casa Nova/BA | 227 / 203 | 64,3% | 68,5% | 0,744 |
| Currais Novos/RN | 29 / 164 | 62,1% | 76,2% | 0,817 |
| Floresta/PE | 31 / 62 | 35,5% | 62,9% | 0,506 |
| Parelhas/RN | 0 / 25 | — | 84,0% | — |
| **Total (5)** | **486 / 556** | **68,3%** | **68,2%** | **0,767** |

Nos 14 municípios: AUC 0,758, sensibilidade 66%, especificidade 71%.
Variável NISAR mais informativa: textura do HV (áreas degradadas são mais heterogêneas no radar).

## Leitura
- **O NISAR separa áreas degradadas de não degradadas acima do acaso** (AUC 0,77 nos 5), com municípios e blocos espaciais fora do treino.
- Funciona melhor onde há degradação ativa (Petrolina, Casa Nova) e no Seridó (Currais Novos). Em Parelhas, sem degradação no MODIS, o NISAR não acusa 84% dos controles.
- **Floresta não apresenta sinal** (AUC 0,51): pouca degradação recente e poucos pontos.
- Petrolina tem muitos falsos alarmes (especificidade 54%): provável confusão com mosaico agrícola e irrigação.

## Limites
- NISAR provisório e só estação seca de 2026; gabarito é tendência de NDVI (não medição de campo).
- Degradação vegetal ≠ desertificação comprovada: em Petrolina e Casa Nova pode haver conversão de uso.
- Lista de municípios do núcleo do Seridó não verificada na fonte primária (PAE/RN 2010).

## Arquivos
- `poligonos_modis_5municipios.geojson` — 2.243 polígonos (degradado / controle / melhora), com área em ha.
- `modis_5.csv`, `nisar_5.csv` — tabelas acima.

## Clima 1991–2024: chuva (CHIRPS), temperatura e evapotranspiração potencial (ERA5-Land)

| Município | Chuva 1991–2007 → 2008–2024 (mm/ano) | Tendência chuva | Temperatura média 1991–2007 → 2008–2024 | Tendência temperatura | Aridez* 1991–2007 → 2008–2024 |
|---|---|---|---|---|---|
| Petrolina/PE | 462 → 443 | 0 mm/década (p = 0,99) | 26,16 → 26,56 °C | **+0,26 °C/década (p = 0,005)** | 0,130 → 0,122 (mais árido) |
| Casa Nova/BA | 494 → 494 | 0 mm/década (p = 0,99) | 25,92 → 26,31 °C | **+0,26 °C/década (p = 0,007)** | 0,141 → 0,139 |
| Floresta/PE | 473 → 491 | +8 mm/década (p = 0,65) | 26,01 → 26,12 °C | +0,14 °C/década (p = 0,13) | 0,151 → 0,158 |
| Currais Novos/RN | 457 → 534 | +42 mm/década (p = 0,15) | 25,19 → 25,20 °C | +0,10 °C/década (p = 0,09) | 0,154 → 0,185 (menos árido) |
| Parelhas/RN | 541 → 629 | +51 mm/década (p = 0,13) | 25,75 → 25,74 °C | +0,05 °C/década (p = 0,34) | 0,166 → 0,199 (menos árido) |

*Aridez = chuva / evapotranspiração potencial. A evapotranspiração do ERA5-Land superestima a de referência (Penman-Monteith), então os valores absolutos ficam abaixo dos oficiais. Use só para comparar períodos e municípios, não com os limiares da UNEP.

**Leitura conjunta clima × vegetação × NISAR**
- **Petrolina e Casa Nova:** aquecimento significativo (+0,26 °C/década), chuva estável e aridez piorando → são exatamente os municípios com **degradação vegetal ativa** no MODIS, e onde o NISAR confirma (AUC 0,74).
- **Seridó (Currais Novos, Parelhas):** chuva subindo (não significativo), quase sem aquecimento, aridez melhorando → **vegetação verdejando** no MODIS, e o NISAR não acusa degradação em Parelhas (especificidade 84%).
- O RESTREND já desconta a chuva, mas **não desconta a temperatura**: parte da degradação em Petrolina e Casa Nova pode vir do calor (mais evapotranspiração), parte do uso do solo.

Arquivos: `clima_anual_1991_2024.csv` (série anual por município), `clima_tendencias_5.csv` (tendências).

## Suscetibilidade à desertificação sob estresse climático (250 m)

Índice 0–1 = média de 5 componentes normalizados: aquecimento 1991–2024 (ERA5-Land), aridez 2008–2024 (CHIRPS/ERA5-Land),
tendência da vegetação descontada a chuva (MODIS), pressão de uso (desmatamento ou pastagem de vigor baixo, MapBiomas) e solo arenoso (MapBiomas Solo).
Classes por quartis nos 5 municípios (suscetibilidade **relativa** entre eles).

| Município | Índice médio | % alta | % muito alta | Principais componentes |
|---|---|---|---|---|
| Petrolina/PE | 0,70 | 35,9 | **51,9** | aquecimento, aridez, solo arenoso, queda da vegetação |
| Casa Nova/BA | 0,61 | 31,3 | **23,7** | aquecimento, aridez, solo arenoso |
| Floresta/PE | 0,45 | 3,8 | 4,0 | aridez |
| Currais Novos/RN | 0,30 | 0 | 0 | — |
| Parelhas/RN | 0,25 | 0 | 0 | — |

**Validação pelo NISAR** (probabilidade de degradação estimada pelo radar, fora da amostra, em 1.042 pontos):

| Classe de suscetibilidade | Pontos | Prob. média de degradação (NISAR) |
|---|---|---|
| Baixa | 260 | 0,29 |
| Média | 167 | 0,35 |
| Alta | 186 | 0,37 |
| Muito alta | 429 | **0,57** |

Spearman índice × NISAR: ρ = 0,49 (p < 10⁻⁶⁰). O sinal do radar sobe junto com a suscetibilidade.

Ressalva: o componente "vegetação" vem do mesmo MODIS usado para treinar o modelo NISAR, então parte da concordância é esperada.
Pesos iguais e classes relativas: é um indicador de prioridade, não um mapa oficial de risco.

Arquivos: `suscetibilidade_alta_5municipios.geojson` (2.030 polígonos alta/muito alta), `suscetibilidade_*.tif` (índice e classe), `suscetibilidade_5.csv`, `suscetibilidade_validacao_nisar.csv`.
