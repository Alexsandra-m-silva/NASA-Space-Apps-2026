# Polígonos MODIS validados pelo NISAR (gradient boosting)

Pontos: 1931 (degradado 786, controle 1145) + melhora 1160 · blocos espaciais: 286

## Resultado (validação cruzada por blocos espaciais)

- AUC: **0.758**
- Limiar (escolhido só no treino): 0.398
- Sensibilidade (degradado → NISAR acusa): **66.2%**
- Especificidade (controle → NISAR NÃO acusa): **71.3%**
- Falso alarme em polígonos de MELHORA (ex.: irrigação nova): **39.9%**

| | NISAR: degradado | NISAR: não degradado |
|---|---|---|
| MODIS: degradado | 520 | 266 |
| MODIS: controle | 329 | 816 |

## Por região

| Região | n | AUC | sensibilidade | especificidade |
|---|---|---|---|---|
| sao_francisco | 1164 | 0.721 | 67.1% | 65.1% |
| serido | 767 | 0.773 | 63.6% | 77.7% |

## Variáveis NISAR que mais pesam

| Feature | queda de AUC |
|---|---|
| nisar_hv_tex | 0.1280 |
| nisar_hv_slope | 0.0529 |
| nisar_hh_slope | 0.0482 |
| nisar_hh_std_t | 0.0466 |
| nisar_hvhh_db | 0.0403 |
| nisar_hv_std_t | 0.0286 |
| nisar_hv_db | 0.0275 |
| nisar_hh_db | 0.0224 |
| nisar_hh_tex | 0.0188 |
| nisar_rvi | 0.0037 |

## Veredito

**O NISAR corrobora o mapa MODIS**: separa degradado de controle com AUC ≥ 0,70 e especificidade ≥ 70%.