# nginx com as páginas (web/), os produtos GeoTIFF (products/) e o roteamento para API e comparar.
FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY web /usr/share/nginx/html
COPY products /srv/products
