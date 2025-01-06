import argparse
import datetime
import hmac
import os

import requests
import random
import string
import json

from dotenv import load_dotenv


def generate_random_string(length=12):
    """
    Génère une chaîne aléatoire pour le champ 'number'.
    """
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))


def make_header(body, secret):
    """
    Crée les en-têtes nécessaires pour signer la requête.
    """
    unix_timestamp = str(datetime.datetime.timestamp(datetime.datetime.now())).split('.')[0]
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

    # JSON valide par défaut sous forme de dictionnaire
    data_dict = {
        "event": "ticket_created",
        "details": {
            "ticket": {
                "number": "XXXX2941J6SABA",
                "type": "online_sale",
                "title": "Event Demo CAC",
                "category": "Prélocation",
                "eventId": 54694,
                "event": "Event Demo",
                "cancellationReason": "",
                "generatedAt": "2025-07-04T10:21:21.925529+00:00",
                "sessions": [
                    {
                        "name": "Event Demo CAC",
                        "date": "2025-02-01",
                        "time": "21:00:00",
                        "doors": "21:00:00",
                        "location": {
                            "name": "Case à Chocs",
                            "street": "Quai Philipe Godet 20",
                            "city": "Neuchatel",
                            "postcode": "2000"
                        }
                    }
                ],
                "promoter": "Case à Chocs",
                "price": {
                    "amount": "30.00",
                    "currency": "CHF"
                }
            },
            "buyer": {
                "role": "customer",
                "firstName": random_first_name,
                "lastName": random_last_name,
                "postcode": "1234"
            }
        },
    }

    # Génère un numéro aléatoire pour 'number'
    data_dict["details"]["ticket"]["number"] = generate_random_string()

    # Introduire une invalidité si spécifié
    if args.invalid_type:
        data_dict = introduce_invalidity(data_dict, args.invalid_type)

    # Convertit le dictionnaire en JSON formaté
    data = json.dumps(data_dict, indent=4)

    # Envoie la requête POST
    make_post_request(args.url, data, args.secret)
