#!/bin/bash
# Setup script for Google Colab / Kaggle
# Jalankan: !bash setup_colab.sh

set -e

echo "=== Rust Backtest Engine — Colab Setup ==="

# Install Rust if not present
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Install Python package
echo "Installing Python package..."
pip install -e ./python

echo ""
echo "Setup complete! Gunakan:"
echo "  from rust_backtest import run"
