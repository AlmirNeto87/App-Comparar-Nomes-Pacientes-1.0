"""
name_matcher.py

Compara os nomes extraidos da foto (lista impressa) com os nomes
guardados no banco de dados local (que vieram dos PDFs).

Usa 'rapidfuzz' para comparacao aproximada (fuzzy matching), porque o
OCR quase nunca acerta 100% do texto - por exemplo, pode ler "Joao"
como "Jo3o" ou "Joilo". Com fuzzy matching, ainda assim conseguimos
encontrar o nome correspondente.
"""

from rapidfuzz import fuzz

# Nota de similaridade minima (0 a 100) para considerar dois nomes como
# o mesmo. Quanto maior, mais rigido fica o filtro.
NOTA_MINIMA_DE_SIMILARIDADE = 85


def comparar_dois_nomes(nome_da_foto, nome_do_pdf):
    """
    Retorna a nota de similaridade (0 a 100) entre um nome tirado da
    foto e um nome que ja esta indexado (veio de um PDF).
    """
    nota = fuzz.token_sort_ratio(nome_da_foto.lower(), nome_do_pdf.lower())
    return nota


def encontrar_nomes_em_comum(nomes_da_foto, nomes_indexados):
    """
    Funcao principal do modulo.

    nomes_da_foto: lista de strings, nomes extraidos da foto pelo OCR.
    nomes_indexados: lista de dicionarios {"nome": ..., "arquivo_pdf": ...}
                      vindos do banco de dados local.

    Retorna uma lista de resultados, um para cada nome da foto que foi
    encontrado em algum PDF, incluindo em qual PDF ele apareceu e a
    nota de similaridade.
    """
    resultados_encontrados = []

    for nome_da_foto in nomes_da_foto:
        melhor_nota = 0
        melhor_correspondencia = None

        for item_indexado in nomes_indexados:
            nota = comparar_dois_nomes(nome_da_foto, item_indexado["nome"])

            if nota > melhor_nota:
                melhor_nota = nota
                melhor_correspondencia = item_indexado

        if melhor_nota >= NOTA_MINIMA_DE_SIMILARIDADE and melhor_correspondencia:
            resultados_encontrados.append(
                {
                    "nome_da_foto": nome_da_foto,
                    "nome_encontrado_no_pdf": melhor_correspondencia["nome"],
                    "arquivo_pdf": melhor_correspondencia["arquivo_pdf"],
                    "similaridade": melhor_nota,
                }
            )

    return resultados_encontrados
