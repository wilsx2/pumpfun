"""
Minimal Python web server that acts as a proxy between clients and an external API.
Accepts requests with name, ticker, optional description, and image data.
"""

import os
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/', methods=['POST'])
def proxy():
    """
    Proxy endpoint that accepts requests with name, ticker, optional description, and image data.
    Validates the request format and forwards it to the external API.
    """
    # Validate required fields
    if 'name' not in request.form:
        return jsonify({'error': 'Missing required field: name'}), 400
    
    if 'ticker' not in request.form:
        return jsonify({'error': 'Missing required field: ticker'}), 400
    
    if 'image' not in request.files:
        return jsonify({'error': 'Missing required field: image'}), 400
    
    # Extract and validate data
    name = request.form.get('name', '').strip()
    ticker = request.form.get('ticker', '').strip()
    description = request.form.get('description', '').strip() if 'description' in request.form else None
    image_data = request.form.get('image', '').strip() # Base64 encoded image data
        
    # Validate that name, ticker, and image are not empty
    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400
    
    if not ticker:
        return jsonify({'error': 'Ticker cannot be empty'}), 400

    if not image_data:
        return jsonify({'error': 'Image cannot be empty'}), 400
    
    # Forward headers (excluding host and content-length which Flask handles)
    headers = {}
    for key, value in request.headers:
        if key.lower() not in ['host', 'content-length', 'connection', 'content-type']:
            headers[key] = value
    
    try:
        # Forward the request to the external API
        response = requests.post(''' Request contents ''')
        
        # Return the response from the external API
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Failed to forward request to external API',
            'message': str(e)
        }), 502


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

