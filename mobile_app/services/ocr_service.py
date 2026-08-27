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
    Funcao principal do modulo: junta as duas etapas acima.
    Recebe o caminho da foto e devolve a lista de nomes encontrados.
    """
    texto_bruto = extrair_texto_da_imagem(caminho_imagem)
    lista_de_nomes = limpar_e_separar_nomes(texto_bruto)
    return lista_de_nomes
