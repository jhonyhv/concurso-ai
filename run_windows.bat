@echo off
setlocal
cd /d "%~dp0"
title ConcursoAI

echo ========================================
echo        Iniciando ConcursoAI
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    ) else (
        echo ERRO: Python nao foi encontrado.
        echo Instale o Python e marque a opcao "Add Python to PATH".
        pause
        exit /b 1
    )
)

echo Python encontrado: %PYTHON_CMD%
echo Verificando dependencias...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO: Nao foi possivel instalar ou verificar as dependencias.
    pause
    exit /b 1
)

echo.
echo Abrindo o ConcursoAI no navegador...
%PYTHON_CMD% -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo ERRO: O aplicativo nao conseguiu iniciar.
    echo Tente executar manualmente: %PYTHON_CMD% -m streamlit run app.py
)

pause
endlocal
