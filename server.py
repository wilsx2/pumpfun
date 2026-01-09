"""
Minimal Python web server that acts as a proxy between clients and an external API.
Accepts requests with name, ticker, optional description, and image data.
Also provides endpoints for creating and broadcasting transactions.
"""

import os
import base64
import requests
from flask import Flask, request, jsonify, Response
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from blockchain import create_tx, broadcast_tx

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/create_tx', methods=['POST'])
def create_transaction():
    """
    Create an unsigned transaction for token creation.
    Accepts: name, symbol, description, image (file), amount, user_public_key
    Returns: unsigned_tx (base64), mint_keypair (base58), mint_public_key (string)
    """
    # Validate required fields
    if 'name' not in request.form:
        return jsonify({'error': 'Missing required field: name'}), 400
    
    if 'symbol' not in request.form:
        return jsonify({'error': 'Missing required field: symbol'}), 400
    
    if 'image' not in request.files:
        return jsonify({'error': 'Missing required field: image'}), 400
    
    if 'amount' not in request.form:
        return jsonify({'error': 'Missing required field: amount'}), 400
    
    if 'user_public_key' not in request.form:
        return jsonify({'error': 'Missing required field: user_public_key'}), 400
    
    # Extract and validate data
    name = request.form.get('name', '').strip()
    symbol = request.form.get('symbol', '').strip()
    description = request.form.get('description', '').strip() if 'description' in request.form else ''
    amount = request.form.get('amount', '').strip()
    user_public_key_str = request.form.get('user_public_key', '').strip()
    image_file = request.files['image']
    
    # Validate that required fields are not empty
    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400
    
    if not symbol:
        return jsonify({'error': 'Symbol cannot be empty'}), 400
    
    if not amount:
        return jsonify({'error': 'Amount cannot be empty'}), 400
    
    if not user_public_key_str:
        return jsonify({'error': 'User public key cannot be empty'}), 400
    
    try:
        amount_float = float(amount)
    except ValueError:
        return jsonify({'error': 'Amount must be a valid number'}), 400
    
    try:
        user_public_key = Pubkey.from_string(user_public_key_str)
    except Exception as e:
        return jsonify({'error': f'Invalid user public key: {str(e)}'}), 400
    
    # Read image data
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
    mint_keypair_base58 = mint_keypair.to_base58_string()
    mint_public_key = str(mint_keypair.pubkey())
    
    return jsonify({
        'unsigned_tx': tx_base64,
        'mint_keypair': mint_keypair_base58,
        'mint_public_key': mint_public_key
    }), 200


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
    app.run(debug=True, host='0.0.0.0', port=5000)

