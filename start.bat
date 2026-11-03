@echo off
chcp 65001 >nul
title Pokémon-TCG-Wächter (Satella)

echo ========================================================
echo   Starting Pokémon-TCG-Wächter (Satella)...
echo ========================================================

:: Python-Pfad ermitteln
set PYTHON_EXE=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PYTHON_EXE=py"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [FEHLER] Kein Python gefunden! Bitte installiere Python von python.org.
    pause
    exit /b 1
)

echo Verwende Python: %PYTHON_EXE%
echo Starte Bot... Drücke Strg+C zum Beenden.
echo --------------------------------------------------------

"%PYTHON_EXE%" bot.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [HINWEIS] Bot wurde mit Fehlercode %ERRORLEVEL% beendet.
    pause
)
