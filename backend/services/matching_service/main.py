"""
main.py (servico de matching)

Microservico responsavel por UMA coisa: comparar uma lista de nomes
(vinda da foto) com uma lista de nomes ja indexados (vindos dos PDFs),
e devolver quais nomes batem.

Roda de forma independente na porta 8002. Pode ser escalado sozinho se
o gargalo for a quantidade de comparacoes (por exemplo, muitos
usuarios comparando listas grandes ao mesmo tempo).
"""

from fastapi import FastAPI
from pydantic import BaseModel

from matcher import encontrar_nomes_em_comum

app = FastAPI(title="Servico de matching")


class ItemIndexado(BaseModel):
    """Representa um nome ja indexado, vindo de algum PDF."""
    nome: str
    arquivo_pdf: str


class PedidoDeComparacao(BaseModel):
    """Formato esperado do pedido de comparacao de nomes."""
    nomes_procurados: list[str]
    nomes_indexados: list[ItemIndexado]


@app.get("/saude")
def verificar_saude():
    """Endpoint simples para checar se o servico esta no ar."""
    return {"status": "ok", "servico": "matching_service"}


@app.post("/comparar")
def comparar_nomes(pedido: PedidoDeComparacao):
    """
    Recebe a lista de nomes procurados e a lista de nomes indexados,
    e devolve as correspondencias encontradas.
    """
    nomes_indexados_como_dicionario = [
        {"nome": item.nome, "arquivo_pdf": item.arquivo_pdf}
        for item in pedido.nomes_indexados
    ]

    resultados = encontrar_nomes_em_comum(
        pedido.nomes_procurados, nomes_indexados_como_dicionario
    )

    return {"total_encontrados": len(resultados), "resultados": resultados}
