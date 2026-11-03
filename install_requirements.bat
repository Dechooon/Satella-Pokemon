@echo off
chcp 65001 >nul
title Pokémon-TCG-Wächter - Installation

set PYTHON_EXE=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Installiere Abhängigkeiten...
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo.
echo Fertig! Drücke eine Taste zum Schließen.
pause
