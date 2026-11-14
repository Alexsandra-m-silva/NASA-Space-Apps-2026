# Quanto o NISAR ajuda a prever degradação?

Pontos: 3091 (14 municípios). XGBoost, validação por blocos espaciais (~11 km), média de 3 sementes.
Features históricas só até 2014; alvo medido em 2015–2024; NISAR e MODIS 2026 = estado atual.

## T1 — degradação recente da vegetação 2015–2024 (AUC)

| Conjunto | Métrica | ± | n | % positivos |
|---|---|---|---|---|
| 1. Histórico até 2014 + clima | 0.273 | 0.038 | 3091 | 0% |
| 2. (1) + MODIS 2026 | 0.273 | 0.038 | 3091 | 0% |
| 3. (1) + NISAR 2026 | 0.273 | 0.038 | 3091 | 0% |
| 4. (1) + MODIS 2026 + NISAR 2026 | 0.273 | 0.038 | 3091 | 0% |
| 5. Só NISAR 2026 | 0.273 | 0.038 | 3091 | 0% |
| 6. Só MODIS 2026 | 0.273 | 0.038 | 3091 | 0% |

Ganho do NISAR sobre histórico+clima: **+0.000** · ganho do MODIS 2026: +0.000 · ganho do NISAR além do MODIS 2026: **+0.000**

## T1 contínuo — tendência RESTREND 2015–2024 (R²)

| Conjunto | Métrica | ± | n | % positivos |
|---|---|---|---|---|
| 1. Histórico até 2014 + clima | 0.278 | 0.011 | 3091 |  |
| 2. (1) + MODIS 2026 | 0.360 | 0.007 | 3091 |  |
| 3. (1) + NISAR 2026 | 0.326 | 0.009 | 3091 |  |
| 4. (1) + MODIS 2026 + NISAR 2026 | 0.372 | 0.009 | 3091 |  |
| 5. Só NISAR 2026 | 0.149 | 0.005 | 3091 |  |
| 6. Só MODIS 2026 | 0.019 | 0.001 | 3091 |  |

Ganho do NISAR sobre histórico+clima: **+0.048** · ganho do MODIS 2026: +0.082 · ganho do NISAR além do MODIS 2026: **+0.012**

## T2 — Caatinga 2014 convertida/desmatada até 2024 (AUC)

| Conjunto | Métrica | ± | n | % positivos |
|---|---|---|---|---|
| 1. Histórico até 2014 + clima | 0.717 | 0.005 | 1859 | 16% |
| 2. (1) + MODIS 2026 | 0.747 | 0.002 | 1859 | 16% |
| 3. (1) + NISAR 2026 | 0.818 | 0.004 | 1859 | 16% |
| 4. (1) + MODIS 2026 + NISAR 2026 | 0.819 | 0.002 | 1859 | 16% |
| 5. Só NISAR 2026 | 0.792 | 0.005 | 1859 | 16% |
| 6. Só MODIS 2026 | 0.552 | 0.015 | 1859 | 16% |

Ganho do NISAR sobre histórico+clima: **+0.101** · ganho do MODIS 2026: +0.030 · ganho do NISAR além do MODIS 2026: **+0.071**
