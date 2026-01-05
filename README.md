# 🚗⚡ Planificateur de Voyage en Véhicule Électrique

Application web Flask pour planifier des trajets en véhicule électrique avec calcul automatique des arrêts de recharge nécessaires.

## 📋 Description du Projet

Cette application implémente une architecture orientée services (SOA) complète avec :

- **Service GraphQL** : Récupération de la liste des véhicules électriques via Chargetrip API
- **Service REST** : API pour les bornes de recharge (Open Data Réseaux Énergies)
- **Service SOAP** : Calcul du temps de trajet avec rechargements
- **Cartographie** : Visualisation interactive avec Folium
- **API REST personnalisée** : Export JSON pour clients tiers

## 🎯 Fonctionnalités

✅ Sélection du véhicule électrique dans une liste complète  
✅ Saisie du trajet (ville de départ → ville d'arrivée)  
✅ Calcul intelligent du nombre d'arrêts de recharge nécessaires  
✅ Localisation automatique des bornes de recharge sur le trajet  
✅ Affichage d'une carte interactive avec l'itinéraire complet  
✅ Calcul du temps total (conduite + rechargement)  
✅ API REST pour intégration tierce  

## 🛠️ Installation

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Connexion Internet

### Étapes d'installation

1. **Créer le dossier du projet**
```bash
mkdir ev-trip-planner
cd ev-trip-planner
```

2. **Créer la structure des dossiers**
```bash
mkdir templates
mkdir static
```

3. **Copier les fichiers**
- `app.py` → Racine du projet
- `soap_service.py` → Racine du projet
- `requirements.txt` → Racine du projet
- `index.html` → Dans le dossier `templates/`
- `style.css` → Dans le dossier `static/`
- `README.md` → Racine du projet

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

## 🚀 Lancement de l'application

### Démarrage simple
```bash
python app.py
```

L'application sera accessible sur : **http://localhost:5000**

### Test du service SOAP
Le service SOAP est intégré dans `app.py`. Pour tester séparément :
```bash
python soap_service.py
```

WSDL disponible sur : **http://localhost:5000/soap/wsdl**

## 📁 Structure du Projet

```
ev-trip-planner/
│
├── app.py                 # Application Flask principale
├── soap_service.py        # Service SOAP pour calcul temps
├── requirements.txt       # Dépendances Python
├── README.md             # Ce fichier
│
├── templates/
│   └── index.html        # Interface utilisateur
│
└── static/
    └── style.css         # Styles CSS
```

## 🔌 API Endpoints

### REST API

#### 1. Liste des véhicules
```
GET /api/vehicles
```
Retourne la liste complète des véhicules électriques disponibles.

**Réponse :**
```json
{
  "success": true,
  "count": 50,
  "vehicles": [
    {
      "id": "1",
      "make": "Tesla",
      "model": "Model 3",
      "version": "Long Range",
      "range": 580,
      "battery": 75
    }
  ]
}
```

#### 2. Planifier un trajet
```
POST /api/plan
Content-Type: application/json

{
  "vehicle_id": "1",
  "start_city": "Paris",
  "end_city": "Lyon"
}
```

**Réponse :**
```json
{
  "success": true,
  "vehicle": {...},
  "start_city": "Paris",
  "end_city": "Lyon",
  "trip": {
    "total_distance": 465.2,
    "num_stops": 0,
    "stops": [],
    "driving_time": 5.17,
    "charging_time": 0,
    "total_time": 5.17
  }
}
```

#### 3. Bornes de recharge
```
GET /api/charging-stations?lat=48.8566&lon=2.3522&radius=50
```

Retourne les bornes de recharge dans un rayon donné (en km).

### Service SOAP

**Endpoint :** `http://localhost:5000/soap`  
**WSDL :** `http://localhost:5000/soap/wsdl`

**Méthode : `calculate_trip_time`**

Paramètres :
- `distance` (float) : Distance en km
- `vehicle_range` (float) : Autonomie en km
- `charging_time_minutes` (int) : Temps de recharge en minutes

Retourne un JSON avec :
- Distance totale
- Nombre d'arrêts
- Temps de conduite
- Temps de recharge
- Temps total

## 🎨 Utilisation de l'Interface Web

1. **Ouvrir** http://localhost:5000 dans votre navigateur
2. **Sélectionner** un véhicule électrique dans la liste
3. **Saisir** la ville de départ (ex: Paris)
4. **Saisir** la ville d'arrivée (ex: Lyon)
5. **Cliquer** sur "Calculer l'itinéraire"
6. **Visualiser** les résultats :
   - Résumé du trajet (distance, temps, arrêts)
   - Liste détaillée des arrêts de recharge
   - Carte interactive avec l'itinéraire complet

## 🔧 Configuration

### Clés API

Les clés API Chargetrip sont déjà configurées dans `app.py` :

```python
CHARGETRIP_CLIENT_ID = "6929b792ae1ea6e7efa99892"
CHARGETRIP_APP_ID = "6929b792ae1ea6e7efa99894"
```

### Services Externes Utilisés

- **Chargetrip GraphQL API** : Base de données de véhicules électriques
- **Open Data Réseaux Énergies** : Bornes de recharge IRVE en France
- **Nominatim** : Géocodage des villes
- **Folium** : Génération de cartes interactives

## 🧪 Tests

### Tester l'API REST
```bash
# Liste des véhicules
curl http://localhost:5000/api/vehicles

# Planifier un trajet
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"1","start_city":"Paris","end_city":"Lyon"}'

# Bornes de recharge
curl "http://localhost:5000/api/charging-stations?lat=48.8566&lon=2.3522&radius=50"
```

### Tester le service SOAP

Utilisez un client SOAP (SoapUI, Postman, etc.) avec le WSDL :
```
http://localhost:5000/soap/wsdl
```

Exemple de requête SOAP :
```xml

   
   
      
         500
         400
         30
      
   

```

## 📦 Déploiement Cloud

### Heroku

1. Créer un fichier `Procfile` :
```
web: python app.py
```

2. Créer un fichier `runtime.txt` :
```
python-3.11.0
```

3. Déployer :
```bash
heroku create mon-app-ev
git push heroku main
```

### Azure / Firebase

Suivre la documentation respective pour le déploiement d'applications Flask.

## 🐛 Dépannage

### Problème : Les véhicules ne se chargent pas
- Vérifier la connexion Internet
- Vérifier les clés API Chargetrip
- Regarder les logs dans la console

### Problème : Erreur de géocodage
- Vérifier l'orthographe des villes
- Ajouter ", France" après le nom de ville si nécessaire
- Certaines petites communes peuvent ne pas être reconnues

### Problème : Pas de bornes trouvées
- Augmenter le rayon de recherche dans le code
- Vérifier la disponibilité de l'API IRVE Open Data

## 📚 Technologies Utilisées

- **Backend** : Flask (Python)
- **Frontend** : HTML5, CSS3, JavaScript vanilla
- **APIs** : GraphQL, REST, SOAP
- **Cartographie** : Folium, OpenStreetMap
- **Services** : Chargetrip, Open Data Réseaux Énergies, Nominatim

## 👨‍💻 Auteur

Projet réalisé dans le cadre du cours INFO802 - Architectures Orientées Service

## 📄 Licence

Ce projet est à usage éducatif uniquement.

## 🎓 Évaluation

Pour l'évaluation, préparer :

1. ✅ **Démonstration fonctionnelle** de l'application
2. ✅ **Présentation du code** (structure, choix techniques)
3. ✅ **URL Git** du projet
4. ✅ **URL Cloud** de l'application déployée

## 📞 Support

En cas de problème :
1. Vérifier que toutes les dépendances sont installées
2. Consulter les logs d'erreur dans le terminal
3. Vérifier la connexion Internet pour les APIs externes

---

**Bon voyage électrique ! ⚡🚗**