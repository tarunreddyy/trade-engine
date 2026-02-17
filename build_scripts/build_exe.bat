@echo off
echo ====================================
echo  TradeEngine - Build Windows EXE
echo ====================================

cd /d "%~dp0.."

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Installing build dependencies...
python -m pip install --upgrade pip
pip install ".[build,groww]"

echo Building executable...
pyinstaller --clean trade_engine.spec

echo.
if exist dist\trade-engine.exe (
    echo Build successful! Executable: dist\trade-engine.exe
) else (
    echo Build failed. Check the output above for errors.
)

pause
