"""
pdf_extractor.py

Le um arquivo PDF e extrai a lista de nomes contida nele.
Usa a biblioteca 'pymupdf' (importada como 'fitz'), que le o texto
de cada pagina do PDF sem precisar de OCR (assumindo que o PDF tem
texto selecionavel, e nao e so uma imagem escaneada).
"""

import re
import fitz  # pymupdf
import pdfplumber  # usado especificamente para reconhecer tabelas e colunas


def extrair_texto_do_pdf(caminho_pdf):
    """Le todas as paginas do PDF e devolve o texto completo, concatenado."""
    documento = fitz.open(caminho_pdf)

    texto_completo = ""
    for pagina in documento:
        texto_completo += pagina.get_text()

    documento.close()
    return texto_completo


def limpar_e_separar_nomes(texto_bruto):
    """
    Mesma logica de limpeza usada no OCR do app mobile: separa por linha,
    remove espacos e numeracao, ignora linhas muito curtas.
    """
    linhas = texto_bruto.split("\n")

    nomes_limpos = []
    for linha in linhas:
        linha_sem_espacos = linha.strip()

        if not linha_sem_espacos:
            continue

        linha_sem_numeracao = re.sub(r"^[\d\.\)\-\s]+", "", linha_sem_espacos)

        if len(linha_sem_numeracao) >= 2:
            nomes_limpos.append(linha_sem_numeracao)

    return nomes_limpos


def extrair_nomes_do_pdf(caminho_pdf):
    """
    Funcao principal do modulo (uso antigo, sem colunas): extrai e ja
    devolve os nomes limpos, tratando o PDF como uma lista simples de
    linhas de texto. Mantida para PDFs que nao tem uma tabela real.
    """
    texto_bruto = extrair_texto_do_pdf(caminho_pdf)
    lista_de_nomes = limpar_e_separar_nomes(texto_bruto)
    return lista_de_nomes


# --- A partir daqui: extracao de UMA coluna especifica de uma tabela ---
#
# O pymupdf (fitz) e otimo para pegar texto corrido, mas nao entende
# "isso e uma tabela com colunas". Para isso usamos o pdfplumber, que
# tem deteccao de tabelas embutida (baseada nas linhas/grades do PDF
# ou no alinhamento do texto).


def extrair_coluna_do_pdf(caminho_pdf, nome_da_coluna="Paciente"):
    """
    Abre o PDF, procura tabelas em cada pagina e devolve apenas os
    valores da coluna cujo cabecalho bate com 'nome_da_coluna' (ex:
    "Paciente"). Se o PDF tiver varias tabelas ou paginas, junta os
    resultados de todas.

    Se nenhuma tabela ou coluna com esse nome for encontrada, devolve
    lista vazia - nesse caso, o ideal e usar 'extrair_nomes_do_pdf'
    como alternativa (ver README, secao sobre PDFs sem tabela).
    """
    nome_procurado = nome_da_coluna.strip().lower()
    valores_da_coluna = []

    with pdfplumber.open(caminho_pdf) as documento:
        for pagina in documento.pages:
            tabelas_da_pagina = pagina.extract_tables()

            for tabela in tabelas_da_pagina:
                if not tabela or len(tabela) < 2:
                    continue  # precisa de cabecalho + pelo menos 1 linha

                linha_do_cabecalho = tabela[0]
                indice_da_coluna = None

                for indice, celula in enumerate(linha_do_cabecalho):
                    texto_da_celula = (celula or "").strip().lower()
                    if nome_procurado in texto_da_celula:
                        indice_da_coluna = indice
                        break

                if indice_da_coluna is None:
                    continue  # essa tabela nao tem a coluna procurada

                for linha_de_dado in tabela[1:]:
                    if indice_da_coluna < len(linha_de_dado):
                        valor = linha_de_dado[indice_da_coluna]
                        if valor and valor.strip():
                            valores_da_coluna.append(valor.strip())

    return valores_da_coluna


# --- A partir daqui: extracao por POSICAO das palavras (x, y) ---
#
# O 'extrair_coluna_do_pdf' acima so funciona quando o pdfplumber
# consegue reconhecer uma tabela de verdade (com bordas/grade). Muitos
# relatorios (como boletins de repasse, extratos, etc.) nao tem grade
# visivel - so texto alinhado em colunas. Para esses casos, olhamos a
# posicao x de cada palavra, do mesmo jeito que fazemos com a foto no
# app mobile.
#
# Complicador a mais: nomes de paciente as vezes quebram em duas
# linhas dentro do PDF (ex: "Jose Rafael dos Anjos" / "Gomes"). Para
# saber quando comeca um registro novo, usamos a coluna "Nº Atend."
# como ancora: toda linha de registro novo tem um numero nessa coluna;
# linhas sem numero ali sao continuacao do nome anterior.


def _normalizar_texto(texto):
    """Deixa o texto em minusculas e sem espacos nas pontas, para comparar."""
    return (texto or "").strip().lower()


def _agrupar_palavras_em_linhas_do_pdf(palavras, tolerancia_vertical=3):
    """
    Agrupa as palavras de uma pagina em linhas, comparando a posicao
    vertical ('top'). Palavras com o 'top' bem proximo sao consideradas
    da mesma linha da tabela.
    """
    linhas = []

    for palavra in sorted(palavras, key=lambda p: (p["top"], p["x0"])):
        linha_encontrada = None
        for linha in linhas:
            if abs(linha[0]["top"] - palavra["top"]) <= tolerancia_vertical:
                linha_encontrada = linha
                break

        if linha_encontrada is not None:
            linha_encontrada.append(palavra)
        else:
            linhas.append([palavra])

    for linha in linhas:
        linha.sort(key=lambda p: p["x0"])  # esquerda para direita

    linhas.sort(key=lambda linha: linha[0]["top"])  # cima para baixo
    return linhas


def _encontrar_faixas_de_colunas_por_posicao(linha_do_cabecalho, nome_da_coluna):
    """
    Dentro da linha de cabecalho, encontra a posicao x de tres pontos
    de referencia: inicio da coluna-ancora "Nº Atend.", inicio da
    coluna que queremos (ex: "Paciente") e inicio da proxima coluna
    depois dela (usado como limite direito). Isso monta uma "faixa" de
    pixels para cada coluna.
    """
    x_inicio_ancora = None
    x_inicio_coluna_alvo = None
    x_inicio_proxima_coluna = None

    nome_alvo_normalizado = _normalizar_texto(nome_da_coluna)
    coluna_alvo_encontrada = False

    for palavra in linha_do_cabecalho:
        texto = _normalizar_texto(palavra["text"])

        if "atend" in texto and x_inicio_ancora is None:
            x_inicio_ancora = palavra["x0"]

        if not coluna_alvo_encontrada and texto.startswith(nome_alvo_normalizado[:5]):
            x_inicio_coluna_alvo = palavra["x0"]
            coluna_alvo_encontrada = True
            continue  # a proxima palavra depois desta e a proxima coluna

        if coluna_alvo_encontrada and x_inicio_proxima_coluna is None:
            x_inicio_proxima_coluna = palavra["x0"]

    return x_inicio_ancora, x_inicio_coluna_alvo, x_inicio_proxima_coluna


def extrair_coluna_do_pdf_por_posicao(caminho_pdf, nome_da_coluna="Paciente"):
    """
    Funcao principal para PDFs tipo relatorio, sem grade de tabela
    visivel. Usa a posicao (x, y) de cada palavra para reconstruir as
    colunas, e trata corretamente nomes que quebram em duas linhas.

    Devolve a lista de valores da coluna pedida (ex: nomes de
    pacientes), um por registro.
    """
    valores_encontrados = []

    x_inicio_ancora = None
    x_inicio_coluna_alvo = None
    x_inicio_proxima_coluna = None

    with pdfplumber.open(caminho_pdf) as documento:
        for pagina in documento.pages:
            palavras_da_pagina = pagina.extract_words()
            linhas = _agrupar_palavras_em_linhas_do_pdf(palavras_da_pagina)

            # tenta achar o cabecalho nesta pagina (pode nao repetir em
            # todas as paginas do relatorio)
            for linha in linhas:
                textos_da_linha = [_normalizar_texto(p["text"]) for p in linha]
                tem_ancora = any("atend" in t for t in textos_da_linha)
                tem_coluna_alvo = any(
                    t.startswith(_normalizar_texto(nome_da_coluna)[:5])
                    for t in textos_da_linha
                )
                if tem_ancora and tem_coluna_alvo:
                    faixas = _encontrar_faixas_de_colunas_por_posicao(
                        linha, nome_da_coluna
                    )
                    if faixas[0] is not None:
                        x_inicio_ancora = faixas[0]
                    if faixas[1] is not None:
                        x_inicio_coluna_alvo = faixas[1]
                    if faixas[2] is not None:
                        x_inicio_proxima_coluna = faixas[2]
                    break

            # sem cabecalho identificado ainda (nem nesta nem em pagina
            # anterior), nao da pra saber onde fica a coluna - pula
            if x_inicio_ancora is None or x_inicio_coluna_alvo is None:
                continue

            limite_direito_coluna_alvo = (
                x_inicio_proxima_coluna - 5
                if x_inicio_proxima_coluna
                else x_inicio_coluna_alvo + 250
            )

            registro_em_construcao = None

            for linha in linhas:
                texto_completo_da_linha = " ".join(
                    p["text"] for p in linha
                ).strip().lower()

                # ignora linhas de titulo/cabecalho repetido e rodape
                if "repasse(s) para terceiro" in texto_completo_da_linha:
                    continue
                if texto_completo_da_linha.startswith("total"):
                    if registro_em_construcao:
                        valores_encontrados.append(registro_em_construcao.strip())
                        registro_em_construcao = None
                    continue

                # uma linha de registro NOVO tem um numero na coluna-ancora
                linha_tem_numero_na_ancora = any(
                    (x_inicio_ancora - 5) <= p["x0"] < (x_inicio_coluna_alvo - 5)
                    and p["text"].replace(".", "").isdigit()
                    for p in linha
                )

                palavras_da_coluna_alvo = [
                    p["text"]
                    for p in linha
                    if (x_inicio_coluna_alvo - 5)
                    <= p["x0"]
                    < limite_direito_coluna_alvo
                ]
                texto_da_coluna_alvo_nesta_linha = " ".join(palavras_da_coluna_alvo)

                if linha_tem_numero_na_ancora:
                    # fecha o registro anterior e comeca um novo
                    if registro_em_construcao:
                        valores_encontrados.append(registro_em_construcao.strip())
                    registro_em_construcao = texto_da_coluna_alvo_nesta_linha
                elif registro_em_construcao is not None and texto_da_coluna_alvo_nesta_linha:
                    # linha de continuacao: nome quebrado em duas linhas
                    registro_em_construcao += " " + texto_da_coluna_alvo_nesta_linha

            if registro_em_construcao:
                valores_encontrados.append(registro_em_construcao.strip())

    return valores_encontrados
