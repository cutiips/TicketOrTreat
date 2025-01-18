import argparse
import datetime
import hmac
import os

import jsonschema
import requests
import random
import string
import json

from dotenv import load_dotenv

def generate_random_string(length=12):
    """
    Génère une chaîne aléatoire pour le champ 'number'.
    """
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

def generate_random_email(first_name, last_name):
    """
    Génère une adresse e-mail aléatoire pour le 'buyer'.
    """
    domains = ['example.com', 'email.com', 'test.org']
    domain = random.choice(domains)
    return f"{first_name.lower()}.{last_name.lower()}@{domain}"

def make_header(body, secret):
    """
    Crée les en-têtes nécessaires pour signer la requête.
    """
    unix_timestamp = str(int(datetime.datetime.now().timestamp()))
    body_to_sign = f'{unix_timestamp}.{body}'.encode()
    digest = hmac.new(secret.encode(), body_to_sign, "sha256").hexdigest()
    headers = {
        'Petzi-Signature': f't={unix_timestamp},v1={digest}',
        'Petzi-Version': '2',
        'Content-Type': 'application/json',
        'User-Agent': 'PETZI webhook'
    }
    return headers

def make_post_request(url, data, secret):
    """
    Envoie une requête POST au serveur Flask.
    """
    try:
        response = requests.post(url, data=data.encode('utf-8'), headers=make_header(data, secret))

        if response.status_code == 200:
            print(f"Request successful. Response: {response.text}")
        else:
            print(f"Request failed with status code {response.status_code}. Response: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

def introduce_invalidity(data_dict, invalid_type):
    """
    Introduit des erreurs dans le JSON pour tester la validation.
    """
    if invalid_type == "missing_field":
        # Supprime un champ requis (par exemple, 'number')
        del data_dict["details"]["ticket"]["number"]
    elif invalid_type == "wrong_type":
        # Modifie le type d'un champ (par exemple, 'eventId' devient une chaîne)
        data_dict["details"]["ticket"]["eventId"] = "invalid_string"
    elif invalid_type == "invalid_enum":
        # Donne une valeur non autorisée dans un champ à énumération
        data_dict["details"]["ticket"]["type"] = "invalid_type"
    return data_dict

if __name__ == "__main__":
    load_dotenv()

    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

    # Crée un parser pour les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="HTTP POST Request with JSON Body")
    parser.add_argument("url", type=str, help="URL to send the POST request to")
    parser.add_argument("secret", nargs='?', type=str, help="Secret shared between your server and the simulator",
                        default=WEBHOOK_SECRET)
    parser.add_argument("--invalid_type", type=str,
                        choices=["missing_field", "wrong_type", "invalid_enum"],
                        help="Type of invalidity to introduce", default=None)

    # Parse les arguments
    args = parser.parse_args()

    # random name / last name
    first_names = ('John', 'Andy', 'Joe', 'Bob', 'Bill', 'Tom', 'Jack', 'Denny', 'Kate', 'Emma')
    last_names = ('Johnson', 'Smith', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor')

    random_first_name = random.choice(first_names)
    random_last_name = random.choice(last_names)
    email = generate_random_email(random_first_name, random_last_name)

    # Random category and price
    categories = ["Prélocation", "VIP", "Standard", "Étudiant"]
    random_category = random.choice(categories)

    price_mapping = {
        "VIP": "50.00",
        "Standard": "30.00",
        "Étudiant": "20.00",
        "Prélocation": "25.00"
    }
    amount = price_mapping.get(random_category, "30.00")

    # Random cancellation reason
    cancellation_reasons = [
        "",
        "undef_cancellation",
        "order_mistake",
        "event_cancellation",
        "event_postponed",
        "stolen",
        "test_ticket",
        "selfticket_mistake"
    ]
    random_cancellation_reason = random.choice(cancellation_reasons)

    # Random city for buyer
    cities = ["Lausanne", "Genève", "Neuchâtel", "Jura", "Fribourg"]
    random_city = random.choice(cities)

    city_postcodes = {
        "Lausanne": "1000",
        "Genève": "1200",
        "Neuchâtel": "2000",
        "Jura": "2800",
        "Fribourg": "1700",
    }

    random_postcode = city_postcodes.get(random_city, "Unknown")

    # Random event
    event = ["TECH WITH US", "KPOP RYU", "VALENTINO VIVACE", "TOOLBOX NEUCHÂTEL", "THEODORA"]
    random_event = random.choice(event)

    # Random date with event
    event_dates = {
        "TECH WITH US": "2025-01-01",
        "KPOP RYU": "2025-02-02",
        "VALENTINO VIVACE": "2025-03-03",
        "TOOLBOX NEUCHÂTEL": "2025-04-04",
        "THEODORA": "2025-05-05",
    }
    random_date = event_dates.get(random_event, "Unknown")

    # JSON valide par défaut sous forme de dictionnaire
    data_dict = {
        "event": "ticket_created",
        "details": {
            "ticket": {
                "number": generate_random_string(),
                "type": "online_presale",
                "title": random_event,
                "category": random_category,
                "eventId": 17,
                "event": random_event,
                "cancellationReason": random_cancellation_reason,
                "sessions": [
                    {
                        "name": random_event,
                        "date": random_date,
                        "time": "21:00:00",
                        "doors": "21:00:00",
                        "location": {
                            "name": "Case à Chocs",
                            "street": "Quai Philipe Godet 20",
                            "city": random_city,
                            "postcode": "2000"
                        }
                    }
                ],
                "promoter": "Case à Chocs",
                "price": {
                    "amount": amount,
                    "currency": "CHF"
                }
            },
            "buyer": {
                "role": "customer",
                "firstName": random_first_name,
                "lastName": random_last_name,
                "email": email,
                "postcode": random_postcode
            }
        },
    }

    # Introduire une invalidité si spécifié
    if args.invalid_type:
        data_dict = introduce_invalidity(data_dict, args.invalid_type)

    # Charger le schéma depuis schema.json pour validation
    try:
        with open('schema.json', 'r') as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError:
        print("Le fichier 'schema.json' n'a pas été trouvé.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Erreur lors du chargement du schéma JSON : {e}")
        exit(1)

    # Valider data_dict contre le schéma
    try:
        jsonschema.validate(instance=data_dict, schema=schema)
        print("Le JSON généré est valide selon le schéma.")
    except jsonschema.exceptions.ValidationError as err:
        print("Le JSON généré est invalide :", err.message)
        print("Chemin de l'erreur :", list(err.absolute_path))
        exit(1)

    # Convertit le dictionnaire en JSON formaté
    data = json.dumps(data_dict, indent=4)

    # Envoie la requête POST
    make_post_request(args.url, data, args.secret)