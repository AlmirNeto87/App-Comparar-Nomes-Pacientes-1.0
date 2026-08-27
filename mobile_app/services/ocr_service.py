"""
ocr_service.py

Responsavel por transformar uma imagem (foto da lista impressa) em texto,
usando OCR (Reconhecimento Otico de Caracteres) diretamente no celular.
Isso permite que o app funcione mesmo sem internet.

Usa a biblioteca 'pytesseract', que depende do motor Tesseract OCR
instalado no dispositivo (no Android, geralmente incluido via recipe
do Buildozer; no desktop, precisa instalar o Tesseract separadamente).
"""

import re
from PIL import Image
import pytesseract
from pytesseract import Output


def extrair_texto_da_imagem(caminho_imagem, idioma="por"):
    """
    Le uma imagem do disco e retorna todo o texto encontrado nela.

    caminho_imagem: caminho do arquivo de foto tirada pelo usuario.
    idioma: idioma esperado no texto (padrao: portugues).
    """
    imagem = Image.open(caminho_imagem)
    texto_bruto = pytesseract.image_to_string(imagem, lang=idioma)
    return texto_bruto


def limpar_e_separar_nomes(texto_bruto):
    """
    Recebe o texto bruto retornado pelo OCR e devolve uma lista de nomes
    limpos, um por linha, sem espacos extras e sem linhas vazias.

    Essa funcao e simples de proposito: o OCR de fotos costuma trazer
    ruido (numeros de linha, tracos, espacos duplicados), entao aqui
    fazemos uma limpeza basica antes de comparar com os PDFs.
    """
    linhas = texto_bruto.split("\n")

    nomes_limpos = []
    for linha in linhas:
        linha_sem_espacos = linha.strip()

        if not linha_sem_espacos:
            continue

        # remove numeracao no inicio da linha, tipo "1.", "23)", "-"
        linha_sem_numeracao = re.sub(r"^[\d\.\)\-\s]+", "", linha_sem_espacos)

        if len(linha_sem_numeracao) >= 2:
            nomes_limpos.append(linha_sem_numeracao)

    return nomes_limpos


def extrair_nomes_da_foto(caminho_imagem):
    """
    Funcao principal do modulo (uso antigo, sem colunas): junta as duas
    etapas acima. Recebe o caminho da foto e devolve a lista de nomes
    encontrados, tratando a foto como uma lista simples (uma coluna so).
    Mantida para listas impressas que nao tem varias colunas.
    """
    texto_bruto = extrair_texto_da_imagem(caminho_imagem)
    lista_de_nomes = limpar_e_separar_nomes(texto_bruto)
    return lista_de_nomes


# --- A partir daqui: extracao de UMA coluna especifica de uma tabela ---
#
# Quando a foto tem varias colunas (ex: "Leito | Paciente | Idade"),
# nao da para so separar por linha - precisamos saber a POSICAO (x, y)
# de cada palavra na imagem, para saber a qual coluna ela pertence.
# O pytesseract consegue devolver isso com "image_to_data".


def extrair_palavras_com_posicao(caminho_imagem, idioma="por"):
    """
    Le a imagem e devolve, para cada palavra reconhecida, o texto e a
    posicao dela (coordenadas x, y na foto), alem de a qual linha ela
    pertence segundo o Tesseract.
    """
    imagem = Image.open(caminho_imagem)
    dados_brutos = pytesseract.image_to_data(
        imagem, lang=idioma, output_type=Output.DICT
    )
    return dados_brutos


def agrupar_palavras_em_linhas(dados_brutos):
    """
    Agrupa as palavras soltas devolvidas pelo Tesseract em linhas da
    tabela (uma linha = uma pessoa, por exemplo), e dentro de cada
    linha, ordena as palavras da esquerda para a direita.
    """
    linhas_por_chave = {}
    total_de_palavras = len(dados_brutos["text"])

    for indice in range(total_de_palavras):
        texto_da_palavra = dados_brutos["text"][indice].strip()
        if not texto_da_palavra:
            continue

        # o Tesseract ja identifica bloco/paragrafo/linha de cada palavra
        chave_da_linha = (
            dados_brutos["block_num"][indice],
            dados_brutos["par_num"][indice],
            dados_brutos["line_num"][indice],
        )

        palavra = {
            "texto": texto_da_palavra,
            "x_inicio": dados_brutos["left"][indice],
            "x_fim": dados_brutos["left"][indice] + dados_brutos["width"][indice],
            "y_inicio": dados_brutos["top"][indice],
        }

        linhas_por_chave.setdefault(chave_da_linha, []).append(palavra)

    # ordena as linhas de cima para baixo (pela posicao y da primeira palavra)
    linhas_ordenadas = sorted(
        linhas_por_chave.values(), key=lambda linha: linha[0]["y_inicio"]
    )

    # dentro de cada linha, ordena as palavras da esquerda para a direita
    for linha in linhas_ordenadas:
        linha.sort(key=lambda palavra: palavra["x_inicio"])

    return linhas_ordenadas


def encontrar_faixa_horizontal_da_coluna(linha_do_cabecalho, nome_da_coluna):
    """
    Procura, na linha de cabecalho da tabela (ex: "Leito Paciente
    Idade"), a palavra que da nome a coluna que queremos (ex:
    "Paciente"), e calcula a faixa horizontal (inicio/fim em pixels)
    que essa coluna ocupa. Palavras de outras linhas dentro dessa
    faixa serao consideradas parte da coluna.
    """
    nome_procurado = nome_da_coluna.strip().lower()

    for indice, palavra_do_cabecalho in enumerate(linha_do_cabecalho):
        texto_do_cabecalho = palavra_do_cabecalho["texto"].strip().lower()

        if nome_procurado in texto_do_cabecalho or texto_do_cabecalho in nome_procurado:
            margem_de_tolerancia = 20  # pixels, para nao cortar a coluna errado
            inicio_da_faixa = palavra_do_cabecalho["x_inicio"] - margem_de_tolerancia

            # a coluna termina onde comeca a proxima coluna do cabecalho
            existe_proxima_coluna = indice + 1 < len(linha_do_cabecalho)
            if existe_proxima_coluna:
                fim_da_faixa = linha_do_cabecalho[indice + 1]["x_inicio"] - 5
            else:
                fim_da_faixa = 100_000  # ultima coluna: sem limite a direita

            return inicio_da_faixa, fim_da_faixa

    return None


def extrair_coluna_da_foto(caminho_imagem, nome_da_coluna="Paciente"):
    """
    Funcao principal para fotos com varias colunas.

    Le a foto, assume que a PRIMEIRA linha reconhecida e o cabecalho
    da tabela (ex: "Leito | Paciente | Idade"), descobre onde fica a
    coluna pedida (ex: "Paciente") e devolve so os valores dessa
    coluna, um por linha de dado (pulando o cabecalho).

    Se o cabecalho nao for encontrado, devolve uma lista vazia -
    melhor avisar o usuario do que adivinhar a coluna errada.
    """
    dados_brutos = extrair_palavras_com_posicao(caminho_imagem)
    linhas = agrupar_palavras_em_linhas(dados_brutos)

    if len(linhas) < 2:
        return []  # nao ha cabecalho + pelo menos uma linha de dado

    linha_do_cabecalho = linhas[0]
    faixa_da_coluna = encontrar_faixa_horizontal_da_coluna(
        linha_do_cabecalho, nome_da_coluna
    )

    if faixa_da_coluna is None:
        return []

    inicio_da_faixa, fim_da_faixa = faixa_da_coluna

    valores_da_coluna = []
    for linha_de_dado in linhas[1:]:  # pula a linha de cabecalho
        palavras_dentro_da_coluna = [
            palavra["texto"]
            for palavra in linha_de_dado
            if inicio_da_faixa <= palavra["x_inicio"] <= fim_da_faixa
        ]

        if palavras_dentro_da_coluna:
            valores_da_coluna.append(" ".join(palavras_dentro_da_coluna))

    return valores_da_coluna
