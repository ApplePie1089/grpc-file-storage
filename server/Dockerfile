FROM python:3.11-slim

RUN pip install --no-cache-dir grpcio grpcio-tools

COPY . /app
WORKDIR /app

CMD ["python", "server.py"]
