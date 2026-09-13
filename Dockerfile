FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080

CMD ["uvicorn", "homeprep_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
