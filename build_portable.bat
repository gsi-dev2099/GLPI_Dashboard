@echo off
echo ========================================================
echo  BUILD PORTABLE - GLPI DASHBOARD TV
echo ========================================================
echo.

echo [1/4] Instalando PyInstaller...
pip install pyinstaller

echo [2/4] Limpiando builds anteriores...
rmdir /s /q build dist
del /q *.spec

echo [3/4] Compilando EXE (Modo Folder)...
:: --onedir: Crea una carpeta con el exe y dependencias (Mas rapido y facil de depurar)
:: --noconsole: Para que no salga la ventana negra (Quitalo si quieres ver logs)
:: --name: Nombre del ejecutable
:: --add-data: Copia carpetas de recursos (Windows usa ;)

pyinstaller --noconsole --onedir --name "TicketDashboardTV" ^
    --add-data "static;static" ^
    --add-data "templates;templates" ^
    --hidden-import=driver_asyncmy ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.lifespan.on ^
    main.py

echo [4/4] Copiando archivo .env...
copy .env dist\TicketDashboardTV\.env

echo.
echo ========================================================
echo  COMPILACION FINALIZADA
echo ========================================================
echo.
echo Tu aplicacion portable esta en: dist\TicketDashboardTV
echo Sube esa carpeta completa a la TV/MiniPC.
echo Ejecuta "TicketDashboardTV.exe" dentro.
echo.
pause
