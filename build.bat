@echo off
REM ============================================================
REM  Build script pentru RadioChromecast -> EXE (PyInstaller)
REM ============================================================
setlocal

cd /d "%~dp0"

echo [1/4] Activez mediul virtual...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo    AVERTISMENT: .venv nu a fost gasit. Folosesc Python-ul de sistem.
)

echo [2/4] Verific PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo    PyInstaller lipseste. Il instalez din requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo    EROARE: instalarea dependintelor a esuat.
        exit /b 1
    )
)

echo [3/4] Curat build-urile anterioare...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"

echo [4/4] Compilez aplicatia folosind RadioChromecast.spec...
python -m PyInstaller --noconfirm --clean RadioChromecast.spec
if errorlevel 1 (
    echo    EROARE: compilarea a esuat.
    exit /b 1
)

echo.
echo ============================================================
echo  GATA! Executabilul se afla in:  dist\RadioChromecast.exe
echo ============================================================
endlocal
