import random
import jsonschema
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

# Charger le schéma de validation JSON
with open("schemas/schema.json", "r") as schema_file:
    webhook_schema = json.load(schema_file)


@app.route('/', methods=['GET'])
def dashboard():
    """
    Page d'accueil : Dashboard principal
    """
    # Derniers billets (limite 10)
    recent_tickets = list(
        collection.find({}, {'_id': 0})
        .sort("purchase_date", -1)
        .limit(3)
    )
    # Formatage des dates
    for ticket in recent_tickets:
        if 'purchase_date' in ticket and isinstance(ticket['purchase_date'], datetime):
            ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket['purchase_date_str'] = 'N/A'

    # Statistiques globales
    total_revenue = sum(float(ticket['details']['ticket']['price']['amount']) for ticket in collection.find())
    total_tickets = collection.count_documents({})

    # Événement le plus vendu
    pipeline = [
        {"$group": {"_id": "$details.ticket.title", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    top_event_data = list(collection.aggregate(pipeline))
    top_event = top_event_data[0]['_id'] if top_event_data else "N/A"

    return render_template(
        'dashboard/dashboard.html',
        tickets=recent_tickets,
        total_revenue=total_revenue,
        total_tickets=total_tickets,
        top_event=top_event
    )


@app.route('/tickets', methods=['GET'])
def tickets():
    """
Page listant tous les billets vendus
"""
    # Récupération des paramètres
    selected_city = request.args.get('city', '')
    selected_category = request.args.get('category', '')

    # Construire la query
    query = {}
    if selected_city:
        query['details.ticket.sessions.0.location.city'] = selected_city
    if selected_category:
        query['details.ticket.category'] = selected_category

    # Utiliser la query
    all_tickets = list(
        collection.find(query, {'_id': 0}).sort("purchase_date", -1)
    )

    # Format des dates
    for ticket in all_tickets:
        if 'purchase_date' in ticket and isinstance(ticket['purchase_date'], datetime):
            ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket['purchase_date_str'] = 'N/A'

    # Obtenir la liste distincte des villes et catégories
    distinct_cities = sorted({t['details']['ticket']['sessions'][0]['location']['city']
                              for t in collection.find({}, {'_id': 0})})
    distinct_categories = sorted({t['details']['ticket']['category']
                                  for t in collection.find({}, {'_id': 0})})

    return render_template(
        'dashboard/tickets.html',
        tickets=all_tickets,
        distinct_cities=distinct_cities,
        distinct_categories=distinct_categories,
        selected_city=selected_city,
        selected_category=selected_category
    )

@app.route('/api/recent-tickets', methods=['GET'])
def recent_tickets():
    """
    Endpoint pour récupérer un lot de tickets récents
    (exemple : scrolling infini)
    """
    offset = int(request.args.get('offset', 0))
    limit = 20

    tickets = list(
        collection.find({}, {'_id': 0})
        .sort("purchase_date", -1)
        .skip(offset)
        .limit(limit)
    )
    # Formatage dates
    for ticket in tickets:
        if 'purchase_date' in ticket and isinstance(ticket['purchase_date'], datetime):
            ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket['purchase_date_str'] = 'N/A'
    return jsonify(tickets)


@app.route('/api/event-data', methods=['GET'])
def event_data():
    """
    Endpoint pour construire le graphique des ventes par événement
    """
    pipeline = [
        {"$group": {"_id": "$details.ticket.title", "total_tickets": {"$sum": 1}}}
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)


@app.route('/event/<event_title>', methods=['GET'])
def event_dashboard(event_title):
    """
    Page de détail d’un événement
    """
    capacity = 750


    # Ventes par jour
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

    # Infos sur l'événement
    event_info = collection.find_one({"details.ticket.title": event_title}, {"_id": 0})
    if event_info:
        event_date = event_info['details']['ticket']['sessions'][0]['date']
        event_location = event_info['details']['ticket']['sessions'][0]['location']['name']
    else:
        event_date = "N/A"
        event_location = "N/A"

    # Récupération de tous les billets pour l'événement
    raw_tickets = list(collection.find({"details.ticket.title": event_title}, {"_id": 0}))

    # Billets vendus et places restantes
    sold = len(raw_tickets)
    remaining = capacity - sold

    displayed_tickets = sorted(raw_tickets, key=lambda t: t['purchase_date'], reverse=True)[:5]

    total_event_revenue = sum(float(t['details']['ticket']['price']['amount']) for t in raw_tickets)

    # Comptage par région (ex. city)
    from collections import Counter
    city_counts = Counter(t['details']['ticket']['sessions'][0]['location']['city'] for t in raw_tickets)
    region_labels = list(city_counts.keys())
    region_values = list(city_counts.values())

    tickets = []
    for ticket in raw_tickets:
        if 'purchase_date' in ticket and isinstance(ticket['purchase_date'], datetime):
            ticket['purchase_date_str'] = ticket['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket['purchase_date_str'] = 'N/A'
        tickets.append(ticket)

    # Graphique par type de billet
    pipeline = [
        {"$match": {"details.ticket.title": event_title}},
        {"$group": {"_id": "$details.ticket.type", "count": {"$sum": 1}}}
    ]
    ticket_type_data = list(collection.aggregate(pipeline))
    ticket_type_labels = [d['_id'] for d in ticket_type_data]
    ticket_type_values = [d['count'] for d in ticket_type_data]

    return render_template(
        'dashboard/event_dashboard.html',
        event_title=event_title,
        event_date=event_date,
        event_location=event_location,
        tickets=displayed_tickets,
        sales_data={"labels": labels, "values": values},
        ticket_type_data={"labels": ticket_type_labels, "values": ticket_type_values},
        total_event_revenue = total_event_revenue,
        region_data = {"labels": region_labels, "values": region_values},
        capacity=capacity,
        sold=sold,
        remaining=remaining
    )

@app.route('/event/<event_title>/all', methods=['GET'])
def event_all_tickets(event_title):
    # Récupérer tous les billets
    raw_tickets = list(collection.find({"details.ticket.title": event_title}, {'_id': 0}))

    # Filtre ville
    selected_city = request.args.get('city', '')
    if selected_city:
        raw_tickets = [t for t in raw_tickets if t['details']['ticket']['sessions'][0]['location']['city'] == selected_city]

    # Filtre type
    selected_type = request.args.get('type', '')
    if selected_type:
        raw_tickets = [t for t in raw_tickets if t['details']['ticket']['type'] == selected_type]

    # Tri
    selected_sort = request.args.get('sort', 'date_desc')
    if selected_sort == 'date_asc':
        raw_tickets.sort(key=lambda x: x['purchase_date'])
    elif selected_sort == 'date_desc':
        raw_tickets.sort(key=lambda x: x['purchase_date'], reverse=True)
    elif selected_sort == 'price_asc':
        raw_tickets.sort(key=lambda x: float(x['details']['ticket']['price']['amount']))
    elif selected_sort == 'price_desc':
        raw_tickets.sort(key=lambda x: float(x['details']['ticket']['price']['amount']), reverse=True)

    # Distinct cities/types (pour remplir le <select>)
    distinct_cities = sorted({t['details']['ticket']['sessions'][0]['location']['city'] for t in collection.find({"details.ticket.title": event_title})})
    distinct_types = sorted({t['details']['ticket']['type'] for t in collection.find({"details.ticket.title": event_title})})

    # Format date
    for t in raw_tickets:
        if 'purchase_date' in t:
            t['purchase_date_str'] = t['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')

    return render_template(
        'dashboard/event_all_tickets.html',
        event_title=event_title,
        tickets=raw_tickets,
        distinct_cities=distinct_cities,
        distinct_types=distinct_types,
        selected_city=selected_city,
        selected_type=selected_type,
        selected_sort=selected_sort
    )



@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Réception du webhook Petzi.
    Vérification de la signature, validation du JSON,
    sauvegarde dans MongoDB, et notification Socket.io.
    """
    # Étape 1 : Vérifier la signature
    signature = request.headers.get("Petzi-Signature")
    if not signature:
        return jsonify({"error": "Signature header missing"}), 400

    try:
        signature_parts = dict(item.split('=') for item in signature.split(','))
        timestamp = int(signature_parts["t"])
        received_signature = signature_parts["v1"]
    except Exception:
        return jsonify({"error": "Invalid signature format"}), 400

    if abs(time.time() - timestamp) > 30:
        return jsonify({"error": "Request is too old"}), 400

    body = request.get_data(as_text=True)
    body_to_sign = f"{timestamp}.{body}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        return jsonify({"error": "Invalid signature"}), 403

    # Étape 2 : Valider et traiter le payload
    try:
        data = request.get_json()

        jsonschema.validate(instance=data, schema=webhook_schema)

        # Pour la démo : on force une date random (2025-02-01 -> 2025-02-03)
        data['purchase_date'] = datetime(
            2025, 2, random.randint(1, 3),
            random.randint(0, 23), random.randint(0, 59),
            random.randint(0, 59))
        purchase_date_str = data['purchase_date'].strftime('%Y-%m-%d %H:%M:%S')

        save_event(data)

        # Émettre l'événement Socket.io avec date formatée
        socketio.emit('new_ticket', {
            'details': data['details'],
            'purchase_date': purchase_date_str
        })

        response = handle_webhook(data)
        return jsonify(response)

    except ValidationError as e:
        return jsonify({
            "error": f"JSON Validation Error: {e.message}",
            "path": list(e.absolute_path)
        }), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    initialize_database()
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
