@echo off
REM ============================================================
REM  Build script pentru RadioChromecast -> EXE (PyInstaller)
REM ============================================================
setlocal

cd /d "%~dp0"

echo [1/5] Activez mediul virtual...
set "VENV_OK=0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)

if "%VENV_OK%"=="0" (
    if exist ".venv" (
        echo    .venv este defect - Python lipseste. Il recreez...
        rmdir /s /q ".venv"
    ) else (
        echo    .venv nu exista. Il creez...
    )

    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo    EROARE: nu am putut crea .venv. Instaleaza Python 3.
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [2/5] Verific PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo    PyInstaller lipseste. Il instalez din requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo    EROARE: instalarea dependintelor a esuat.
        exit /b 1
    )
)

echo [3/5] Curat build-urile anterioare...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"

echo [4/5] Compilez aplicatia folosind RadioChromecast.spec...
python -m PyInstaller --noconfirm --clean RadioChromecast.spec
if errorlevel 1 (
    echo    EROARE: compilarea a esuat.
    exit /b 1
)

echo [5/5] Copiez stations.json langa executabil...
if not exist "stations.json" (
    echo    EROARE: stations.json lipseste din radacina proiectului.
    exit /b 1
)
copy /Y "stations.json" "dist\stations.json" >nul
if errorlevel 1 (
    echo    EROARE: nu am putut copia stations.json in dist.
    exit /b 1
)

echo.
echo ============================================================
echo  GATA! Executabilul se afla in:  dist\RadioChromecast.exe
echo ============================================================
endlocal
