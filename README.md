# Climate Guardian — Dancing with the SARs

NASA Space Apps Challenge 2026. NISAR L-band no núcleo da detecção; GPM IMERG como contexto de chuva.

## O que está plugado

| Papel | Produto NASA | Como entra |
| --- | --- | --- |
| Imagem no mapa (hoje, sem login) | GIBS `NISAR_L2_Geocoded_Polarimetric_Covariance` | mosaico diário do GCOV, 15.6 m |
| Análise quantitativa | `NISAR_L2_GCOV_V1` (validado 6 nov 2026) ou `NISAR_L2_GCOV_PROVISIONAL_V1` | camada `HHHH` (gamma0) |
| Chuva | GPM IMERG Late daily `GPM_3IMERGDL` v07 + camada GIBS `IMERG_Precipitation_Rate` | entre as duas passagens SAR |

Água calma / inundação: backscatter HH muito baixo. Mudança = pixels que cruzam o limiar (padrão −18 dB) entre o par antes/depois, de preferência no mesmo track/frame (ciclo de 12 dias).

## Chat com os dados da tela

O botão de avatar abre o chat nas páginas do projeto. As perguntas incluem o texto e os valores dos controles exibidos na página atual. O navegador chama a API do projeto; a chave do Microsoft Foundry fica apenas no `.env` do servidor.

Preencha `FOUNDRY_API_KEY` no `.env` local. O endpoint e o nome do deployment (`FOUNDRY_ENDPOINT` e `FOUNDRY_MODEL`) também ficam nesse arquivo; não cole a chave no código nem a envie ao navegador. O `.env` está excluído do Git. Depois, na pasta do projeto, reconstrua e inicie os serviços:

```powershell
docker compose up --build -d
```

Abra `http://localhost:8090` e clique no avatar no canto inferior direito.

## 1. Ver as imagens agora

```bash
python -m http.server 8000 --directory web
```

Open `http://localhost:8000`. The slider compares two NISAR passes over the Uruguay River at Uruguaiana (24 Oct and 5 Nov 2026, same track). Red and cyan on `web/scenes/change.png` are the calculated open-water change. Check GPM for rain.

## 2. Conta Earthdata (números reais)

1. Crie login em [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/).
2. Copie `.env.example` → `.env` com `EARTHDATA_USERNAME` e `EARTHDATA_PASSWORD`.
3. Autorize ASF DAAC e GES DISC na conta (Applications).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a
python -m pipeline.fetch_nisar              # lista o par GCOV
python -m pipeline.fetch_gpm
python -m pipeline.fetch_nisar --download   # HDF5 (grande) — 1 granule de cada lado
python -m pipeline.detect_change            # hectares + limitações
```

AOI e datas: `pipeline/config.py`.

## 3. Julgagem (Validity / Relevance)

- **Relevance:** o mapa e os indicadores saem do GCOV L-band, não de um basemap decorativo.
- **Validity:** produto RTC/gamma0 feito para inundação; limiar empírico, speckle, geometria e penetração L-band em vegetação estão listados em `change_stats.json`.
