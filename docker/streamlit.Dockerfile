# "Comparar e explicar" (Floresta compare): app Streamlit da equipe, servido em /comparar/.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN pip install --no-cache-dir "streamlit>=1.40" "folium>=0.15" "streamlit-folium>=0.22" numpy pandas pillow scipy
COPY streamlit_app.py /srv/streamlit_app.py
COPY .streamlit /srv/.streamlit
COPY products /srv/products
COPY web/municipios /srv/web/municipios
EXPOSE 8501
# baseUrlPath permite servir atrás do nginx em /comparar/ sem alterar o app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.baseUrlPath=comparar", "--server.headless=true", "--browser.gatherUsageStats=false", "--client.toolbarMode=viewer"]
