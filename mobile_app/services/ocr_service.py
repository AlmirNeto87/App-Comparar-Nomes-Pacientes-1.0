"""
ocr_service.py

Responsavel por transformar uma imagem (foto da lista impressa) em texto,
usando OCR (Reconhecimento Otico de Caracteres) diretamente no celular.
Isso permite que o app funcione mesmo sem internet.

Usa a biblioteca 'pytesseract', que depende do motor Tesseract OCR
instalado no dispositivo (no Android, geralmente incluido via recipe
do Buildozer; no desktop, precisa instalar o Tesseract separadamente).
"""

import os
import platform
import re
from PIL import Image
import pytesseract
from pytesseract import Output


# --- Localizacao automatica do Tesseract no Windows ---
#
# O pytesseract so encontra o programa Tesseract se ele estiver no
# PATH do Windows. Como o instalador nem sempre marca essa opcao,
# aqui a gente confere se o Tesseract esta no local padrao de
# instalacao e, se estiver, aponta direto pra ele - assim funciona
# mesmo sem mexer nas variaveis de ambiente do sistema.
if platform.system() == "Windows":
    CAMINHOS_PADRAO_WINDOWS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for caminho_candidato in CAMINHOS_PADRAO_WINDOWS:
        if os.path.exists(caminho_candidato):
            pytesseract.pytesseract.tesseract_cmd = caminho_candidato
            break


def extrair_texto_da_imagem(caminho_imagem, idioma="por"):
    """
    Le uma imagem do disco e retorna todo o texto encontrado nela.

    caminho_imagem: caminho do arquivo de foto tirada pelo usuario.
    idioma: idioma esperado no texto (padrao: portugues).

    Usa o modo '--psm 6' do Tesseract (assume que a imagem inteira e
    UM UNICO bloco de texto). Sem isso, o modo automatico padrao do
    Tesseract tenta adivinhar onde ficam os "blocos" de texto na
    imagem - e em tabelas largas (varias colunas) ele erra, tratando
    cada coluna como um bloco separado. Isso faz o texto sair fora de
    ordem: primeiro todos os numeros de atendimento, depois todas as
    datas, depois todos os nomes - cada "coluna" numa sequencia
    diferente, em vez de linha por linha como esta na foto.
    """
    imagem = Image.open(caminho_imagem)
    texto_bruto = pytesseract.image_to_string(
        imagem, lang=idioma, config="--psm 6"
    )
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

    Usa '--psm 6' pelo mesmo motivo explicado em
    'extrair_texto_da_imagem': evita que o Tesseract separe as
    colunas da tabela como blocos de leitura independentes.
    """
    imagem = Image.open(caminho_imagem)
    dados_brutos = pytesseract.image_to_data(
        imagem, lang=idioma, config="--psm 6", output_type=Output.DICT
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

    Atencao: essa extracao depende da posicao (x, y) de cada palavra
    continuar alinhada da primeira a ultima linha da foto. Fotos com
    perspectiva/inclinacao (comum em fotos tiradas a mao) podem fazer
    a coluna "escorregar" - nesse caso, prefira
    'extrair_nomes_da_foto_por_padrao' (ver mais abaixo), que nao
    depende de posicao.
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


# --- Extracao por PADRAO DE TEXTO (mais robusta a fotos tiradas a mao) ---
#
# A extracao por posicao (x, y) acima funciona bem quando a foto esta
# bem alinhada/reta. Mas fotos tiradas a mao quase sempre tem uma
# pequena inclinacao ou perspectiva, o que faz a posicao das colunas
# "escorregar" aos poucos conforme desce na lista - e ai a coluna
# calculada la em cima (no cabecalho) nao bate mais la embaixo.
#
# Para listas onde cada linha comeca com um padrao reconhecivel (ex:
# numero de atendimento + data + hora, como em listas de agenda/
# atendimento), e mais confiavel usar o TEXTO CORRIDO de cada linha e
# reconhecer onde o nome comeca e termina pelo formato das palavras -
# nomes proprios comecam com maiuscula ("Daniel", "Façanha"), e a
# proxima coluna geralmente vem em MAIUSCULAS ("IPM", "LIV SAÚDE") ou
# e um numero/hora - o que sinaliza o fim do nome.

PADRAO_INICIO_DE_REGISTRO = re.compile(
    r"^\s*\d{4,9}\s+\d{2}/\d{2}/\d{2,4}\s+\d{1,2}:\d{2}(:\d{2})?\s+(?P<resto>.+)$"
)

CONECTORES_COMUNS_EM_NOMES = {"de", "da", "do", "dos", "das", "e"}


def _parece_palavra_de_nome(palavra):
    """
    Uma 'palavra de nome' comeca com maiuscula seguida de minusculas
    (ex: "Daniel", "Façanha"), ou e um conector comum em nomes
    portugueses (ex: "de", "da", "dos"). Uma palavra toda em
    MAIUSCULAS (ex: "IPM", "LIV") ou um numero marca o fim do nome.
    """
    if palavra.lower() in CONECTORES_COMUNS_EM_NOMES:
        return True
    return bool(re.match(r"^[A-ZÀ-Ý][a-zà-ÿ]+$", palavra))


def _extrair_nome_do_inicio_do_texto(texto):
    """
    Recebe o restante da linha (depois do numero/data/hora) e devolve
    so as palavras que parecem nome, parando na primeira palavra que
    nao parece (normalmente o inicio da proxima coluna, tipo o
    convenio).
    """
    palavras_do_nome = []
    for palavra in texto.split():
        if _parece_palavra_de_nome(palavra):
            palavras_do_nome.append(palavra)
        else:
            break
    return " ".join(palavras_do_nome)


def extrair_nomes_da_foto_por_padrao(caminho_imagem):
    """
    Extrai nomes de listas onde cada linha comeca com um numero de
    atendimento, seguido de data e hora (formato comum em listas de
    agenda/atendimento medico). Funciona direto em cima do texto
    corrido do OCR (nao usa posicao x/y), o que a torna bem mais
    tolerante a fotos tiradas com um pequeno angulo do que a extracao
    por posicao.
    """
    texto_bruto = extrair_texto_da_imagem(caminho_imagem)
    nomes_encontrados = []

    for linha in texto_bruto.split("\n"):
        correspondencia = PADRAO_INICIO_DE_REGISTRO.match(linha)
        if not correspondencia:
            continue  # essa linha nao comeca com numero+data+hora

        nome = _extrair_nome_do_inicio_do_texto(correspondencia.group("resto"))
        if len(nome) >= 2:
            nomes_encontrados.append(nome)

    return nomes_encontrados


def extrair_nomes_da_lista_impressa(caminho_imagem, nome_da_coluna="Paciente"):
    """
    Funcao recomendada para o app usar. Tenta, em ordem de
    confiabilidade:

    1) padrao de linha "numero + data + hora + nome" - o mais robusto
       a fotos tiradas a mao, ideal para listas de agenda/atendimento
    2) extracao por posicao (x, y) do cabecalho - funciona bem quando
       a foto esta bem alinhada e a lista nao segue o padrao acima
    3) leitura do texto inteiro, linha a linha - ultimo recurso, para
       nunca devolver uma lista vazia sem tentar de verdade

    Remove nomes repetidos mantendo a ordem em que apareceram.
    """
    nomes = extrair_nomes_da_foto_por_padrao(caminho_imagem)

    if not nomes:
        nomes = extrair_coluna_da_foto(caminho_imagem, nome_da_coluna)

    if not nomes:
        nomes = extrair_nomes_da_foto(caminho_imagem)

    return list(dict.fromkeys(nomes))
