@echo off
REM ============================================================
REM  Repara permisiunile firewall pentru RadioChromecast.exe
REM  RULEAZA CA ADMINISTRATOR (click dreapta -> Run as administrator)
REM ============================================================
setlocal

REM Verific drepturi de administrator
net session >nul 2>&1
if errorlevel 1 (
    echo EROARE: Acest script trebuie rulat ca ADMINISTRATOR.
    echo Click dreapta pe fisier -^> "Run as administrator".
    pause
    exit /b 1
)

set "EXEPATH=%~dp0dist\RadioChromecast.exe"
if not exist "%EXEPATH%" set "EXEPATH=%~dp0RadioChromecast.exe"

echo Sterg regulile vechi (inclusiv cele de BLOCK) pentru RadioChromecast...
netsh advfirewall firewall delete rule name="RadioChromecast" >nul 2>&1
netsh advfirewall firewall delete rule program="%EXEPATH%" >nul 2>&1

echo Adaug reguli de ALLOW (intrare) pentru executabil...
netsh advfirewall firewall add rule name="RadioChromecast" dir=in action=allow program="%EXEPATH%" enable=yes profile=private,domain
netsh advfirewall firewall add rule name="RadioChromecast" dir=in action=allow protocol=TCP localport=8090 enable=yes profile=private,domain

echo.
echo ============================================================
echo  GATA! Reguli firewall actualizate pentru:
echo  %EXEPATH%
echo ============================================================
pause
endlocal
