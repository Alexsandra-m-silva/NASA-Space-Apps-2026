# Frontend Climate Sentinel (Next.js) da pasta platform/.
FROM node:22-alpine AS deps
WORKDIR /app
COPY platform/package.json platform/package-lock.json* ./
# preinstall da Gabi (scripts/assemble-lock.js) precisa existir; com o lock commitado ele sai sem fazer nada
COPY platform/scripts ./scripts
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY platform/ .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0
COPY --from=build /app ./
EXPOSE 3847
CMD ["npm", "run", "start"]
