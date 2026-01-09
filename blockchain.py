import os
import requests
import json
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig

def create_tx(name: str, symbol: str, description: str, image_data: bytes, amount: float, user_public_key: Pubkey) -> tuple[VersionedTransaction, Keypair] | None:
    # Generate a random keypair for token
    mint_keypair = Keypair()

    # Define token metadata
    form_data = {
        'name': name,
        'symbol': symbol,
        'description': description,
    }

    files = {
        'file': (f'{symbol}.png', image_data, 'image/png')
    }

    # Create IPFS metadata storage
    metadata_response = requests.post("https://pump.fun/api/ipfs", data=form_data, files=files)
    if metadata_response.status_code != 200:
        print(f"IPFS upload failed: {metadata_response.status_code} - {metadata_response.text}")
        return None
    try:
        metadata_response_json = metadata_response.json()
    except json.JSONDecodeError as e:
        print(f"Failed to parse IPFS response JSON: {e}")
        return None
    
    # Token metadata
    token_metadata = {
        'name': form_data['name'],
        'symbol': form_data['symbol'],
        'uri': metadata_response_json['metadataUri']
    }

    # Send the create transaction
    response = requests.post(
        f"https://pumpportal.fun/api/trade-local",
        headers={'Content-Type': 'application/json'},
        data=json.dumps({
            'publicKey': str(user_public_key),
            'action': 'create',
            'tokenMetadata': token_metadata,
            'mint': str(mint_keypair.pubkey()),
            'denominatedInSol': 'true',
            'amount': str(amount),
            'slippage': 10,
            'priorityFee': 0.0005,
            'pool': 'pump',
            'isMayhemMode': 'false'
        })
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        print(f"Error: Bad request - {response.text}")
        return None
    
    # Get the unsigned transaction
    unsigned_tx = VersionedTransaction.from_bytes(response.content)
    
    # Return unsigned transaction and mint keypair
    # Both need to be signed later
    return (unsigned_tx, mint_keypair)

def sign_tx(tx: VersionedTransaction, mint_keypair: Keypair, user_keypair: Keypair) -> VersionedTransaction:
    # Sign the transaction with both keypairs
    # Create a new VersionedTransaction with the message and both keypairs
    # The order matters - user keypair first (index 0), then mint keypair (index 1)
    # This matches the order of account_keys in the transaction message
    signed_tx = VersionedTransaction(tx.message, [user_keypair, mint_keypair])
    return signed_tx

def broadcast_tx(tx: VersionedTransaction) -> str | None:
    commitment = CommitmentLevel.Confirmed
    config = RpcSendTransactionConfig(preflight_commitment=commitment)
    txPayload = SendVersionedTransaction(tx, config)

    response = requests.post(
        url="https://api.mainnet-beta.solana.com/",
        headers={"Content-Type": "application/json"},
        data=SendVersionedTransaction(tx, config).to_json()
    )
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code} - {response.text}")
        return None
    
    response_json = response.json()
    print(f"Broadcast response: {response_json}")
    
    if 'error' in response_json:
        error = response_json['error']
        error_msg = error.get('message', 'Unknown error')
        error_data = error.get('data', {})
        
        # Check for AccountNotFound error
        if 'AccountNotFound' in str(error_data.get('err', '')) or 'no record of a prior credit' in error_msg:
            print("\n⚠️  ACCOUNT NOT FOUND ERROR:")
            print("   Your account doesn't exist on-chain yet. You need to fund it first.")
            print("   Send some SOL to your account address to initialize it.")
            print(f"   Account: {tx.message.account_keys[0] if len(tx.message.account_keys) > 0 else 'Unknown'}")
            print("   You can fund it from an exchange or another wallet.")
        
        print(f"\nTransaction error: {error_msg}")
        if error_data:
            print(f"Error details: {error_data}")
        return None
    
    if 'result' not in response_json:
        print(f"Unexpected response format: {response_json}")
        return None
    
    txSignature = response_json['result']
    print(f'✅ Transaction successful!')
    print(f'Transaction: https://solscan.io/tx/{txSignature}')
    return txSignature

if __name__ == "__main__":
    with open('./example.png', 'rb') as f:
        image_data = f.read()
    kp = Keypair.from_base58_string("private_key")
    result = create_tx("example", "EX", "This is an example", image_data, 0, kp.pubkey())
    if result:
        tx, mint_kp = result
        tx = sign_tx(tx, mint_kp, kp)
        broadcast_tx(tx)
    else:
        print("Failed to create transaction")