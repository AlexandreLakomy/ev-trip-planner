#!/bin/bash

echo "========================================="
echo "  EV Trip Planner – Démarrage des services"
echo "========================================="

# -------------------------------
# 1. Installer les dépendances
# -------------------------------
echo "[1/3] Installation des dépendances Python..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# -------------------------------
# 2. Lancer le service SOAP (5001)
# -------------------------------
echo "[2/3] Démarrage du service SOAP (port 5001)..."

# On lance SOAP en arrière-plan
# Les logs sont redirigés vers soap.log
python soap_service.py > soap.log 2>&1 &

SOAP_PID=$!
echo "SOAP lancé (PID=$SOAP_PID)"

# Attendre que SOAP soit prêt
sleep 5

# -------------------------------
# 3. Lancer l’API REST Flask (5000)
# -------------------------------
echo "[3/3] Démarrage de l’API REST Flask (port 5000)..."

# ⚠️ Ce process DOIT rester au premier plan
# C’est lui que le Cloud (Azure) surveille
gunicorn \
  --bind 0.0.0.0:5000 \
  --timeout 600 \
  --workers 1 \
  app:app
