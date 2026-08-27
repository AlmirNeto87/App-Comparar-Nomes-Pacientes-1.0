"""
sync_service.py

Responsavel por conversar com o backend (microservicos) quando o
celular tem internet disponivel. Duas tarefas principais:

1. Enviar um PDF novo para o backend processar (extrair os nomes).
2. Baixar o indice atualizado de nomes e salvar no banco local,
   para que o app continue funcionando mesmo offline depois.
"""

import datetime
import requests

from services import local_database

# Endereco do API Gateway do backend.
# Trocar pelo endereco real do servidor quando for para producao.
ENDERECO_BACKEND = "http://localhost:8000"

TEMPO_LIMITE_REQUISICAO_SEGUNDOS = 15


def esta_conectado_a_internet():
    """
    Verifica de forma simples se o backend esta acessivel.
    Se a requisicao falhar (sem internet ou servidor fora do ar),
    o app deve continuar funcionando em modo offline.
    """
    try:
        resposta = requests.get(
            f"{ENDERECO_BACKEND}/saude",
            timeout=TEMPO_LIMITE_REQUISICAO_SEGUNDOS,
        )
        return resposta.status_code == 200
    except requests.exceptions.RequestException:
        return False


def enviar_pdf_para_processar(caminho_pdf):
    """
    Envia um arquivo PDF para o backend, que vai extrair os nomes
    dele (usando o servico de PDF) e devolver a lista de nomes.
    """
    with open(caminho_pdf, "rb") as arquivo:
        arquivos = {"arquivo_pdf": arquivo}
        resposta = requests.post(
            f"{ENDERECO_BACKEND}/pdfs/processar",
            files=arquivos,
            timeout=TEMPO_LIMITE_REQUISICAO_SEGUNDOS,
        )

    resposta.raise_for_status()
    return resposta.json()


def sincronizar_indice_de_nomes():
    """
    Baixa do backend a lista mais recente de nomes indexados (de todos
    os PDFs ja processados) e substitui o cache local por ela.

    Deve ser chamada quando o app detectar conexao com a internet,
    por exemplo ao abrir o app ou por um botao de "atualizar".
    """
    if not esta_conectado_a_internet():
        return {"sucesso": False, "motivo": "sem conexao com o backend"}

    resposta = requests.get(
        f"{ENDERECO_BACKEND}/nomes/indice-completo",
        timeout=TEMPO_LIMITE_REQUISICAO_SEGUNDOS,
    )
    resposta.raise_for_status()
    lista_de_pdfs_com_nomes = resposta.json()["pdfs"]

    local_database.criar_tabelas_se_nao_existirem()
    local_database.limpar_indice_local()

    data_de_hoje = datetime.datetime.now().isoformat()

    for pdf_info in lista_de_pdfs_com_nomes:
        local_database.salvar_nomes_do_pdf(
            lista_de_nomes=pdf_info["nomes"],
            nome_arquivo_pdf=pdf_info["nome_arquivo"],
            data_sincronizacao=data_de_hoje,
        )

    return {"sucesso": True, "total_pdfs_sincronizados": len(lista_de_pdfs_com_nomes)}
