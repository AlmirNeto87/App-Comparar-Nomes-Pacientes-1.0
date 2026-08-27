"""
local_database.py

Guarda, no proprio celular, uma copia local (cache) dos nomes que ja
foram extraidos dos arquivos PDF pelo backend. Isso e o que permite o
app funcionar em modo offline: mesmo sem internet, a comparacao de
nomes acontece contra esse banco local.

Usa SQLite, que ja vem embutido no Python (nao precisa instalar nada).
"""

import sqlite3
import os

CAMINHO_BANCO = os.path.join(os.path.expanduser("~"), "comparador_nomes_cache.db")


def conectar():
    """Abre uma conexao com o banco de dados local."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    return conexao


def criar_tabelas_se_nao_existirem():
    """
    Cria a tabela 'nomes_indexados' caso o banco local esteja vazio.
    Cada linha representa um nome encontrado em algum PDF.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nomes_indexados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nome_arquivo_pdf TEXT NOT NULL,
            data_sincronizacao TEXT NOT NULL
        )
        """
    )

    conexao.commit()
    conexao.close()


def salvar_nomes_do_pdf(lista_de_nomes, nome_arquivo_pdf, data_sincronizacao):
    """
    Salva no banco local os nomes que vieram de um PDF especifico.
    Usado depois que o app sincroniza com o backend.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    for nome in lista_de_nomes:
        cursor.execute(
            """
            INSERT INTO nomes_indexados (nome, nome_arquivo_pdf, data_sincronizacao)
            VALUES (?, ?, ?)
            """,
            (nome, nome_arquivo_pdf, data_sincronizacao),
        )

    conexao.commit()
    conexao.close()


def buscar_todos_os_nomes_indexados():
    """
    Retorna todos os nomes salvos localmente, junto com o PDF de origem.
    Essa lista e usada para comparar com os nomes tirados da foto.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT nome, nome_arquivo_pdf FROM nomes_indexados")
    resultados = cursor.fetchall()

    conexao.close()

    # devolve uma lista de dicionarios, mais facil de usar no resto do app
    return [{"nome": linha[0], "arquivo_pdf": linha[1]} for linha in resultados]


def limpar_indice_local():
    """Apaga todos os nomes salvos localmente (usado antes de re-sincronizar)."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM nomes_indexados")
    conexao.commit()
    conexao.close()
