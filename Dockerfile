# Imagem única para implantação em nuvem: console + API no mesmo contêiner.
#
# O `docker-compose.yml` continua sendo o jeito certo de rodar em produção de
# verdade — front e back separados, cada um escalando por conta própria. Esta
# imagem existe para o outro cenário: um PaaS onde cada serviço tem custo, URL e
# hibernação próprios, e onde dois contêineres significam dois lugares para dar
# errado no meio de uma apresentação.
#
#   docker build -t claro-hub .
#   docker run -p 8000:8000 --env-file .env claro-hub
#
# Sem Redis e sem MongoDB o hub sobe em memória e informa isso no /health.

# --- 1. console -------------------------------------------------------------
FROM node:20-alpine AS web

WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# --- 2. runtime -------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=web /web/dist ./web

# O PaaS injeta a porta em $PORT; 8000 é o padrão para rodar local.
ENV PORT=8000
EXPOSE 8000

# Sem shell não há expansão de $PORT, por isso a forma exec com sh -c.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
