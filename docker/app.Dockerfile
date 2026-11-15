# Imagem leve para a API e para o worker que publica os resultados.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN pip install --no-cache-dir "fastapi==0.115.6" "uvicorn[standard]==0.34.0" "psycopg[binary]==3.2.3" "psycopg-pool==3.2.4" "openai==1.93.0"
COPY app /srv/app
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
