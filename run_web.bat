@echo off
REM Export model artifacts to JSON, then build and preview the React frontend.
cd /d %~dp0
call .venv\Scripts\activate.bat
python scripts\export_web.py || goto :err
cd web
if not exist node_modules call npm install || goto :err
call npm run build || goto :err
echo.
echo Open http://localhost:4173  (Ctrl+C to stop)
call npm run preview -- --port 4173
goto :eof
:err
echo Something failed above.
pause
