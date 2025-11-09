#!/usr/bin/env bash
set -o errexit

echo "Forcing Python 3.10.14 environment..."
export PYTHON_VERSION=3.10.14

# Устанавливаем правильную версию Python
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - || true
apt-get update -y
apt-get install -y python3.10 python3.10-venv python3.10-distutils

# Активируем 3.10 для виртуального окружения
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

echo "Installing dependencies..."
pip install -r requirements.txt
