FROM python:3.12-slim 
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y curl
COPY . . 
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --retries=3 --timeout=10s --start-period=15s \
CMD curl -f http://localhost:8000/health || exit 1 
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]
