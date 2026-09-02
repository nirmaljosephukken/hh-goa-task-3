# FaceProof — Face-to-Social-to-Blockchain Verification

FaceProof is a Python project that verifies whether a publicly indexed social-media image is the same image, or a close repost/crop, as an uploaded face image. It discovers candidates with Google Lens through SerpApi, checks image and face similarity, fingerprints the verified artifact with SHA-256, and records or confirms that fingerprint on Ethereum Sepolia.

> This is a verification demonstration, not an identity system. A matching result is evidence that images match; it does not establish a person's real-world identity.

## What it does

1. Detects at least one face in the input image and generates an embedding.
2. Uploads the real input image to SerpApi and searches Google Lens for exact or visual matches.
3. Keeps only discovered results from supported social platforms: Instagram, Facebook, X/Twitter, Threads, TikTok, Reddit, LinkedIn, Pinterest, Tumblr, and Bluesky. Video-hosting sites such as YouTube are excluded.
4. Downloads up to 12 candidates and accepts one only when both checks pass:
   - the image is a duplicate, recompressed repost, or plausible crop; and
   - the first detected candidate face is within the configured face-distance threshold.
5. Computes the SHA-256 fingerprint of the matched social image.
6. Checks the `VerificationRegistry` contract on Ethereum Sepolia.
7. Registers a new fingerprint and source URL only if the fingerprint has not already been registered.
8. Optionally modifies a copy of the artifact by one byte to demonstrate that its SHA-256 fingerprint changes.

The project deliberately does not create an on-chain record if no candidate passes both image and face verification. A different photograph of the same person is rejected.

## Architecture

```text
Uploaded image
  │
  ├── Face detection and encoding
  │
  └── SerpApi image upload → Google Lens search
                                │
                                └── Social-media candidates
                                      │
                                      ├── Near-duplicate/crop image check
                                      └── Face-distance check
                                                │
                                                └── SHA-256 artifact fingerprint
                                                          │
                                                          └── Ethereum Sepolia registry
                                                                │
                                                                └── Read-back verification
```

## Interfaces

### Local web interface

Start the Flask application:

```bash
python -m src.web_app
```

Open `http://127.0.0.1:5000` in a browser. The form accepts JPG, JPEG, PNG, and WEBP files up to 10 MB. After a file is selected, the form immediately displays its filename and confirms that it is ready to verify.

Choose either of these Google Lens modes:

- **Visual matches** — recommended in the web interface; useful for resized or visually similar reposts.
- **Exact matches** — limits the Lens search request to exact-match results.

The result page shows the input and selected social image (when available), face count, Lens result count, face distance, image crop similarity, SHA-256 fingerprint, Sepolia status, and an Etherscan transaction link for a new registration. The web interface always runs the tamper check. Uploaded and downloaded files are placed in a unique `data/runs/<run-id>/` directory.

### Command-line interface

Run a verification from the repository root:

```bash
python -m src.main --image data/input.png
```

Options:

```bash
python -m src.main --image data/input.png --search-type exact_matches
python -m src.main --image data/input.png --search-type visual_matches
python -m src.main --image data/input.png --tamper-test
```

The CLI defaults to `exact_matches`. It writes the selected artifact to `data/discovered_artifact.jpg`; candidate downloads use `data/social_candidate_<number>.jpg`.

## Requirements

- Python 3.10 or later
- A SerpApi key with Google Lens access
- An Ethereum Sepolia RPC endpoint
- A funded Sepolia test-wallet private key (test ETH only)
- A deployed `VerificationRegistry` contract

Python dependencies are listed in `requirements.txt`: `face-recognition`, NumPy, Pillow, Requests, python-dotenv, Web3, Flask, and pytest.

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### Windows note for face recognition

`face-recognition` requires `dlib`, which may need native compilation on Windows. A verified prebuilt installation path is:

```bash
pip install dlib-bin face-recognition-models click
pip install --no-deps face-recognition
pip install -r requirements.txt
```

You may also need the Microsoft C++ Build Tools if installing `dlib` from source.

## Configuration

Copy the example configuration and supply real values:

```bash
copy .env.example .env
```

```text
SERPAPI_KEY=your_serpapi_key
SEPOLIA_RPC_URL=https://your-sepolia-rpc-provider.example
PRIVATE_KEY=your_test_wallet_private_key
CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
```

Keep `.env` private. Never commit a real private key or use a wallet that holds production funds.

## Verification rules

A candidate must satisfy both of the following:

- **Face verification:** the face-recognition distance between the input encoding and the candidate's first detected face must be at most `0.60`.
- **Image verification:** an image passes when either its difference-hash distance is at most `40` with an aspect-ratio delta at most `0.08`, or its best crop similarity is at least `0.82`.

The image checker evaluates grayscale visual similarity over several plausible crop positions, allowing reposts that have been recompressed, resized, or cropped. These thresholds support the demo workflow; they are not calibrated for forensic or production identity use.

## Blockchain registry

The included Solidity contract is [`contracts/VerificationRegistry.sol`](contracts/VerificationRegistry.sol). It runs on Ethereum Sepolia (chain ID `11155111`) and stores, for each SHA-256 digest:

- `bytes32 dataHash`
- source URL
- block timestamp
- submitting wallet address

It exposes:

- `register(bytes32 dataHash, string sourceUrl)` — stores a new record and emits `RecordRegistered`; duplicate hashes are rejected.
- `verify(bytes32 dataHash)` — returns whether the record exists, its URL, timestamp, and submitter.

The image itself is never placed on-chain—only its cryptographic fingerprint and provenance URL are stored. Any content change produces a new SHA-256 digest and fails a comparison with the registered digest.

## Deploying the contract

For a quick demonstration, deploy with Remix:

1. Open Remix and create `contracts/VerificationRegistry.sol` using the contract in this repository.
2. Compile with Solidity 0.8.20 or later.
3. Connect MetaMask to Sepolia.
4. Deploy `VerificationRegistry`.
5. Put the deployed address in `CONTRACT_ADDRESS` in `.env`.

An optional [`scripts/deploy.py`](scripts/deploy.py) helper is also included. It expects an ABI/bytecode artifact at `artifacts/VerificationRegistry.json` and uses the same `.env` values.

## Tests

Run the offline test suite:

```bash
pytest
```

The tests cover SHA-256 behavior, rejection of modified content, social-domain filtering, and acceptance/rejection behavior for duplicate, cropped, and unrelated images. Tests do not require SerpApi, Sepolia, or private credentials.

## Repository structure

```text
hh-goa-face-blockchain/
├── contracts/
│   └── VerificationRegistry.sol       # Sepolia fingerprint registry
├── data/                              # local inputs and generated artifacts (ignored)
├── demo/
│   └── README.md                      # recording checklist
├── scripts/
│   └── deploy.py                      # optional deployment helper
├── src/
│   ├── blockchain.py                  # Web3 contract connection and registration
│   ├── face_detector.py               # face detection, encoding, and comparison
│   ├── hashing.py                     # streaming SHA-256 utilities
│   ├── image_matcher.py               # repost/crop image comparison
│   ├── main.py                        # CLI workflow
│   ├── matcher.py                     # social-domain filtering and formatting
│   ├── pipeline.py                    # reusable workflow used by the web app
│   ├── web_app.py                     # Flask routes and upload handling
│   ├── web_search.py                  # SerpApi/Lens and image-download helpers
│   ├── static/app.css                 # local interface styling
│   └── templates/index.html           # upload form and result page
├── tests/                             # offline unit tests
├── .env.example
├── requirements.txt
└── README.md
```

## Demo checklist

1. Use an image you are permitted to process and that is genuinely indexed in a downloadable social-media post.
2. Show the selected filename in the local form or run the CLI command.
3. Show face detection, live Google Lens discovery, and the selected social result.
4. Show both the image and face verification metrics.
5. Show the SHA-256 digest and Sepolia transaction/record.
6. Run the tamper check and show that the fingerprint changes.

Do not reveal `.env`, API keys, or the private key in a recording.

## Limitations and responsible use

- Google Lens ranking, availability, and SerpApi results are external and can change.
- Some social platforms block automated image downloads; the project safely refuses to register an unverified fallback.
- A social result is image-match evidence, not identity proof or proof of authorship.
- Face embeddings can have false positives and false negatives and should not be used as a sole basis for consequential decisions.
- Sepolia is a public testnet intended for demonstrations, not production evidence storage.