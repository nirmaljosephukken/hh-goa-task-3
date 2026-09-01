"""
Optional deployment helper.

For a hackathon, deploying the contract through Remix is usually simpler.
If you use this script, compile the Solidity contract first and provide
the ABI/bytecode in artifacts/VerificationRegistry.json.
"""

import json
import os

from dotenv import load_dotenv
from web3 import Web3


def main():
    load_dotenv()

    w3 = Web3(Web3.HTTPProvider(os.environ["SEPOLIA_RPC_URL"]))
    account = w3.eth.account.from_key(os.environ["PRIVATE_KEY"])

    artifact_path = "artifacts/VerificationRegistry.json"
    with open(artifact_path, "r", encoding="utf-8") as fh:
        artifact = json.load(fh)

    contract = w3.eth.contract(
        abi=artifact["abi"],
        bytecode=artifact["bytecode"],
    )

    nonce = w3.eth.get_transaction_count(account.address)

    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": 11155111,
        "gas": 500000,
        "maxFeePerGas": w3.to_wei(30, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print("Contract:", receipt.contractAddress)
    print("Transaction:", tx_hash.hex())


if __name__ == "__main__":
    main()
