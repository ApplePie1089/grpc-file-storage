FROM python:3.11-slim

RUN pip install --no-cache-dir fastapi uvicorn grpcio grpcio-tools pytest httpx python-multipart

COPY . /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
