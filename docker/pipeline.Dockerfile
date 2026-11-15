# Imagem completa do pipeline (GEE, NISAR, XGBoost, SHAP). Só é usada para reprocessar:
#   docker compose --profile pipeline run --rm dg-pipeline python -m pipeline.<etapa>
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt shap matplotlib
COPY pipeline /srv/pipeline
COPY app /srv/app
CMD ["python", "-m", "pipeline.bundle"]
