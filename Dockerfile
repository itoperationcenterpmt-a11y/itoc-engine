FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /srv/backend/
COPY frontend/ /srv/frontend/
ENV ITOC_FRONTEND_DIR=../frontend PYTHONUNBUFFERED=1
EXPOSE 8000
