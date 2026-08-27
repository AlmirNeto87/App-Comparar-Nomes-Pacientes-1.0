# Este Dockerfile espera ser construido com o contexto na pasta "backend/"
# (veja docker-compose.yml)

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/matching_service/ .

# Porta padrao do servico de matching
EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
