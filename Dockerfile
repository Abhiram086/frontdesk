# Stage 1: Build the React frontend
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend serving API + built React app
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=web /web/dist ./static

ENV TZ=Asia/Kolkata PYTHONUNBUFFERED=1

CMD sh -c "python -m app.migrate && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"