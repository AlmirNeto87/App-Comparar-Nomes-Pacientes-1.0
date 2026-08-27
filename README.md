# Comparador de nomes

App mobile em Python que tira foto de uma lista impressa de nomes, le
os nomes com OCR, e verifica quais desses nomes ja existem em um
conjunto de arquivos PDF. Funciona offline (indice local) e sincroniza
com um backend em microservicos quando ha internet.

## Como o projeto esta organizado

```
comparador-nomes/
├── mobile_app/              # App mobile (Kivy)
│   ├── main.py               # Tela principal e fluxo do usuario
│   ├── services/
│   │   ├── camera_service.py    # Tira foto usando a camera do celular
│   │   ├── ocr_service.py       # Le texto da foto (OCR local)
│   │   ├── local_database.py    # Cache local em SQLite (uso offline)
│   │   ├── name_matcher.py      # Compara nomes localmente (fuzzy match)
│   │   └── sync_service.py      # Sincroniza com o backend quando online
│   ├── requirements.txt
│   └── buildozer.spec        # Configuracao para gerar o APK Android
│
├── backend/                 # Backend em microservicos (FastAPI)
│   ├── gateway/               # API Gateway (porta 8000) - unico ponto
│   │   └── main.py            # de entrada usado pelo app mobile
│   ├── services/
│   │   ├── pdf_service/        # Extrai nomes dos PDFs (porta 8001)
│   │   └── matching_service/   # Compara nomes no servidor (porta 8002)
│   ├── requirements.txt
│   └── docker-compose.yml    # Sobe os 3 servicos de uma vez
│
├── .gitignore
└── README.md
```

## Arquitetura, em resumo

- **App mobile**: tira a foto, faz OCR local e guarda um indice de
  nomes em SQLite. Funciona sem internet.
- **API Gateway**: unico endereco que o app mobile conhece. Encaminha
  os pedidos para o microservico certo.
- **Servico de PDF**: recebe PDFs, extrai o texto e devolve a lista de
  nomes encontrados.
- **Servico de matching**: compara listas de nomes usando fuzzy
  matching (para tolerar erros de OCR, como "Joao" vs "Jo3o").

Cada microservico roda e escala de forma independente. Se o gargalo
for processar PDFs, so o `pdf_service` precisa ser escalado; se for
comparar nomes, so o `matching_service`.

## Rodando o backend

Pre-requisito: Docker e Docker Compose instalados.

```bash
cd backend
docker compose up --build
```

Isso sobe:
- API Gateway em `http://localhost:8000`
- Servico de PDF em `http://localhost:8001`
- Servico de matching em `http://localhost:8002`

Para testar sem Docker, rodando cada servico manualmente (util durante
o desenvolvimento):

```bash
cd backend
python -m venv venv
source venv/bin/activate        # no Windows: venv\Scripts\activate
pip install -r requirements.txt

# em 3 terminais separados:
uvicorn gateway.main:app --port 8000 --reload
uvicorn services.pdf_service.main:app --port 8001 --reload
uvicorn services.matching_service.main:app --port 8002 --reload
```

### Testando o backend rapidamente

```bash
# checar se o gateway esta no ar
curl http://localhost:8000/saude

# enviar um PDF para ser processado
curl -X POST http://localhost:8000/pdfs/processar \
  -F "arquivo_pdf=@caminho/para/lista.pdf"

# baixar o indice completo de nomes (o mesmo que o app mobile sincroniza)
curl http://localhost:8000/nomes/indice-completo
```

## Rodando o app mobile (modo desenvolvimento, no computador)

O Kivy roda tanto no celular quanto no computador, o que ajuda a
testar a interface antes de gerar o APK.

```bash
cd mobile_app
python -m venv venv
source venv/bin/activate        # no Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

No computador, a camera pode nao funcionar dependendo do sistema
operacional - nesse caso, teste o fluxo de sincronizacao e comparacao
usando uma imagem colocada manualmente na pasta de fotos.

### Gerando o APK para Android

```bash
cd mobile_app
pip install buildozer
buildozer android debug
```

O APK gerado fica em `mobile_app/bin/`.

### OCR no Android

O `pytesseract` depende do motor Tesseract OCR instalado no
dispositivo. No Android, isso exige adicionar uma recipe do Tesseract
ao `python-for-android` (usado por baixo dos panos pelo Buildozer).
Se preferir simplificar essa etapa, uma alternativa e trocar o OCR
local por uma biblioteca 100% Python como o `easyocr`, ou delegar o
OCR para o backend quando houver internet (mantendo o fluxo offline
como modo de contingencia).

## Fluxo completo, de ponta a ponta

1. Alguem sobe os PDFs existentes para o backend (`POST /pdfs/processar`).
2. O app mobile sincroniza (`Sincronizar com o servidor`), baixando o
   indice de nomes e guardando localmente.
3. O usuario tira foto da lista impressa.
4. O app roda OCR na foto, compara com o indice local (mesmo offline)
   e mostra quais nomes da foto foram encontrados, e em qual PDF.

## Proximos passos sugeridos

- Adicionar autenticacao no API Gateway antes de expor o backend
  publicamente.
- Adicionar testes automatizados para `name_matcher.py` e
  `pdf_extractor.py`, que sao as pecas mais sensiveis a erro.
- Trocar o SQLite do backend/armazenamento de PDFs por um banco mais
  robusto (Postgres) se o volume de PDFs crescer muito.
