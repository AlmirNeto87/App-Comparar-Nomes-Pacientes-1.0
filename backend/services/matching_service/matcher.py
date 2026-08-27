"""
matcher.py

Logica de comparacao aproximada de nomes (fuzzy matching), usada pelo
microservico de matching. E a mesma ideia usada no app mobile offline,
mas roda no servidor - util quando o celular quer delegar essa
comparacao pesada em vez de fazer localmente (por exemplo, listas
muito grandes).
"""

from rapidfuzz import fuzz

NOTA_MINIMA_DE_SIMILARIDADE = 85


def comparar_dois_nomes(nome_a, nome_b):
    """Retorna a nota de similaridade (0 a 100) entre dois nomes."""
    return fuzz.token_sort_ratio(nome_a.lower(), nome_b.lower())


def encontrar_nomes_em_comum(nomes_procurados, nomes_indexados):
    """
    nomes_procurados: lista de strings (nomes tirados da foto).
    nomes_indexados: lista de dicionarios {"nome": ..., "arquivo_pdf": ...}.

    Devolve a lista de correspondencias encontradas, cada uma com o
    nome original, o nome encontrado no PDF, o arquivo de origem e a
    nota de similaridade.
    """
    resultados = []

    for nome_procurado in nomes_procurados:
        melhor_nota = 0
        melhor_correspondencia = None

        for item in nomes_indexados:
            nota = comparar_dois_nomes(nome_procurado, item["nome"])
            if nota > melhor_nota:
                melhor_nota = nota
                melhor_correspondencia = item

        if melhor_nota >= NOTA_MINIMA_DE_SIMILARIDADE and melhor_correspondencia:
            resultados.append(
                {
                    "nome_procurado": nome_procurado,
                    "nome_encontrado": melhor_correspondencia["nome"],
                    "arquivo_pdf": melhor_correspondencia["arquivo_pdf"],
                    "similaridade": melhor_nota,
                }
            )

    return resultados
