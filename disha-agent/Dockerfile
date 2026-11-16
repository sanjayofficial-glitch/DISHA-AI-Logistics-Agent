FROM python:3.12-slim

WORKDIR /srv

# System deps for psycopg-style builds are not needed; keep the image slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p data

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('PORT','8080')+'/health', timeout=4).status==200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
