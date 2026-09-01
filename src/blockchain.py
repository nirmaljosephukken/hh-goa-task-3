import json
from pathlib import Path

from web3 import Web3


ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dataHash", "type": "bytes32"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
        ],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dataHash", "type": "bytes32"}
        ],
        "name": "verify",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def connect(rpc_url: str, private_key: str, contract_address: str):
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        raise RuntimeError("Could not connect to the Sepolia RPC endpoint.")

    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=ABI,
    )

    return w3, account, contract


def register_hash(w3, account, contract, digest_hex: str, source_url: str) -> str:
    digest = bytes.fromhex(digest_hex)

    nonce = w3.eth.get_transaction_count(account.address)
    priority_fee = w3.to_wei(1, "gwei")
    base_fee = w3.eth.get_block("latest").get("baseFeePerGas", 0)
    max_fee = max(w3.to_wei(30, "gwei"), base_fee * 2 + priority_fee)

    transaction_params = {
        "from": account.address,
        "nonce": nonce,
        "chainId": 11155111,
    }
    estimated_gas = contract.functions.register(
        digest,
        source_url,
    ).estimate_gas(transaction_params)

    tx = contract.functions.register(
        digest,
        source_url,
    ).build_transaction(
        {
            **transaction_params,
            "gas": int(estimated_gas * 1.2),
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError("Blockchain transaction failed.")

    return tx_hash.hex()


def verify_hash(w3, contract, digest_hex: str):
    digest = bytes.fromhex(digest_hex)
    return contract.functions.verify(digest).call()
