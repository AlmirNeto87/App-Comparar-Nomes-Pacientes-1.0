"""
main.py (API Gateway)

Ponto unico de entrada do backend. O app mobile so conversa com o
Gateway - ele e quem sabe para qual microservico encaminhar cada
pedido. Isso permite trocar, mover ou escalar os microservicos por
baixo dos panos sem o app mobile precisar saber onde cada um esta.

Roda na porta 8000 (a mesma usada em ENDERECO_BACKEND no app mobile).
"""

import httpx
from fastapi import FastAPI, UploadFile, File

app = FastAPI(title="API Gateway - Comparador de Nomes")

# Enderecos internos dos microservicos.
# Em producao, isso normalmente viria de variaveis de ambiente ou de um
# sistema de descoberta de servicos (service discovery).
ENDERECO_SERVICO_PDF = "http://localhost:8001"
ENDERECO_SERVICO_MATCHING = "http://localhost:8002"

TEMPO_LIMITE_SEGUNDOS = 30


@app.get("/saude")
def verificar_saude():
    """
    Usado pelo app mobile para saber se ha conexao com o backend
    antes de tentar sincronizar.
    """
    return {"status": "ok", "servico": "api_gateway"}


@app.post("/pdfs/processar")
async def processar_pdf(arquivo_pdf: UploadFile = File(...)):
    """
    Recebe um PDF do app mobile e repassa para o servico de PDF
    extrair os nomes.
    """
    conteudo_do_arquivo = await arquivo_pdf.read()

    async with httpx.AsyncClient(timeout=TEMPO_LIMITE_SEGUNDOS) as cliente_http:
        resposta = await cliente_http.post(
            f"{ENDERECO_SERVICO_PDF}/extrair-nomes",
            files={"arquivo_pdf": (arquivo_pdf.filename, conteudo_do_arquivo)},
        )

    resposta.raise_for_status()
    return resposta.json()


@app.get("/nomes/indice-completo")
async def obter_indice_completo():
    """
    Repassa para o servico de PDF o pedido de gerar o indice completo
    (todos os nomes de todos os PDFs ja processados). Usado pelo app
    mobile na hora de sincronizar o cache local.
    """
    async with httpx.AsyncClient(timeout=TEMPO_LIMITE_SEGUNDOS) as cliente_http:
        resposta = await cliente_http.get(f"{ENDERECO_SERVICO_PDF}/indice-completo")

    resposta.raise_for_status()
    return resposta.json()


@app.post("/nomes/comparar")
async def comparar_nomes(pedido_de_comparacao: dict):
    """
    Repassa para o servico de matching um pedido de comparacao de
    nomes. Alternativa a fazer a comparacao localmente no celular -
    util para listas muito grandes.
    """
    async with httpx.AsyncClient(timeout=TEMPO_LIMITE_SEGUNDOS) as cliente_http:
        resposta = await cliente_http.post(
            f"{ENDERECO_SERVICO_MATCHING}/comparar",
            json=pedido_de_comparacao,
        )

    resposta.raise_for_status()
    return resposta.json()
