#!/bin/bash
set -e

echo "===================================="
echo " TradeEngine - Build Wheel and SDist"
echo "===================================="

cd "$(dirname "$0")/.."

echo "Cleaning previous package artifacts..."
rm -rf build dist ./*.egg-info

echo "Installing build dependencies..."
python -m pip install --upgrade pip
pip install ".[build]"

echo "Building package..."
python -m build

echo ""
if [ -d dist ]; then
    echo "Package build successful. Artifacts are in dist/"
else
    echo "Package build failed. Check the output above for errors."
fi
