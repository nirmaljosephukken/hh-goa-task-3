# HH Goa 2026 — Face → Web → Blockchain Verification

A reproducible pipeline for the HH Goa 2026 Shortlisting Task 3:

**Face scan → face detection/encoding → genuine reverse-image/web search → candidate post → face verification → SHA-256 fingerprint → Ethereum Sepolia → independent verification**

## What this demonstrates

1. Detects and encodes a face in an input image.
2. Sends the actual input image to Google Lens through SerpApi. The result is not hardcoded.
3. Selects only a social-media result dynamically from returned exact/visual matches.
4. Tries discovered social-media candidates until one is an exact, resized, or cropped repost of the input and passes face verification.
5. Computes a SHA-256 fingerprint of the discovered artifact.
6. Registers the fingerprint and source URL in an Ethereum Sepolia smart contract.
7. Reads the record back from the blockchain and compares it with a freshly computed hash.
8. Optionally performs a one-pixel tamper test to demonstrate that modified content fails verification.

## Architecture

```text
input.jpg
   |
   +--> Face detection + encoding
   |
   +--> SerpApi Image Upload
             |
             +--> Google Lens Exact Matches / Visual Matches
                         |
                         +--> candidate URL/image
                                      |
                                      +--> face check
                                      |
                                      +--> SHA-256
                                               |
                                               +--> Ethereum Sepolia
                                                        |
                                                        +--> read-back verification
```

## Important scope note

The face encoder and the reverse-image search solve different parts of the pipeline. The encoder proves that the input contains a detectable face and provides an embedding that can be compared with a candidate image. Google Lens performs the web discovery step. The project does **not** claim that a face embedding is itself a general-purpose search engine.

Use images of people you have permission to process, or suitable public-domain/public-figure demonstration material.

## Requirements

- Python 3.10+
- A SerpApi API key
- An Ethereum Sepolia RPC URL
- A funded Sepolia wallet private key (test ETH only)
- A deployed `VerificationRegistry` contract

## Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### Windows face-recognition note

`face-recognition` depends on `dlib`, which may try to compile from source on
Windows. The project was verified with this prebuilt setup after installing the
Microsoft C++ Build Tools:

```bash
pip install dlib-bin face-recognition-models click
pip install --no-deps face-recognition
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```text
SERPAPI_KEY=...
SEPOLIA_RPC_URL=...
PRIVATE_KEY=...
CONTRACT_ADDRESS=...
```

Never commit `.env` or a real private key.

## Run

```bash
python -m src.main --image data/input.jpg
```

Useful options:

```bash
python -m src.main --image data/input.jpg --search-type exact_matches
python -m src.main --image data/input.jpg --search-type visual_matches
python -m src.main --image data/input.jpg --tamper-test
```

## Local web interface

To run the optional local interface, start the project environment and run:

```bash
python -m src.web_app
```

Then open `http://127.0.0.1:5000`. Upload an image to view the face count,
Google Lens result count, discovered social post, image and face-match scores,
SHA-256 fingerprint, Sepolia verification status, transaction link, and tamper
test on one page. The interface uses the same verification rules as the CLI.

For the interface used in the final demo, start it with network access and use
the port printed by Flask. The page makes live requests to SerpApi and Sepolia,
so it can take up to two minutes to return a result.

The pipeline intentionally stops without creating a blockchain record when Lens
does not return a downloadable social-media image that is a duplicate, repost,
or crop of the input and is face-verified. A different photo of the same person
is rejected.
Use an image with a genuinely indexed social post for the end-to-end demonstration.

## Deploy the contract

The simplest route is Remix:

1. Open Remix.
2. Create `contracts/VerificationRegistry.sol`.
3. Compile with Solidity 0.8.20+.
4. Connect MetaMask to Sepolia.
5. Deploy `VerificationRegistry`.
6. Copy the deployed contract address into `.env`.

A deployment script is also included as a starting point, but Remix is recommended for a short hackathon submission because it reduces setup friction.

## Blockchain

This project uses **Ethereum Sepolia**, chain ID `11155111`.

The contract stores:
- `bytes32 dataHash`
- source URL
- timestamp
- submitting address

The actual image is not stored on-chain. Only its cryptographic fingerprint is stored.

## Verification logic

If:

```text
SHA256(discovered_file) == dataHash stored on-chain
```

the artifact is verified against the registered record.

If the file changes, even by one pixel, its SHA-256 digest changes and verification fails.

## Demo recording

Recommended recording sequence:

1. Show the input image.
2. Run the command.
3. Show face detection and encoding.
4. Show live Google Lens results and the dynamically selected social-media source.
5. Show candidate-image face check.
6. Show SHA-256.
7. Show Sepolia transaction hash.
8. Open the transaction/contract in a Sepolia explorer.
9. Run verification.
10. Run the tamper test and show the mismatch.

## Limitations

- Reverse-image search availability and ranking depend on the external search provider.
- A search result is evidence of an image match, not proof of a person's real-world identity.
- Some social platforms block automated image retrieval. The pipeline deliberately does not register an unverified fallback; use an input image whose genuine Lens results include a downloadable matching social-media post.
- Face embeddings can produce false positives/negatives and should not be treated as definitive identity proof.
- Sepolia is a public testnet; it is appropriate for demonstration, not production evidence.

## Project structure

```text
hh-goa-face-blockchain/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── contracts/
│   └── VerificationRegistry.sol
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── face_detector.py
│   ├── web_search.py
│   ├── matcher.py
│   ├── hashing.py
│   ├── blockchain.py
│   └── verifier.py
├── scripts/
│   └── deploy.py
├── tests/
│   ├── test_hashing.py
│   └── test_verification.py
├── data/
└── demo/
```
