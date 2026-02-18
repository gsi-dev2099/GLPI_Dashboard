#!/bin/bash

echo "========================================================"
echo " BUILD PORTABLE - GLPI DASHBOARD TV (LINUX)"
echo "========================================================"
echo

echo "[1/4] Instalando Dependencias..."
pip install pyinstaller -r requirements.txt

echo "[2/4] Limpiando builds anteriores..."
rm -rf build dist
rm -f *.spec

echo "[3/4] Compilando Binario (Modo Folder)..."
# --onedir: Crea carpeta con dependencias
# --noconsole: Sin terminal (útil si es GUI, pero aquí webserver está bien tener logs o no, noconsole ocultará output)
# --add-data: En Linux el separador es ':'

pyinstaller --noconsole --onedir --name "TicketDashboardTV" \
    --add-data "static:static" \
    --add-data "templates:templates" \
    --hidden-import=driver_asyncmy \
    --hidden-import=uvicorn.loops.auto \
    --hidden-import=uvicorn.protocols.http.auto \
    --hidden-import=uvicorn.lifespan.on \
    main.py

echo "[4/4] Copiando archivo .env..."
cp .env dist/TicketDashboardTV/.env

echo
echo "========================================================"
echo " COMPILACION FINALIZADA"
echo "========================================================"
echo
echo "Tu aplicacion portable esta en: dist/TicketDashboardTV"
echo "Entra a la carpeta y ejecuta: ./TicketDashboardTV"
echo
