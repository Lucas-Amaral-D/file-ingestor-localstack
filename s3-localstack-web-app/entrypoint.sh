#!/bin/bash
set -e

echo "Iniciando Flask sem esperar LocalStack..."
exec python app.py

