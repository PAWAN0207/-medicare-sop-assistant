FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1 DB_PATH=/app/var/sop_index.db
EXPOSE 8000
# index (idempotent: a restart re-indexes nothing) then serve
CMD ["sh", "-c", "python -m sopassist.ingest.cli ${INITIAL_SNAPSHOT:-data/sops} && uvicorn sopassist.main:app --host 0.0.0.0 --port 8000"]
