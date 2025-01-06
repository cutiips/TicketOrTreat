import random

from flask import Flask, request, jsonify, render_template
import hmac
import hashlib
import time
import json
from jsonschema import ValidationError
from flask_socketio import SocketIO
from datetime import datetime
from mongodb_handler import save_event, initialize_database
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
    recent_tickets = list(
        collection.find({}, {'_id': 0})
        .sort("purchase_date", -1)
        .limit(10)
    )

    # formater les dates
    for ticket in recent_tickets:
        if 'purchase_date' in ticket and isinstance(ticket['purchase_date'], datetime):
            ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket['purchase_date_str'] = 'N/A'

    total_revenue = sum(float(ticket['details']['ticket']['price']['amount']) for ticket in collection.find())
    total_tickets = collection.count_documents({})

    pipeline = [
        {"$group": {"_id": "$details.ticket.title", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    top_event_data = list(collection.aggregate(pipeline))
    top_event = top_event_data[0]['_id'] if top_event_data else "N/A"

    # Renvoyer les données au template
    return render_template(
        'dashboard/dashboard.html',
        tickets=recent_tickets,
        total_revenue=total_revenue,
        total_tickets=total_tickets,
        top_event=top_event
    )


@app.route('/tickets', methods=['GET'])
def tickets():
    all_tickets = list(
        collection.find({}, {'_id': 0}).sort("purchase_date", -1)
    )
    return render_template('dashboard/tickets.html', tickets=all_tickets)


@app.route('/api/recent-tickets', methods=['GET'])
def recent_tickets():
    offset = int(request.args.get('offset', 0))
    limit = 20  # nbre de résultats à retourner

    tickets = list(
        collection.find({}, {'_id': 0})
        .sort("purchase_date", -1)
        .skip(offset)
        .limit(limit)
    )

    return jsonify(tickets)


@app.route('/api/event-data', methods=['GET'])
def event_data():
    pipeline = [
        {"$group": {"_id": "$details.ticket.title", "total_tickets": {"$sum": 1}}},
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)


@app.route('/event/<event_title>', methods=['GET'])
def event_dashboard(event_title):
    pipeline = [
        {"$match": {"details.ticket.title": event_title}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$purchase_date"}},
            "total_tickets": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    sales_data = list(collection.aggregate(pipeline))

    labels = [data["_id"] for data in sales_data]
    values = [data["total_tickets"] for data in sales_data]

    event_info = collection.find_one({"details.ticket.title": event_title}, {"_id": 0})

    if event_info:
        event_date = event_info['details']['ticket']['sessions'][0]['date']
        event_location = event_info['details']['ticket']['sessions'][0]['location']['name']
    else:
        event_date = "N/A"
        event_location = "N/A"

    raw_tickets = list(collection.find({"details.ticket.title": event_title}, {"_id": 0}))

    tickets = []
    for ticket in raw_tickets:
        if 'purchase_date' in ticket:
            if isinstance(ticket['purchase_date'], datetime):
                ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                ticket['purchase_date_str'] = ticket['purchase_date']
        else:
            ticket['purchase_date_str'] = 'N/A'
        tickets.append(ticket)

    pipeline = [
        {"$match": {"details.ticket.title": event_title}},
        {"$group": {"_id": "$details.ticket.type", "count": {"$sum": 1}}}
    ]
    ticket_type_data = list(collection.aggregate(pipeline))
    ticket_type_labels = [data['_id'] for data in ticket_type_data]
    ticket_type_values = [data['count'] for data in ticket_type_data]

    return render_template(
        'dashboard/event_dashboard.html',
        event_title=event_title,
        event_date=event_date,
        event_location=event_location,
        tickets=tickets,
        sales_data={"labels": labels, "values": values},
        ticket_type_data={"labels": ticket_type_labels, "values": ticket_type_values}
    )



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
        # data['purchase_date'] = datetime.utcnow() # now
        data['purchase_date'] = datetime(2025, 2, random.randint(1, 3), random.randint(0, 23), random.randint(0, 59), random.randint(0, 59)) # random date
        purchase_date_str = data['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')

        save_event(data)

        # emit l'événement avec la date formatée
        socketio.emit('new_ticket', {
            'details': data['details'],
            'purchase_date': purchase_date_str
        })

        response = handle_webhook(data)
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
    initialize_database()
    # Werkzeug est utilisé par défaut pour le serveur de développement Flask - seulement en développement
    # socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)

    # Alternative : eventlet
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
