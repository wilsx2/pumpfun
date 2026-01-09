/**
 * PumpFun Client - Modular JavaScript client for creating tokens on PumpFun
 * 
 * This client is designed to work with Phantom wallet and can be integrated
 * into any web application. It uses CDN-loaded Solana Web3.js library.
 * 
 * Usage:
 *   <script src="https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js"></script>
 *   <script src="https://cdn.jsdelivr.net/npm/bs58@5.0.0/dist/bs58.bundle.min.js"></script>
 *   <script src="pumpfun-client.js"></script>
 */

(function(global) {
    'use strict';

    /**
     * PumpFun Client Class
     * Handles token creation, transaction signing, and broadcasting
     */
    class PumpFunClient {
        /**
         * Create a new PumpFunClient instance
         * @param {string} serverUrl - Base URL of the PumpFun server (default: 'http://localhost:5000')
         */
        constructor(serverUrl = 'http://localhost:5000') {
            this.serverUrl = serverUrl;
            this.solana = null;
            this.wallet = null;
            this.publicKey = null;
        }

        /**
         * Initialize Phantom wallet connection
         * @returns {Promise<Object>} - Wallet connection result
         * @throws {Error} - If Phantom wallet is not available
         */
        async connectWallet() {
            const { solana } = window;
            
            if (!solana || !solana.isPhantom) {
                throw new Error('Phantom wallet not found. Please install Phantom extension.');
            }

            try {
                this.solana = solana;
                const response = await solana.connect();
                this.wallet = response;
                this.publicKey = new solanaWeb3.PublicKey(response.publicKey.toString());
                
                return {
                    publicKey: this.publicKey.toBase58(),
                    connected: true
                };
            } catch (error) {
                throw new Error(`Failed to connect wallet: ${error.message}`);
            }
        }

        /**
         * Disconnect from Phantom wallet
         */
        async disconnectWallet() {
            if (this.solana && this.wallet) {
                try {
                    await this.solana.disconnect();
                } catch (error) {
                    console.warn('Error disconnecting wallet:', error);
                }
            }
            this.wallet = null;
            this.publicKey = null;
        }

        /**
         * Check if wallet is connected
         * @returns {boolean}
         */
        isConnected() {
            return this.wallet !== null && this.publicKey !== null;
        }

        /**
         * Get current wallet public key
         * @returns {string|null} - Base58 encoded public key or null if not connected
         */
        getPublicKey() {
            return this.publicKey ? this.publicKey.toBase58() : null;
        }

        /**
         * Create an unsigned transaction for token creation
         * @param {Object} params - Transaction parameters
         * @param {string} params.name - Token name
         * @param {string} params.symbol - Token symbol
         * @param {string} [params.description] - Token description (optional)
         * @param {File|Blob} params.image - Image file
         * @param {number} [params.amount] - Initial amount in SOL (optional, defaults to 0)
         * @returns {Promise<Object>} - Returns unsigned_tx (base64), mint_keypair (base58), mint_public_key
         */
        async createTransaction({ name, symbol, description, image, amount }) {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected. Call connectWallet() first.');
            }

            // Validate required fields
            if (!name || !symbol || !image) {
                throw new Error('Missing required fields: name, symbol, and image are required');
            }

            // Amount is optional - default to 0 if not provided
            const amountValue = amount !== undefined && amount !== null ? amount : 0;

            const formData = new FormData();
            formData.append('name', name);
            formData.append('symbol', symbol);
            if (description) {
                formData.append('description', description);
            }
            formData.append('image', image);
            formData.append('amount', amountValue.toString());
            formData.append('user_public_key', this.publicKey.toBase58());

            const response = await fetch(`${this.serverUrl}/create_tx`, {
                method: 'POST',
                body: formData,
                mode: 'cors'
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            return await response.json();
        }

        /**
         * Sign a transaction with Phantom wallet and mint keypair
         * @param {string} unsignedTxBase64 - Base64 encoded unsigned transaction
         * @param {string} mintKeypairBase58 - Base58 encoded mint keypair (private key)
         * @returns {Promise<VersionedTransaction>} - Signed transaction
         */
        async signTransaction(unsignedTxBase64, mintKeypairBase58) {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected. Call connectWallet() first.');
            }

            // Decode the unsigned transaction
            const txBuffer = Uint8Array.from(atob(unsignedTxBase64), c => c.charCodeAt(0));
            const unsignedTx = solanaWeb3.VersionedTransaction.deserialize(txBuffer);

            // Decode the mint keypair
            const mintKeypair = solanaWeb3.Keypair.fromSecretKey(bs58.decode(mintKeypairBase58));

            // First, sign with Phantom wallet (user signature)
            const walletSignedTx = await this.solana.signTransaction(unsignedTx);

            // Then sign with the mint keypair
            walletSignedTx.sign([mintKeypair]);

            return walletSignedTx;
        }

        /**
         * Broadcast a signed transaction to the Solana network
         * @param {VersionedTransaction} signedTx - Signed transaction
         * @returns {Promise<Object>} - Transaction signature and URL
         */
        async broadcastTransaction(signedTx) {
            // Serialize the signed transaction to base64
            const signedTxBase64 = btoa(String.fromCharCode(...signedTx.serialize()));

            const response = await fetch(`${this.serverUrl}/broadcast_tx`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    signed_tx: signedTxBase64
                }),
                mode: 'cors'
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            return await response.json();
        }

        /**
         * Complete flow: create, sign, and broadcast a token creation transaction
         * @param {Object} params - Token creation parameters
         * @param {string} params.name - Token name
         * @param {string} params.symbol - Token symbol
         * @param {string} [params.description] - Token description (optional)
         * @param {File|Blob} params.image - Image file
         * @param {number} [params.amount] - Initial amount in SOL (optional, defaults to 0)
         * @param {Function} [onProgress] - Optional progress callback: (step, message) => void
         * @returns {Promise<Object>} - Transaction result with signature, URL, and mint public key
         */
        async createToken({ name, symbol, description, image, amount }, onProgress) {
            const progress = onProgress || (() => {});

            try {
                // Step 1: Create unsigned transaction
                progress('creating', 'Creating transaction...');
                const { unsigned_tx, mint_keypair, mint_public_key } = await this.createTransaction({
                    name,
                    symbol,
                    description,
                    image,
                    amount
                });

                progress('signing', 'Please approve the transaction in Phantom wallet...');
                
                // Step 2: Sign the transaction
                const signedTx = await this.signTransaction(unsigned_tx, mint_keypair);

                progress('broadcasting', 'Broadcasting transaction to Solana network...');

                // Step 3: Broadcast the transaction
                const result = await this.broadcastTransaction(signedTx);

                progress('complete', 'Transaction successful!');

                return {
                    ...result,
                    mint_public_key
                };
            } catch (error) {
                progress('error', error.message);
                throw error;
            }
        }

        /**
         * Check server health
         * @returns {Promise<Object>} - Health status
         */
        async checkHealth() {
            try {
                const response = await fetch(`${this.serverUrl}/health`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors'
                });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return await response.json();
            } catch (error) {
                console.error('Health check error:', error);
                throw new Error(`Health check failed: ${error.message}`);
            }
        }
    }

    // Export to global scope
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = PumpFunClient;
    } else {
        global.PumpFunClient = PumpFunClient;
    }

})(typeof window !== 'undefined' ? window : this);

