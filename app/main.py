from flask import Flask, request, jsonify, render_template
import hmac
import hashlib
import time
import json
from jsonschema import ValidationError
from flask_socketio import SocketIO

from mongodb_handler import save_event
from webhook_handler import handle_webhook
from dotenv import load_dotenv
import os
from mongodb_handler import collection


app = Flask(__name__)
socketio = SocketIO(app)

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

with open("schemas/schema.json", "r") as schema_file:
    webhook_schema = json.load(schema_file)


@app.route('/', methods=['GET'])
def dashboard():
    tickets = list(collection.find({}, {'_id': 0}))

    total_revenue = sum(float(ticket['details']['ticket']['price']['amount']) for ticket in tickets)

    return render_template('dashboard.html', tickets=tickets, total_revenue=total_revenue)


@app.route('/webhook', methods=['POST'])
def webhook():
    # Étape 1 : Vérifier la signature
    signature = request.headers.get("Petzi-Signature")
    if not signature:
        return jsonify({"error": "Signature header missing"}), 400

    # Extraire le timestamp et la signature
    try:
        signature_parts = dict(item.split('=') for item in signature.split(','))
        timestamp = int(signature_parts["t"])
        received_signature = signature_parts["v1"]
    except Exception:
        return jsonify({"error": "Invalid signature format"}), 400

    # Vérifier si la requête est récente
    if abs(time.time() - timestamp) > 30:
        return jsonify({"error": "Request is too old"}), 400

    # Calculer la signature attendue
    body = request.get_data(as_text=True)
    body_to_sign = f"{timestamp}.{body}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    # Comparer les signatures
    if not hmac.compare_digest(expected_signature, received_signature):
        return jsonify({"error": "Invalid signature"}), 403

    # Étape 2 : Valider et traiter le payload
    try:
        data = request.get_json()
        save_event(data)
        response = handle_webhook(data)
        socketio.emit('new_ticket', data)

        return jsonify(response)

    except ValidationError as e:
        return jsonify({"error": f"JSON Validation Error: {e.message}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def process_payload(data):
    """
    Traite les données du webhook.
    """
    event = data.get("event")
    details = data.get("details")
    print(f"Event: {event}, Details: {json.dumps(details, indent=2)}")


if __name__ == '__main__':
    # Werkzeug est utilisé par défaut pour le serveur de développement Flask - seulement en développement
    # socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)

    # Alternative : eventlet
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
