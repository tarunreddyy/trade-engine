@echo off
echo ====================================
echo  TradeEngine - Build Wheel and SDist
echo ====================================

cd /d "%~dp0.."

echo Cleaning previous package artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"

echo Installing build dependencies...
python -m pip install --upgrade pip
pip install ".[build]"

echo Building package...
python -m build

echo.
if exist dist (
    echo Package build successful. Artifacts are in dist\
) else (
    echo Package build failed. Check the output above for errors.
)

pause
