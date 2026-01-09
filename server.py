"""
Minimal Python web server that acts as a proxy between clients and an external API.
Accepts requests with name, ticker, optional description, and image data.
Also provides endpoints for creating and broadcasting transactions.
"""

import os
import base64
import requests
import base58
from flask import Flask, request, jsonify, Response
from flask_cors import CORS, cross_origin
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from blockchain import create_tx, broadcast_tx

app = Flask(__name__)
# Enable CORS for all routes with explicit configuration
CORS(app, 
     resources={
         r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }
     })

# Ensure CORS headers are added to all responses, including errors
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', methods=['GET'])
def serve_example():
    """Serve the example HTML page with server URL injected."""
    try:
        # Read the example.html file
        html_path = os.path.join(os.path.dirname(__file__), 'example.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Get the server URL from the request
        # Use request.url_root to get the base URL (e.g., http://localhost:5000/)
        server_url = request.url_root.rstrip('/')
        
        # Replace the placeholder or hardcoded server URL in the HTML
        # We'll inject it as a script variable before the PumpFunClient initialization
        injection_script = f'''
    <script>
        // Server URL injected by server
        window.SERVER_URL = '{server_url}';
    </script>
'''
        
        # Insert the script right before the closing </head> tag
        html_content = html_content.replace('</head>', injection_script + '</head>')
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        return jsonify({'error': f'Failed to serve page: {str(e)}'}), 500


@app.route('/pumpfun-client.js', methods=['GET'])
def serve_client_js():
    """Serve the pumpfun-client.js file."""
    try:
        js_path = os.path.join(os.path.dirname(__file__), 'pumpfun-client.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        return js_content, 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except Exception as e:
        return jsonify({'error': f'Failed to serve JavaScript file: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/create_tx', methods=['POST'])
def create_transaction():
    """
    Create an unsigned transaction for token creation.
    Accepts: name, symbol, description, image (file), amount (optional), user_public_key
    Returns: unsigned_tx (base64), mint_keypair (base58), mint_public_key (string)
    """
    # Validate required fields
    if 'name' not in request.form:
        return jsonify({'error': 'Missing required field: name'}), 400
    
    if 'symbol' not in request.form:
        return jsonify({'error': 'Missing required field: symbol'}), 400
    
    if 'image' not in request.files:
        return jsonify({'error': 'Missing required field: image'}), 400
    
    if 'user_public_key' not in request.form:
        return jsonify({'error': 'Missing required field: user_public_key'}), 400
    
    # Extract and validate data
    name = request.form.get('name', '').strip()
    symbol = request.form.get('symbol', '').strip()
    description = request.form.get('description', '').strip() if 'description' in request.form else ''
    amount = request.form.get('amount', '0').strip()  # Default to 0 if not provided
    user_public_key_str = request.form.get('user_public_key', '').strip()
    image_file = request.files['image']
    
    # Validate that required fields are not empty
    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400
    
    if not symbol:
        return jsonify({'error': 'Symbol cannot be empty'}), 400
    
    if not user_public_key_str:
        return jsonify({'error': 'User public key cannot be empty'}), 400
    
    # Amount is optional - default to 0 if empty
    if not amount:
        amount_float = 0.0
    else:
        try:
            amount_float = float(amount)
            if amount_float < 0:
                return jsonify({'error': 'Amount cannot be negative'}), 400
        except ValueError:
            return jsonify({'error': 'Amount must be a valid number'}), 400
    
    try:
        user_public_key = Pubkey.from_string(user_public_key_str)
    except Exception as e:
        return jsonify({'error': f'Invalid user public key: {str(e)}'}), 400
    
    # Read image data
    try:
        image_data = image_file.read()
        if not image_data:
            return jsonify({'error': 'Image file is empty'}), 400
        
        # Create the transaction
        result = create_tx(name, symbol, description, image_data, amount_float, user_public_key)
        
        if result is None:
            return jsonify({'error': 'Failed to create transaction'}), 500
        
        unsigned_tx, mint_keypair = result
        
        # Serialize the transaction and keypair for client
        tx_bytes = bytes(unsigned_tx)
        tx_base64 = base64.b64encode(tx_bytes).decode('utf-8')
        # Convert full keypair to base58 (64 bytes)
        # JavaScript Keypair.fromSecretKey() expects the full 64-byte keypair
        mint_keypair_bytes = bytes(mint_keypair)
        mint_keypair_base58 = base58.b58encode(mint_keypair_bytes).decode('utf-8')
        mint_public_key = str(mint_keypair.pubkey())
        
        return jsonify({
            'unsigned_tx': tx_base64,
            'mint_keypair': mint_keypair_base58,
            'mint_public_key': mint_public_key
        }), 200
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error creating transaction: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/broadcast_tx', methods=['POST'])
def broadcast_transaction():
    """
    Broadcast a signed transaction to the Solana network.
    Accepts: signed_tx (base64 encoded)
    Returns: transaction signature or error
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    
    if 'signed_tx' not in data:
        return jsonify({'error': 'Missing required field: signed_tx'}), 400
    
    signed_tx_base64 = data['signed_tx']
    
    if not signed_tx_base64:
        return jsonify({'error': 'signed_tx cannot be empty'}), 400
    
    try:
        # Deserialize the signed transaction
        tx_bytes = base64.b64decode(signed_tx_base64)
        signed_tx = VersionedTransaction.from_bytes(tx_bytes)
    except Exception as e:
        return jsonify({'error': f'Invalid transaction data: {str(e)}'}), 400
    
    # Broadcast the transaction
    tx_signature = broadcast_tx(signed_tx)
    
    if tx_signature is None:
        return jsonify({'error': 'Failed to broadcast transaction'}), 500
    
    return jsonify({
        'status': 'success',
        'signature': tx_signature,
        'transaction_url': f'https://solscan.io/tx/{tx_signature}'
    }), 200

if __name__ == '__main__':
    # Railway provides PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    # Disable debug mode in production (enable only if FLASK_DEBUG=true)
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)

