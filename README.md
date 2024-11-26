## 🚀 Partie venv :
1. Créer :
    ```bash
    py -3.10 -m venv venv310 # version 3.10 - 3.13 n'est pas supporté par certaines dépendances
    ```
2. Lancer :
    ```bash
    venv310\Scripts\activate # Windows
    ```
3. Màj de `pip` et `setuptools` :
    ```bash
    python -m pip install --upgrade pip setuptools
    ```
4. Dép :
    ```bash
    pip install -r requirements.txt
    ```

## 💽 Partie persistance
1. Créer créer un fichier `.env` à la racine du projet contenant :
    ```bash
    WEBHOOK_SECRET=VOTRE_SECRET
    ```
_(Remplacez `VOTRE_SECRET` par votre clé secrète, sans guillemets ni backticks.)_

2. Création du conteneur MongoDB avec docker:
    ```bash
    docker run -d --name mongodb-container -p 27017:27017 -v mongodb_data:/data/db mongo:latest
    ```
3. Vérification :
    ```bash
    docker ps
    ```

## ▶️ Lancer l'app
1. lancer le serveur :
    ```bash
    cd .\app\
    ```

    ```bash
    python -m main
    ```
2. Simuler un webhook Petzi :
    ```bash
    python petzi_simulator.py http://localhost:5000/webhook {YOUR_SECRET} 
    ```

---
## 💊 issues :
- Problème d'installation de `socketio`
```bash
error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/
```
- Solution :
    - Se référer à cette solution : https://stackoverflow.com/questions/64261546/how-to-solve-error-microsoft-visual-c-14-0-or-greater-is-required-when-inst