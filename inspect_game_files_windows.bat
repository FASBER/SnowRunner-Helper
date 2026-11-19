@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo SnowRunner Helper: проверка игровых архивов (только чтение)
echo Можно вставить путь к папке client или к одному .pak/.stg
py stg_inspector.py
pause
