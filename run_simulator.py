import subprocess

# Chemin vers Python dans l'environnement virtuel
python_path = "venv310/Scripts/python.exe"

# Définir les paramètres de la commande
url = "http://localhost:5000/webhook"
secret = "AEeyJhbGciOiJIUzUxMiIsImlzcyI6"

# Nombre de fois à exécuter la commande
num_executions = 50

# Boucle pour exécuter plusieurs fois la commande
for i in range(num_executions):
    print(f"Execution {i + 1}/{num_executions}")
    subprocess.run([python_path, "petzi_simulator.py", url, secret])
