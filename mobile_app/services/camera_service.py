"""
camera_service.py

Responsavel por tirar foto usando a camera do celular.
Usa a biblioteca 'plyer', que funciona em Android/iOS quando empacotado
com Buildozer (Android) ou Briefcase/kivy-ios (iOS).
"""

import os
import time
from plyer import camera


# Pasta onde as fotos tiradas pelo usuario ficam salvas localmente
PASTA_FOTOS = os.path.join(os.path.expanduser("~"), "comparador_nomes_fotos")


def garantir_pasta_fotos():
    """Cria a pasta de fotos caso ela ainda nao exista."""
    if not os.path.exists(PASTA_FOTOS):
        os.makedirs(PASTA_FOTOS)


def gerar_caminho_foto():
    """
    Gera um caminho de arquivo unico para a proxima foto,
    usando a data/hora atual para evitar nomes repetidos.
    """
    garantir_pasta_fotos()
    nome_arquivo = f"lista_{int(time.time())}.jpg"
    return os.path.join(PASTA_FOTOS, nome_arquivo)


def tirar_foto(callback_sucesso, callback_erro=None):
    """
    Abre a camera do celular e tira uma foto.

    callback_sucesso: funcao chamada com o caminho da foto quando der certo.
    callback_erro: funcao chamada com a mensagem de erro, se algo falhar.
    """
    caminho_foto = gerar_caminho_foto()

    try:
        # plyer.camera.take_picture abre a camera nativa do celular
        camera.take_picture(
            filename=caminho_foto,
            on_complete=lambda caminho: callback_sucesso(caminho_foto),
        )
    except Exception as erro:
        if callback_erro:
            callback_erro(str(erro))
