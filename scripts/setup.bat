@echo off
REM GitHub Stars Manager - Windows Setup Script
echo Setting up GitHub Stars Manager...

REM Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    exit /b 1
)

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.9+
    exit /b 1
)

echo Installing frontend dependencies...
cd github-stars-manager-frontend
call pnpm install --prefer-offline
cd ..

echo Installing backend dependencies...
cd backend
call pnpm install --prefer-offline
cd ..

echo Installing Python dependencies...
cd services
pip install -r requirements.txt
cd ..

echo Setup complete!
pause
