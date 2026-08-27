# Este Dockerfile espera ser construido com o contexto na pasta "backend/"
# (veja docker-compose.yml: "context: ./backend, dockerfile: gateway/Dockerfile")

FROM python:3.12-slim

WORKDIR /app

# requirements.txt fica na raiz de backend/, compartilhado pelos servicos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia so o codigo deste microservico
COPY gateway/ .

# Porta padrao do API Gateway
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
