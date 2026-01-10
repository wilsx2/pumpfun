# PumpFun Token Creator

A Python Flask server and JavaScript client for creating tokens on PumpFun using Solana blockchain.

## Features

- Create tokens on PumpFun via API
- Phantom wallet integration for transaction signing
- Modular JavaScript client for easy integration
- Complete example HTML application with image preview
- Image upload and caching functionality
- Server-side HTML injection for seamless deployment
- Railway deployment support

## Server Setup

### Requirements

- Python 3.8+
- Flask
- Flask-CORS
- Solana Python libraries (solders)
- requests
- base58

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

**Note:** The server can be deployed to Railway or similar platforms. It automatically detects the `PORT` environment variable and supports `X-Forwarded-Proto` headers for HTTPS.

## JavaScript Client

The modular JavaScript client (`pumpfun-client.js`) can be integrated into any web application. It uses Phantom wallet for transaction signing and works entirely in the browser using CDN-loaded libraries.

### Quick Start

1. Include the required CDN libraries and the client:

```html
<script src="https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js"></script>
<!-- bs58 can be loaded from CDN or implemented inline (see example.html) -->
<script src="https://cdn.jsdelivr.net/npm/bs58@5.0.0/dist/bs58.bundle.min.js"></script>
<!-- Or use the inline implementation from example.html -->
<script src="pumpfun-client.js"></script>
```

**Note:** The `example.html` file includes an inline base58 implementation to avoid CDN issues. You can use either approach.

2. Use the client in your code:

```javascript
// Initialize client (server URL is optional, defaults to http://localhost:5000)
const client = new PumpFunClient('http://localhost:5000');

// Connect Phantom wallet
await client.connectWallet();

// Create a token
const result = await client.createToken({
    name: 'My Token',
    symbol: 'MTK',
    description: 'A cool token',  // Optional
    image: imageFile,  // File or Blob object
    amount: 0.1  // Optional: Initial amount in SOL (defaults to 0)
});

console.log('Transaction:', result.signature);
console.log('Mint Public Key:', result.mint_public_key);
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
  - `name` (string, required): Token name
  - `symbol` (string, required): Token symbol
  - `description` (string, optional): Token description
  - `image` (File|Blob, required): Image file for the token
  - `amount` (number, optional): Initial amount in SOL (defaults to 0 if not provided)
- `onProgress` (Function, optional): Progress callback `(step, message) => void`
  - Steps: `'creating'`, `'signing'`, `'broadcasting'`, `'complete'`, `'error'`

**Returns:** `Promise<Object>` with:
- `signature`: Transaction signature
- `transaction_url`: Solscan URL
- `mint_public_key`: Mint account public key

**Throws:** Error if wallet not connected or transaction fails

#### `createTransaction(params)`

Create an unsigned transaction for token creation (lower-level method).

**Parameters:** Same as `createToken` params

**Returns:** `Promise<Object>` with:
- `unsigned_tx`: Base64 encoded unsigned transaction
- `mint_keypair`: Base58 encoded mint keypair
- `mint_public_key`: Mint account public key

#### `signTransaction(unsignedTxBase64, mintKeypairBase58)`

Sign a transaction with Phantom wallet and mint keypair.

**Parameters:**
- `unsignedTxBase64` (string): Base64 encoded unsigned transaction
- `mintKeypairBase58` (string): Base58 encoded mint keypair

**Returns:** `Promise<VersionedTransaction>` - Signed transaction

#### `broadcastTransaction(signedTx)`

Broadcast a signed transaction to the Solana network.

**Parameters:**
- `signedTx` (VersionedTransaction): Signed transaction object

**Returns:** `Promise<Object>` with transaction signature and URL

#### `checkHealth()`

Check if the server is running and healthy.

**Returns:** `Promise<Object>` with server status

### Example Usage

The server can serve the example HTML page directly. Simply navigate to the root URL:

1. Start the Python server: `python server.py`
2. Open `http://localhost:5000` in a web browser (with Phantom wallet installed)
3. Connect your wallet and create a token!

**Features of the example:**
- Image preview functionality
- Support for base64 images via `?image_token=<token>` query parameter
- Progress indicators during token creation
- Automatic server URL detection
- Wallet connection status display
- Transaction result display with links to Solscan and Pump.fun

You can also open `example.html` directly in a browser, but you'll need to ensure the server is running and update the server URL manually.

## Server API Endpoints

### `GET /`

Serves the example HTML page with server URL and optional base64 image injected.

**Query Parameters:**
- `image_token` (string, optional): Token to retrieve cached image

**Response:** HTML page with injected `window.SERVER_URL` and `window.BASE64_IMAGE` variables

### `GET /pumpfun-client.js`

Serves the JavaScript client library.

**Response:** JavaScript file content

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### `POST /upload_image`

Upload a base64 image and receive a token for later retrieval.

**Request:** `application/json`
```json
{
  "image": "data:image/png;base64,..."  // Base64 encoded image
}
```

**Response:**
```json
{
  "token": "uuid-token-string",
  "status": "success"
}
```

**Note:** Images are cached in memory with a 1-hour TTL. Use the token with the `?image_token=<token>` query parameter on the root endpoint.

### `POST /create_tx`

Create an unsigned transaction for token creation.

**Request:** `multipart/form-data`
- `name` (string, required): Token name
- `symbol` (string, required): Token symbol
- `description` (string, optional): Token description
- `image` (file, required): Token image file
- `amount` (string, optional): Initial amount in SOL (defaults to "0" if not provided)
- `user_public_key` (string, required): User's Solana public key (base58)

**Response:**
```json
{
  "unsigned_tx": "base64_encoded_transaction",
  "mint_keypair": "base58_encoded_mint_keypair",
  "mint_public_key": "mint_public_key_string"
}
```

**Error Responses:**
- `400`: Missing required fields or invalid input
- `500`: Server error during transaction creation

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

**Error Responses:**
- `400`: Invalid transaction data
- `500`: Failed to broadcast transaction

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

## Deployment

### Railway

The server is configured to work with Railway deployment:

1. Set the `PORT` environment variable (Railway sets this automatically)
2. Set `FLASK_DEBUG=false` for production (or `true` for debugging)
3. The server automatically detects HTTPS via `X-Forwarded-Proto` header

### Environment Variables

- `PORT`: Server port (defaults to 5000)
- `FLASK_DEBUG`: Enable Flask debug mode (defaults to `False`)

### Image Caching

Images uploaded via `/upload_image` are cached in memory with a 1-hour TTL. For production deployments with high traffic, consider:
- Using Redis or similar external cache
- Implementing persistent storage for images
- Adjusting `IMAGE_CACHE_TTL` in `server.py`

## Security Notes

- **Never expose private keys** in client-side code
- Always use Phantom wallet or similar secure wallet solutions
- The mint keypair is generated server-side and only the private key is sent to the client for signing
- Ensure your server is running over HTTPS in production
- Validate all inputs on both client and server side
- Image cache is stored in memory - consider external storage for production
- CORS is enabled for all origins - restrict in production if needed

## Architecture

The application consists of:

- **server.py**: Flask server that handles API requests and serves the HTML page
- **pumpfun-client.js**: Browser-side JavaScript client for interacting with the server and Phantom wallet
- **blockchain.py**: Core blockchain logic for creating and broadcasting transactions
- **example.html**: Complete example UI demonstrating token creation

The server acts as a proxy between the client and PumpFun's APIs, handling:
- Image upload to IPFS
- Transaction creation via PumpFun API
- Transaction broadcasting to Solana network

## License

MIT

