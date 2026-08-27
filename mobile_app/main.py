"""
main.py

Ponto de entrada do app mobile.

Fluxo do usuario, em design bem simples:
1. Usuario aperta "Tirar foto" -> app abre a camera.
2. App roda OCR na foto e extrai a lista de nomes escritos nela.
3. App compara esses nomes com o indice local de nomes (que veio dos PDFs).
4. App mostra na tela quais nomes da foto foram encontrados em quais PDFs.
5. Em segundo plano, se tiver internet, o app sincroniza o indice local
   com o backend para manter os dados atualizados.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

from services import camera_service
from services import ocr_service
from services import local_database
from services import name_matcher
from services import sync_service


class TelaPrincipal(BoxLayout):
    """
    Tela unica do app (design simples de proposito).
    Contem os botoes de acao e a area de resultados.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=12, **kwargs)

        self.rotulo_status = Label(
            text="Toque em 'Tirar foto' para comecar",
            size_hint=(1, 0.1),
        )
        self.add_widget(self.rotulo_status)

        botao_tirar_foto = Button(
            text="Tirar foto da lista",
            size_hint=(1, 0.15),
            on_press=self.ao_tocar_tirar_foto,
        )
        self.add_widget(botao_tirar_foto)

        botao_sincronizar = Button(
            text="Sincronizar com o servidor",
            size_hint=(1, 0.15),
            on_press=self.ao_tocar_sincronizar,
        )
        self.add_widget(botao_sincronizar)

        # Area rolavel onde a lista de resultados vai aparecer
        area_rolavel = ScrollView(size_hint=(1, 0.6))
        self.lista_de_resultados = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=6
        )
        self.lista_de_resultados.bind(
            minimum_height=self.lista_de_resultados.setter("height")
        )
        area_rolavel.add_widget(self.lista_de_resultados)
        self.add_widget(area_rolavel)

        # garante que o banco local existe assim que o app abre
        local_database.criar_tabelas_se_nao_existirem()

    def atualizar_status(self, texto):
        """Atualiza o texto de status no topo da tela."""
        self.rotulo_status.text = texto

    def ao_tocar_tirar_foto(self, instancia_do_botao):
        """Chamado quando o usuario aperta o botao de tirar foto."""
        self.atualizar_status("Abrindo camera...")
        camera_service.tirar_foto(
            callback_sucesso=self.ao_foto_tirada_com_sucesso,
            callback_erro=self.ao_erro_generico,
        )

    def ao_foto_tirada_com_sucesso(self, caminho_da_foto):
        """
        Chamado depois que a foto foi salva no celular.
        Roda o OCR e a comparacao de nomes em seguida.
        """
        self.atualizar_status("Lendo nomes da foto (OCR)...")
        # Clock.schedule_once evita travar a interface enquanto processa
        Clock.schedule_once(lambda dt: self.processar_foto(caminho_da_foto), 0.1)

    def processar_foto(self, caminho_da_foto):
        """Extrai os nomes da foto e compara com o indice local."""
        nomes_da_foto = ocr_service.extrair_nomes_da_foto(caminho_da_foto)

        if not nomes_da_foto:
            self.atualizar_status("Nenhum nome foi reconhecido na foto.")
            return

        nomes_indexados = local_database.buscar_todos_os_nomes_indexados()

        if not nomes_indexados:
            self.atualizar_status(
                "Indice local vazio. Toque em 'Sincronizar' primeiro."
            )
            return

        resultados = name_matcher.encontrar_nomes_em_comum(
            nomes_da_foto, nomes_indexados
        )

        self.mostrar_resultados(resultados, total_nomes_na_foto=len(nomes_da_foto))

    def mostrar_resultados(self, resultados, total_nomes_na_foto):
        """Preenche a lista de resultados na tela."""
        self.lista_de_resultados.clear_widgets()

        self.atualizar_status(
            f"{len(resultados)} de {total_nomes_na_foto} nomes encontrados nos PDFs"
        )

        for resultado in resultados:
            texto_linha = (
                f"{resultado['nome_da_foto']}  ->  "
                f"{resultado['arquivo_pdf']} "
                f"({resultado['similaridade']:.0f}% de similaridade)"
            )
            self.lista_de_resultados.add_widget(
                Label(text=texto_linha, size_hint_y=None, height=32)
            )

    def ao_tocar_sincronizar(self, instancia_do_botao):
        """Chamado quando o usuario aperta o botao de sincronizar."""
        self.atualizar_status("Sincronizando com o servidor...")
        Clock.schedule_once(lambda dt: self.sincronizar(), 0.1)

    def sincronizar(self):
        """Baixa o indice atualizado de nomes do backend."""
        resultado = sync_service.sincronizar_indice_de_nomes()

        if resultado["sucesso"]:
            total = resultado["total_pdfs_sincronizados"]
            self.atualizar_status(f"Sincronizado! {total} PDFs no indice local.")
        else:
            self.atualizar_status(
                "Sem conexao com o servidor. Usando dados salvos localmente."
            )

    def ao_erro_generico(self, mensagem_de_erro):
        """Mostra qualquer erro de forma simples para o usuario."""
        self.atualizar_status(f"Erro: {mensagem_de_erro}")


class AppComparadorDeNomes(App):
    """Classe principal do aplicativo Kivy."""

    def build(self):
        self.title = "Comparador de nomes"
        return TelaPrincipal()


if __name__ == "__main__":
    AppComparadorDeNomes().run()
