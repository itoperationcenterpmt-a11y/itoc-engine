FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r requirements.txt
COPY backend/ /srv/backend/
COPY frontend/ /srv/frontend/
ENV ITOC_FRONTEND_DIR=../frontend PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app && chown -R app:app /srv
USER app
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9000/api/health', timeout=4).status==200 else 1)"
