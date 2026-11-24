# Dalil Legal

Plateforme de consultation juridique orientée vers le droit marocain. Le projet comprend un frontend en HTML/CSS/JavaScript, une API FastAPI, une base SQLite, un corpus de modèles de documents et des fonctions IA utilisant une API compatible avec Groq.

## Prérequis

- Windows 10/11
- Python 3.10 ou plus récent
- Une clé API Groq pour les fonctions de génération et de consultation par IA

## Installation

Depuis la racine du projet, ouvrez PowerShell :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Si PowerShell empêche l’activation de l’environnement virtuel, vous pouvez appeler directement ses exécutables, par exemple :

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Configuration

Le backend charge les fichiers `.env` placés dans `backend/` ou à la racine du projet. Créez ou modifiez `backend/.env` avec vos propres valeurs :

```dotenv
GROQ_API_KEY=votre-cle-api
GROQ_MODEL=llama-3.3-70b-versatile
JWT_SECRET=remplacez-par-une-longue-valeur-aleatoire
```

`LLM_API_KEY`, `LLM_MODEL` et `LLM_BASE_URL` sont également pris en charge pour configurer directement le fournisseur compatible OpenAI. Ne partagez pas votre fichier `.env` et ne publiez pas de clé API. En production, définissez impérativement un `JWT_SECRET` unique et protégez les clés utilisées par le projet.

**Sécurité :** le code contient actuellement une valeur de repli pour la clé IA. Avant toute publication ou mise en production, supprimez cette valeur par défaut et toute clé réelle des fichiers versionnés, puis révoquez/renouvelez les clés qui auraient été exposées. La clé doit être fournie uniquement par la configuration d’environnement.

## Lancer le backend et le frontend

Depuis la racine du projet, activez l’environnement virtuel, placez-vous dans `backend/`, puis démarrez le serveur :

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Le backend sert également les fichiers du dossier `frontend/`. Il n’est donc pas nécessaire de lancer un second serveur frontend pour le développement local.

- Application : <http://127.0.0.1:8000/>
- Documentation interactive de l’API : <http://127.0.0.1:8000/docs>
- Vérification de l’état du serveur : <http://127.0.0.1:8000/api/health>

Laissez cette fenêtre de terminal ouverte pendant l’utilisation. Pour arrêter le serveur, appuyez sur `Ctrl+C`.

Si l’environnement virtuel est déjà activé, la commande équivalente depuis `backend/` est :

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Le chemin du frontend étant résolu depuis l’emplacement du code, il reste servi à la racine du site.

## Frontend seul

Les pages sont des fichiers statiques consultables dans `frontend/`, mais le parcours recommandé est de les ouvrir via `http://127.0.0.1:8000/`. Certaines pages utilisent des chemins d’API relatifs, notamment l’inscription et la connexion : ouvrir les fichiers directement avec `file://` ou les servir sur un autre port ne garantit pas le fonctionnement de ces appels.

## Données et génération de documents

- La base SQLite est `backend/dalillegal.db`. Les tables nécessaires et les articles de base sont initialisés au démarrage.
- Les modèles PDF et DOCX se trouvent dans `backend/models/`.
- Les documents créés sont enregistrés dans `backend/generated_docs/`.
- `backend/index_all_pdfs.py` est un script d’indexation optionnel. Il recherche des fichiers PDF dans `backend/data/`, dossier qui doit être alimenté avant son utilisation. Le corpus de modèles de `backend/models/` n’est pas automatiquement indexé par ce script.

## Structure principale

```text
backend/
  main.py                 API FastAPI, authentification et service des pages frontend
  models_service.py       Recherche de modèles et génération de documents
  rag_service.py          Recherche juridique et base SQLite/FTS5
  requirements.txt        Dépendances Python
  models/                 Modèles PDF et DOCX
  generated_docs/         Documents générés
frontend/
  *.html                  Pages de l’application
  shared.js               Fonctions frontend partagées
  style.css               Styles
```

## Dépannage

- **`py` ou Python introuvable** : installez Python et vérifiez que le lanceur Python est disponible dans le terminal.
- **Dépendances manquantes** : activez `.venv`, puis relancez `pip install -r backend\requirements.txt`.
- **Port 8000 déjà utilisé** : choisissez un autre port dans la commande Uvicorn, puis ouvrez le site sur ce port.
- **Fonctions IA indisponibles** : vérifiez la valeur de `GROQ_API_KEY` ou `LLM_API_KEY` dans le fichier `.env`, puis redémarrez le serveur.
