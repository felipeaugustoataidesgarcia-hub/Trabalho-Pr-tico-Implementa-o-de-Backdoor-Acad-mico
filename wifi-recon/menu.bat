@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ---------------------------------------------------------------
rem  menu.bat - Menu Windows do sistema de auditoria Wi-Fi.
rem  Cobre o que roda no Windows: recon, IP, wordlist, relatorio e
rem  painel web. A quebra da senha (captura/WPS) exige Kali Linux.
rem  Uso academico / autorizado.
rem ---------------------------------------------------------------

rem Detecta o interpretador Python (python ou py)
where python >nul 2>nul
if %errorlevel%==0 (set "PY=python") else (set "PY=py")

:menu
cls
echo ============================================================
echo    AUDITORIA WI-FI  -  Menu Windows
echo    Alvo: TP-Link AC750 (Archer C20)   -   uso academico
echo ============================================================
echo.
echo   1^) Reconhecimento (lista redes: MAC, canal, freq, cripto^)
echo   2^) Reconhecimento + salvar dados.json e dados.csv
echo   3^) IP do roteador (precisa estar conectado a rede^)
echo   4^) Gerar wordlist direcionada a TP-Link
echo   5^) Gerar relatorio (.md + .html^)
echo   6^) Abrir painel web no navegador
echo   7^) Recon nativo via netsh (sem Python^)
echo   0^) Sair
echo.
set "op="
set /p "op=Escolha: "

if "%op%"=="1" ( echo. & %PY% wifi_recon.py & echo. & pause & goto menu )
if "%op%"=="2" ( echo. & %PY% wifi_recon.py --json dados.json --csv dados.csv & echo. & pause & goto menu )
if "%op%"=="3" ( echo. & ipconfig ^| findstr /i "Gateway" & echo. & arp -a & echo. & pause & goto menu )
if "%op%"=="4" ( echo. & %PY% gerar_wordlist_tplink.py -o tplink.txt --datas & echo. & pause & goto menu )
if "%op%"=="5" goto relatorio
if "%op%"=="6" ( echo Abra http://127.0.0.1:8000 no navegador. Ctrl+C encerra o servidor. & echo. & %PY% webui.py & pause & goto menu )
if "%op%"=="7" ( echo. & netsh wlan show networks mode=bssid & echo. & pause & goto menu )
if "%op%"=="0" ( exit /b )
goto menu

:relatorio
cls
echo === Gerar relatorio ===
echo (campos em branco entram como "preencher" no relatorio^)
echo.
set "autor="  & set /p "autor=Autor(es): "
set "metodo=" & set /p "metodo=Metodo (wps / wps-bf / pmkid / handshake): "
set "senha="  & set /p "senha=Senha recuperada: "
set "pin="    & set /p "pin=PIN do WPS (ou Enter): "
set "ip="     & set /p "ip=IP do roteador (ou Enter): "
set "args="
if exist dados.json set "args=--json dados.json --target TP-Link"
%PY% gerar_relatorio.py %args% --autor "%autor%" --metodo "%metodo%" --senha "%senha%" --wps-pin "%pin%" --ip "%ip%" --saida relatorio.md --html relatorio.html
echo.
echo Pronto. Abra relatorio.html no navegador e use Imprimir ^> Salvar como PDF.
echo.
pause
goto menu
