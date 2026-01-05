#!/bin/bash

# 1. Installation des dépendances (au cas où le build ne l'a pas fait)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 2. Lancer le serveur SOAP (Port 8001) en arrière-plan (&)
# On redirige les logs vers un fichier pour éviter de bloquer
python soap_service.py > soap.log 2>&1 &

echo "Démarrage du SOAP server... attente de 5s"
sleep 5

# 3. Lancer l'application Flask (Port 8000) au PREMIER PLAN
# C'est ce processus que Azure va écouter.
# Ne mettez PAS de '&' à la fin de cette ligne.
gunicorn --bind=0.0.0.0:8000 --timeout 600 app:app