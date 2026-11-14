# Indicadores NISAR (jun–out/2026) × MapBiomas e outras camadas

Pontos: 3091 em 14 municípios (Seridó e São Francisco). Correlação de Spearman (ρ).
Negrito: |ρ| ≥ 0,30 e p < 0,001. (ns) = não significativo (p ≥ 0,05).

| Indicador NISAR | ndvi_jun_out_2026 | ndvi_tendencia_2001_2024 | desmatado_2001_2024 | pastagem_vigor_baixo | veg_secundaria_2024 | anos_com_fogo | areia_pct | chuva_jan_mai_2026 | chuva_jun_out_2026 | temp_jun_out_2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| HV (dB) | +0.24 | +0.02 (ns) | -0.22 | **-0.31** | -0.04 | -0.06 | -0.14 | -0.02 (ns) | +0.06 | **-0.36** |
| HH (dB) | +0.27 | +0.06 | -0.21 | -0.29 | -0.08 | -0.05 | -0.12 | -0.07 | +0.03 (ns) | **-0.31** |
| HV/HH (dB) | +0.10 | -0.03 (ns) | -0.15 | -0.20 | +0.05 | -0.07 | -0.11 | +0.07 | +0.08 | -0.30 |
| RVI | +0.10 | -0.03 (ns) | -0.15 | -0.20 | +0.05 | -0.07 | -0.11 | +0.07 | +0.08 | -0.30 |
| HV variação temporal | +0.21 | +0.07 | -0.00 (ns) | +0.05 | -0.08 | +0.04 | -0.02 (ns) | +0.07 | +0.08 | +0.12 |
| HH variação temporal | +0.20 | +0.08 | -0.00 (ns) | -0.02 (ns) | -0.08 | -0.01 (ns) | +0.01 (ns) | -0.08 | -0.03 (ns) | +0.01 (ns) |
| HV inclinação sazonal | +0.05 | +0.07 | -0.00 (ns) | +0.08 | +0.04 | +0.00 (ns) | **-0.39** | **+0.53** | +0.26 | +0.04 |
| HH inclinação sazonal | -0.10 | -0.11 | -0.02 (ns) | -0.03 (ns) | -0.09 | +0.01 (ns) | +0.01 (ns) | -0.07 | -0.19 | +0.00 (ns) |
| HV textura | -0.12 | -0.04 | +0.14 | +0.21 | -0.02 (ns) | -0.02 (ns) | +0.05 | +0.04 | -0.04 | +0.14 |
| HH textura | -0.12 | -0.04 | +0.14 | +0.23 | -0.03 (ns) | -0.00 (ns) | +0.03 (ns) | +0.07 | -0.03 (ns) | +0.13 |

## NISAR por classe de uso do MapBiomas 2024 (medianas; Kruskal-Wallis HV: H = 1142, p = 2e-242)

| classe_mapbiomas            |   pontos |   HV_dB |   HH_dB |   HVHH_dB |   RVI |   HV_textura |   NDVI_2026 |
|:----------------------------|---------:|--------:|--------:|----------:|------:|-------------:|------------:|
| Savana (Caatinga)           |     1625 |  -13.17 |   -7.74 |     -5.46 |  0.89 |         2.05 |        0.4  |
| Lavoura perene              |      168 |  -15.04 |   -8.39 |     -6.51 |  0.73 |         2.67 |        0.59 |
| Mosaico de usos             |      613 |  -15.07 |   -9.17 |     -5.91 |  0.82 |         2.58 |        0.36 |
| Campo                       |       31 |  -15.5  |   -9.66 |     -6.2  |  0.77 |         2.15 |        0.31 |
| Lavoura temporária          |       48 |  -15.95 |   -9.42 |     -6.6  |  0.72 |         2.96 |        0.5  |
| Pastagem                    |      513 |  -16.19 |   -9.95 |     -6.09 |  0.79 |         2.95 |        0.38 |
| Solo exposto / não vegetado |       25 |  -16.76 |  -10.76 |     -6.52 |  0.73 |         3.04 |        0.31 |
| Cana                        |       24 |  -17.97 |  -10.62 |     -7.26 |  0.63 |         2.41 |        0.5  |
