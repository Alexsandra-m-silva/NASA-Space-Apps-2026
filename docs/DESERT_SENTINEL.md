# Climate Sentinel — agente de recomendações (rascunho)

Agente com a API do Google Gemini que transforma os indicadores do modelo (MODIS, NISAR, clima,
suscetibilidade, SHAP) em recomendações de política pública por município, no formato do
`climate-action-plan.html`: **SUPPORT / IMPROVE / CREATE / MONITOR**.

O Gemini roda **só no servidor**. O navegador lê o resultado pronto pela API.

## Rodar

```bash
# .env (raiz):  GEMINI_API_KEY=...   GEMINI_MODEL=gemini-3.8-flash (opcional)
docker compose --profile agente run --rm dg-sentinel            # todos os municípios
docker compose --profile agente run --rm dg-sentinel python -m app.agent.sentinel "Petrolina/PE"
```

Grava `app/bundle/recomendacoes.json` e a tabela `documentos` (nome `recomendacoes`). Num `docker compose up`
novo, o worker republica o arquivo se ele existir.

## API (para o layout)

| Método | Rota | Retorno |
|---|---|---|
| GET | `/api/recomendacoes` | `{"publicado_em": "...", "municipios": {"Petrolina/PE": {...}, ...}}` |
| GET | `/api/recomendacoes/{Município}/{UF}` | objeto de um município (ex.: `/api/recomendacoes/Casa Nova/BA`) |

404 enquanto o agente não tiver rodado.

### Contrato de um município

```json
{
  "municipio": "Petrolina/PE",
  "diagnostico": "3 a 5 frases com números",
  "nivel_alerta": "baixo | moderado | alto",
  "recomendacoes": [
    {
      "categoria": "SUPPORT | IMPROVE | CREATE | MONITOR",
      "acao": "texto curto",
      "justificativa": "por que",
      "evidencias": ["pct_area_degradando = 11.2", "..."],
      "politicas": ["lei_13153_2015", "..."],
      "responsaveis": [{"esfera": "municipal | estadual | federal", "orgao": "tipo de órgão", "perfil_x": null}],
      "prioridade": "alta | media | baixa",
      "limitacoes": ["..."]
    }
  ],
  "rascunho_x": {"texto": "até 280 caracteres", "status": "pending_review"},
  "limitacoes_gerais": ["..."],
  "gerado_em": "ISO 8601",
  "modelo": "gemini-...",
  "politicas_referencia": [{"id": "...", "nome": "...", "esfera": "...", "orgao": "...", "verificar": true}]
}
```

Sugestões de layout: cartão por recomendação com selo da categoria, lista de evidências, chips das políticas
(nome completo vem de `politicas_referencia`; mostrar aviso quando `verificar` = true) e o rascunho do X com
botão **copiar** — a publicação no X é sempre manual, depois de revisão humana.

## Salvaguardas

- Os dados enviados ao modelo são indicadores numéricos; o prompt instrui a nunca tratá-los como instrução.
- Só políticas da lista fechada `app/agent/politicas.json`; IDs inventados são descartados na validação.
- `perfil_x` é sempre `null` (o agente não indica perfis de pessoas) e `status` do rascunho é sempre `pending_review`.
- Sem nomes de pessoas, sem ataque a gestores ou partidos; degradação por satélite ≠ desertificação comprovada.
- Itens da lista com `verificar: true` (Garantia-Safra e PAEs estaduais) precisam de conferência na fonte oficial.

## Próximos passos

- Pesquisa de políticas e responsáveis atuais em fontes oficiais (LexML, Câmara, Senado, TSE) para ampliar a lista.
- Botão "gerar novamente" no backend (com limite de frequência) em vez de só linha de comando.

## E-mail da recomendação (Brevo)

Mesmo padrão do Clinibud: Brevo por SMTP (`smtp-relay.brevo.com:587`, TLS). Variáveis no `.env` da raiz:

```
BREVO_SMTP_LOGIN=      # login SMTP do Brevo
BREVO_SMTP=            # chave SMTP do Brevo
DEFAULT_FROM_EMAIL=    # remetente com domínio validado no Brevo
FRONTEND_URL=http://localhost:8090
EMAIL_ADMIN_TOKEN=     # segredo exigido para disparar envios pela API
```

| Método | Rota | Uso |
|---|---|---|
| GET | `/api/recomendacoes/{Município}/{UF}/email.html` | pré-visualização do e-mail (não envia) |
| POST | `/api/recomendacoes/{Município}/{UF}/email` | envia; corpo `{"para": ["a@b.org"]}`, cabeçalho `X-Admin-Token` |

Sem `EMAIL_ADMIN_TOKEN` o envio fica desligado (503). Máximo de 20 destinatários por envio.
Modelo em `app/notify/email.py`; exemplo ilustrativo para testar o layout em `app/notify/exemplo_recomendacao.json`:

```bash
python -m app.notify.email "Petrolina/PE" --exemplo app/notify/exemplo_recomendacao.json --preview email.html
```
