@echo off
title HACKALEM AI - Order Management
echo Устанавливаем зависимости...
python -m pip install -r requirements.txt

echo.
echo Запускаем сервер...
echo Приложение будет доступно по адресу: http://127.0.0.1:8000
echo.

start http://127.0.0.1:8000
python -m uvicorn main:app --reload
