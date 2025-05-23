from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random
import string
import time

app = Flask(__name__, static_folder='static', static_url_path='')

# Configuração avançada de CORS
CORS(app, resources={
    r"/gerar-pix": {
        "origins": "*",
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/verificar-pagamento/*": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    },
    r"/.*": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    }
})

# Simulação de banco de dados em memória
payments_db = {}
qr_codes_db = {}

def generate_payment_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def mercado_pago_simulator(amount, email, name, cpf):
    time.sleep(1)
    
    payment_id = generate_payment_id()
    expiration = datetime.now() + timedelta(minutes=15)
    
    qr_code_data = f"00020126580014BR.GOV.BCB.PIX0136{payment_id}5204000053039865404{amount:.2f}5802BR5925GOVBR PAGAMENTOS6007BRASIL62260522{payment_id}6304"
    
    return {
        "success": True,
        "qr_code": qr_code_data,
        "qr_base64": "iVBORw0KGgoAAAANSUhEUgAAAMgAAADIAQMAAABl5f1ZAAAAA1BMVEX///+nxBvIAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAFUlEQVRoge3BAQ0AAADCoPdPbQ43oAAAAAAuNhB5AAE0eBBxAAAAAElFTkSuQmCC",
        "pix_code": qr_code_data,
        "payment_id": payment_id,
        "expiration": expiration.isoformat(),
        "status": "pending"
    }

@app.route('/gerar-pix', methods=['POST', 'OPTIONS'])
def gerar_pix():
    try:
        # Verifica se é uma requisição OPTIONS (pré-voo CORS)
        if request.method == 'OPTIONS':
            return jsonify({}), 200
        
        data = request.get_json()
        
        if not data or 'email' not in data or 'valor' not in data:
            return jsonify({"success": False, "error": "Email e valor são obrigatórios"}), 400
        
        try:
            valor = float(data['valor'])
            if valor <= 0:
                return jsonify({"success": False, "error": "Valor deve ser positivo"}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Valor deve ser um número válido"}), 400
        
        response = mercado_pago_simulator(
            amount=valor,
            email=data['email'],
            name=data.get('nome', 'Cliente GovBR'),
            cpf=data.get('cpf', '')
        )
        
        payments_db[response['payment_id']] = {
            "status": "pending",
            "amount": valor,
            "email": data['email'],
            "created_at": datetime.now().isoformat(),
            "expiration": response['expiration']
        }
        
        qr_codes_db[response['payment_id']] = response['qr_code']
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Erro interno no servidor",
            "details": str(e)
        }), 500

@app.route('/verificar-pagamento/<payment_id>', methods=['GET'])
def verificar_pagamento(payment_id):
    try:
        if payment_id in payments_db:
            payment = payments_db[payment_id]
            
            if (datetime.now() - datetime.fromisoformat(payment['created_at'])).seconds > 5:
                if random.random() < 0.2:
                    payment['status'] = 'approved'
                    payment['approved_at'] = datetime.now().isoformat()
            
            return jsonify({
                "status": payment['status'],
                "payment_details": {
                    "id": payment_id,
                    "amount": payment['amount'],
                    "status": payment['status'],
                    "created_at": payment['created_at'],
                    "expiration": payment['expiration']
                }
            })
        else:
            return jsonify({"error": "Pagamento não encontrado"}), 404
            
    except Exception as e:
        return jsonify({
            "error": "Erro ao verificar pagamento",
            "details": str(e)
        }), 500

@app.route('/')
def serve_index():
    return send_from_directory('static', 'pagamento-pix.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/health-check', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "ok" if payments_db else "empty",
            "environment": os.getenv('FLASK_ENV', 'development')
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
