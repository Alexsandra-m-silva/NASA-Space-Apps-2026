# Deploy no Easypanel

O repositório sai pronto para um serviço **Compose** do Easypanel usando o `docker-compose.yml` (mesmo padrão do
Simemap e do Prospector). Localmente, `docker-compose.local.yml` acrescenta a porta 8090 e o reprocessamento dos modelos.

Detalhes do compose que são obrigatórios no Easypanel:

- **Sem `ports`**: o domínio é ligado na aba Domains; nenhuma porta é publicada no servidor.
- **Variáveis por interpolação** (`VAR: ${VAR}` em `environment:`): é assim que a aba Environment chega ao container.
- **Rede externa `easypanel`** no `guardian-web`: sem ela o domínio responde "Service is not reachable".
- **Nomes com prefixo** (`guardian-*`): nomes curtos colidem com outras stacks na rede do servidor.
- **Sem bind mounts**: páginas, produtos e resultados dos modelos vão dentro das imagens.

## 1. Criar o serviço

1. No projeto do Easypanel: **+ Service → Compose**.
2. **Source → Git**: `https://github.com/Alexsandra-m-silva/NASA-Space-Apps-2026.git`, branch `main`,
   arquivo `docker-compose.yml`.
3. **Environment**: cole as variáveis da seção 2, uma por linha, sem comentários no fim da linha.
   Não inclua `COMPOSE_FILE`/`COMPOSE_PATH_SEPARATOR` (são só do uso local).
4. **Domains**: domínio apontando para o serviço **`guardian-web`**, porta **`80`** (o Easypanel emite o HTTPS).
5. **Deploy**. Na primeira subida, o `guardian-worker` publica os resultados no PostGIS e termina; depois sobem a API,
   o comparar e o web.

## 2. Variáveis de ambiente

```
POSTGRES_PASSWORD=<senha forte>
FRONTEND_URL=https://<seu-dominio>
FOUNDRY_ENDPOINT=https://<recurso>.services.ai.azure.com/openai/v1
FOUNDRY_API_KEY=<chave>
FOUNDRY_MODEL=gpt-5-mini
GEMINI_API_KEY=<chave>
GEMINI_MODEL=gemini-3.8-flash
BREVO_SMTP_LOGIN=<login SMTP do Brevo>
BREVO_SMTP=<chave SMTP do Brevo>
DEFAULT_FROM_EMAIL=<remetente com domínio validado no Brevo>
EMAIL_ADMIN_TOKEN=<segredo para disparar e-mails pela API>
```

Sem `FOUNDRY_*` o chat responde 503; sem `GEMINI_API_KEY` o agente não roda; sem `EMAIL_ADMIN_TOKEN` o envio de
e-mail fica desligado. O resto do app funciona sem nenhuma chave.

## 3. Gerar as recomendações (agente Desert Sentinel)

No console do serviço (ou localmente apontando para o banco de produção):

```
docker compose --profile agente run --rm guardian-sentinel
```

As recomendações ficam no banco e **sobrevivem a novos deploys** (o worker não apaga o documento `recomendacoes`).

## 4. Rotas

| Rota | O que é |
|---|---|
| `/` (`modelo.html`) | mapa, suscetibilidade, validação NISAR, SHAP |
| `/municipios.html`, `/produto.html` | comparação MODIS × NISAR por município e produto GeoTIFF |
| `/comparar/` | Compare and explain (Streamlit) |
| `/api/...`, `/docs` | API somente leitura, recomendações, e-mail, chat |

## 5. Uso local

```bash
cp .env.example .env            # já traz COMPOSE_FILE com os dois arquivos
docker compose up -d --build    # http://localhost:8090
docker compose --profile pipeline run --rm guardian-pipeline python -m pipeline.bundle   # reprocessar
```
