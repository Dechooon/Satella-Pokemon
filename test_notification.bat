@echo off
chcp 65001 >nul
title Pokémon-TCG-Wächter - Test Benachrichtigung

set PYTHON_EXE=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Sende Testnachricht an Telegram, Discord und ntfy...
"%PYTHON_EXE%" bot.py --test

echo.
pause
