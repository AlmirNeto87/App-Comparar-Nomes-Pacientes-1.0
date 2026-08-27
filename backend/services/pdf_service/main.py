"""
main.py (servico de PDF)

Microservico responsavel por UMA coisa: receber um arquivo PDF e
devolver a lista de nomes encontrados nele.

Roda de forma independente dos outros microservicos, na porta 8001.
Pode ser escalado sozinho se o gargalo do sistema for processamento
de PDFs (por exemplo, rodando varias copias atras de um load balancer).
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from pdf_extractor import (
    extrair_nomes_do_pdf,
    extrair_coluna_do_pdf,
    extrair_coluna_do_pdf_por_posicao,
)

# Nome da coluna usada por padrao quando o PDF tem uma tabela com
# varias colunas (ex: "Leito | Paciente | Idade"). Pode ser trocado
# em cada chamada da API via o parametro 'nome_coluna'.
NOME_DA_COLUNA_PADRAO = "Paciente"

app = FastAPI(title="Servico de PDF")

# Pasta onde os PDFs recebidos ficam guardados permanentemente,
# para que o indice completo possa ser reconstruido depois.
PASTA_PDFS_ARMAZENADOS = os.path.join(os.path.dirname(__file__), "pdfs_armazenados")
os.makedirs(PASTA_PDFS_ARMAZENADOS, exist_ok=True)


@app.get("/saude")
def verificar_saude():
    """Endpoint simples para checar se o servico esta no ar."""
    return {"status": "ok", "servico": "pdf_service"}


def extrair_coluna_com_alternativas(caminho_pdf, nome_coluna):
    """
    Tenta extrair a coluna pedida em ordem de precisao:
    1) deteccao de tabela por grade (funciona em PDFs com bordas visiveis)
    2) deteccao por posicao das palavras (funciona em relatorios sem
       grade, tipo boletins/extratos - e o caso mais comum na pratica)
    3) por ultimo, se nada funcionar, devolve o texto inteiro linha a
       linha, so para nao devolver uma lista vazia sem explicacao.

    Remove nomes repetidos mantendo a ordem (um paciente pode aparecer
    varias vezes no PDF, uma linha por procedimento, por exemplo).
    """
    nomes = extrair_coluna_do_pdf(caminho_pdf, nome_coluna)

    if not nomes:
        nomes = extrair_coluna_do_pdf_por_posicao(caminho_pdf, nome_coluna)

    if not nomes:
        nomes = extrair_nomes_do_pdf(caminho_pdf)

    nomes_sem_repeticao = list(dict.fromkeys(nomes))
    return nomes_sem_repeticao


@app.post("/extrair-nomes")
async def extrair_nomes(
    arquivo_pdf: UploadFile = File(...),
    nome_coluna: str = Form(default=NOME_DA_COLUNA_PADRAO),
):
    """
    Recebe um arquivo PDF, salva permanentemente na pasta de PDFs
    armazenados e devolve a lista de nomes extraidos da coluna pedida
    (ver 'extrair_coluna_com_alternativas' para a ordem de tentativas).
    """
    caminho_definitivo = os.path.join(PASTA_PDFS_ARMAZENADOS, arquivo_pdf.filename)

    with open(caminho_definitivo, "wb") as arquivo_destino:
        shutil.copyfileobj(arquivo_pdf.file, arquivo_destino)

    lista_de_nomes = extrair_coluna_com_alternativas(caminho_definitivo, nome_coluna)

    return {
        "nome_arquivo": arquivo_pdf.filename,
        "total_nomes": len(lista_de_nomes),
        "nomes": lista_de_nomes,
    }


@app.get("/pdfs-armazenados")
def listar_pdfs_armazenados():
    """Lista todos os PDFs que ja foram enviados e processados ate agora."""
    arquivos = os.listdir(PASTA_PDFS_ARMAZENADOS)
    return {"pdfs": arquivos}


@app.get("/indice-completo")
def gerar_indice_completo(nome_coluna: str = NOME_DA_COLUNA_PADRAO):
    """
    Reprocessa todos os PDFs armazenados e devolve o indice completo
    de nomes. Usado pelo API Gateway para responder a sincronizacao
    do app mobile. Usa a mesma cadeia de tentativas do endpoint
    '/extrair-nomes' (ver 'extrair_coluna_com_alternativas').
    """
    resultado = []

    for nome_arquivo in os.listdir(PASTA_PDFS_ARMAZENADOS):
        caminho_completo = os.path.join(PASTA_PDFS_ARMAZENADOS, nome_arquivo)
        nomes = extrair_coluna_com_alternativas(caminho_completo, nome_coluna)
        resultado.append({"nome_arquivo": nome_arquivo, "nomes": nomes})

    return {"pdfs": resultado}
