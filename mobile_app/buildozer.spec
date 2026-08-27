[app]
title = Comparador de Nomes
package.name = comparadordenomes
package.domain = org.seudominio

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

# Dependencias que vao dentro do pacote Android (recipes do python-for-android)
requirements = python3,kivy,plyer,pillow,requests,rapidfuzz

# Permissoes necessarias no Android: camera e acesso a internet
android.permissions = CAMERA,INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

orientation = portrait

[buildozer]
log_level = 2

# Observacao: o Tesseract OCR (usado pelo pytesseract) precisa de uma
# recipe separada para Android. Ver README.md, secao "OCR no Android",
# para instrucoes de como adicionar essa dependencia nativa.
