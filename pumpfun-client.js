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

    // Check for required dependencies - but don't throw immediately, allow the class to be defined
    // The actual methods will check and throw errors when called if dependencies are missing
    if (typeof solanaWeb3 === 'undefined') {
        console.error('PumpFunClient: solanaWeb3 is not defined. Make sure @solana/web3.js is loaded before this script.');
        // Try to find it under a different name or wait for it
        if (typeof window !== 'undefined') {
            // Check common alternative names
            if (window.solanaWeb3) {
                global.solanaWeb3 = window.solanaWeb3;
            } else if (window.solana && window.solana.web3) {
                global.solanaWeb3 = window.solana.web3;
            } else {
                // Try to access it after a short delay (for async loading)
                setTimeout(function() {
                    if (typeof solanaWeb3 !== 'undefined' && typeof PumpFunClient !== 'undefined') {
                        console.log('PumpFunClient: solanaWeb3 loaded successfully');
                    }
                }, 100);
            }
        }
    }

    if (typeof bs58 === 'undefined') {
        console.error('PumpFunClient: bs58 is not defined. Make sure bs58 is loaded before this script.');
    }

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
            // Check for solanaWeb3 dependency
            if (typeof solanaWeb3 === 'undefined') {
                throw new Error('solanaWeb3 is not available. Make sure @solana/web3.js is loaded: <script src="https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js"></script>');
            }
            
            // Try multiple ways to find Phantom wallet
            let solana = null;
            
            // Method 1: Check window.solana directly
            if (window.solana && (window.solana.isPhantom || typeof window.solana.connect === 'function')) {
                solana = window.solana;
            }
            // Method 2: Check window.phantom.solana
            else if (window.phantom && window.phantom.solana) {
                solana = window.phantom.solana;
            }
            // Method 3: Wait a bit and try again (for delayed injection)
            else {
                // Wait up to 1 second for Phantom to inject, checking every 100ms
                for (let i = 0; i < 10; i++) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    if (window.solana && (window.solana.isPhantom || typeof window.solana.connect === 'function')) {
                        solana = window.solana;
                        break;
                    }
                    if (window.phantom && window.phantom.solana) {
                        solana = window.phantom.solana;
                        break;
                    }
                }
            }
            
            // Check if solana exists and has required methods
            if (!solana || typeof solana.connect !== 'function') {
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

            // Check for dependencies
            if (typeof solanaWeb3 === 'undefined') {
                throw new Error('solanaWeb3 is not available. Make sure @solana/web3.js is loaded.');
            }
            if (typeof bs58 === 'undefined') {
                throw new Error('bs58 is not available. Make sure bs58 is loaded.');
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

