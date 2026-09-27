FROM python:3.12-slim
WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app
ENV ORION_STATE_DIR=/app/runtime/state
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health',timeout=2)"
CMD ["python","-m","orion.app"]
