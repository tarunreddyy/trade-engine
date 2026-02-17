#!/bin/bash
set -e

echo "===================================="
echo " TradeEngine - Build Executable"
echo "===================================="

cd "$(dirname "$0")/.."

echo "Cleaning previous builds..."
rm -rf build dist

echo "Installing build dependencies..."
python -m pip install --upgrade pip
pip install ".[build,groww]"

echo "Building executable..."
pyinstaller --clean trade_engine.spec

echo ""
if [ -f dist/trade-engine ]; then
    echo "Build successful! Executable: dist/trade-engine"
else
    echo "Build failed. Check the output above for errors."
fi
