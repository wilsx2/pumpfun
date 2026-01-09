# PumpFun Token Creator

A Python Flask server and JavaScript client for creating tokens on PumpFun using Solana blockchain.

## Features

- Create tokens on PumpFun via API
- Phantom wallet integration for transaction signing
- Modular JavaScript client for easy integration
- Complete example HTML application

## Server Setup

### Requirements

- Python 3.8+
- Flask
- Solana Python libraries (solders)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
python server.py
```

The server will run on `http://localhost:5000` by default.

## JavaScript Client

The modular JavaScript client (`pumpfun-client.js`) can be integrated into any web application. It uses Phantom wallet for transaction signing and works entirely in the browser using CDN-loaded libraries.

### Quick Start

1. Include the required CDN libraries and the client:

```html
<script src="https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js"></script>
<script src="https://unpkg.com/bs58@latest/dist/bs58.bundle.min.js"></script>
<script src="pumpfun-client.js"></script>
```

2. Use the client in your code:

```javascript
// Initialize client
const client = new PumpFunClient('http://localhost:5000');

// Connect Phantom wallet
await client.connectWallet();

// Create a token
const result = await client.createToken({
    name: 'My Token',
    symbol: 'MTK',
    description: 'A cool token',
    image: imageFile,  // File object from input
    amount: 0.1  // SOL
});

console.log('Transaction:', result.signature);
console.log('View on Solscan:', result.transaction_url);
```

### API Reference

#### `new PumpFunClient(serverUrl)`

Create a new client instance.

- `serverUrl` (string, optional): Base URL of the PumpFun server. Default: `'http://localhost:5000'`

#### `connectWallet()`

Connect to Phantom wallet. Must be called before creating tokens.

**Returns:** `Promise<Object>` with `publicKey` and `connected` status

**Throws:** Error if Phantom wallet is not available

#### `disconnectWallet()`

Disconnect from Phantom wallet.

#### `isConnected()`

Check if wallet is currently connected.

**Returns:** `boolean`

#### `getPublicKey()`

Get the current wallet's public key.

**Returns:** `string|null` - Base58 encoded public key or null if not connected

#### `createToken(params, onProgress)`

Complete flow: create, sign, and broadcast a token creation transaction.

**Parameters:**
- `params` (Object):
  - `name` (string): Token name
  - `symbol` (string): Token symbol
  - `description` (string, optional): Token description
  - `image` (File|Blob): Image file for the token
  - `amount` (number): Initial amount in SOL
- `onProgress` (Function, optional): Progress callback `(step, message) => void`
  - Steps: `'creating'`, `'signing'`, `'broadcasting'`, `'complete'`, `'error'`

**Returns:** `Promise<Object>` with:
- `signature`: Transaction signature
- `transaction_url`: Solscan URL
- `mint_public_key`: Mint account public key

**Throws:** Error if wallet not connected or transaction fails

#### `checkHealth()`

Check if the server is running and healthy.

**Returns:** `Promise<Object>` with server status

### Example Usage

See `example.html` for a complete working example with a user interface.

To run the example:

1. Start the Python server: `python server.py`
2. Open `example.html` in a web browser (with Phantom wallet installed)
3. Connect your wallet and create a token!

## Server API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### `POST /create_tx`

Create an unsigned transaction for token creation.

**Request:** `multipart/form-data`
- `name` (string, required): Token name
- `symbol` (string, required): Token symbol
- `description` (string, optional): Token description
- `image` (file, required): Token image file
- `amount` (string, required): Initial amount in SOL
- `user_public_key` (string, required): User's Solana public key (base58)

**Response:**
```json
{
  "unsigned_tx": "base64_encoded_transaction",
  "mint_keypair": "base58_encoded_mint_keypair",
  "mint_public_key": "mint_public_key_string"
}
```

### `POST /broadcast_tx`

Broadcast a signed transaction to the Solana network.

**Request:** `application/json`
```json
{
  "signed_tx": "base64_encoded_signed_transaction"
}
```

**Response:**
```json
{
  "status": "success",
  "signature": "transaction_signature",
  "transaction_url": "https://solscan.io/tx/..."
}
```

## Integration Examples

### React Component

```javascript
import { useState, useEffect } from 'react';

function TokenCreator() {
    const [client, setClient] = useState(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        setClient(new PumpFunClient('http://localhost:5000'));
    }, []);

    const handleConnect = async () => {
        try {
            await client.connectWallet();
            setConnected(true);
        } catch (error) {
            console.error('Connection failed:', error);
        }
    };

    const handleCreateToken = async (formData) => {
        try {
            const result = await client.createToken(formData, (step, msg) => {
                console.log(`${step}: ${msg}`);
            });
            console.log('Success!', result);
        } catch (error) {
            console.error('Error:', error);
        }
    };

    return (
        <div>
            {!connected ? (
                <button onClick={handleConnect}>Connect Wallet</button>
            ) : (
                <TokenForm onSubmit={handleCreateToken} />
            )}
        </div>
    );
}
```

### Vue.js Component

```javascript
export default {
    data() {
        return {
            client: null,
            connected: false
        };
    },
    mounted() {
        this.client = new PumpFunClient('http://localhost:5000');
    },
    methods: {
        async connectWallet() {
            try {
                await this.client.connectWallet();
                this.connected = true;
            } catch (error) {
                console.error('Connection failed:', error);
            }
        },
        async createToken(formData) {
            try {
                const result = await this.client.createToken(formData);
                console.log('Success!', result);
            } catch (error) {
                console.error('Error:', error);
            }
        }
    }
};
```

## Security Notes

- **Never expose private keys** in client-side code
- Always use Phantom wallet or similar secure wallet solutions
- The mint keypair is generated server-side and only the private key is sent to the client for signing
- Ensure your server is running over HTTPS in production
- Validate all inputs on both client and server side

## License

MIT

