import argparse
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from .blockchain import connect, register_hash
from .face_detector import compare_faces, detect_and_encode
from .hashing import sha256_file
from .image_matcher import compare_images
from .matcher import format_candidate
from .web_search import (
    choose_candidate,
    download_image,
    google_lens_search,
    social_candidates,
    upload_image,
)


def main():
    # External search-result titles may contain characters unavailable in a
    # legacy Windows console encoding. Keep the pipeline running and preserve
    # all verification data rather than failing while displaying a title.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description="HH Goa 2026 Face -> Web -> Blockchain pipeline"
    )
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--search-type",
        choices=["exact_matches", "visual_matches"],
        default="exact_matches",
    )
    parser.add_argument("--tamper-test", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    serpapi_key = os.environ["SERPAPI_KEY"]
    rpc_url = os.environ["SEPOLIA_RPC_URL"]
    private_key = os.environ["PRIVATE_KEY"]
    contract_address = os.environ["CONTRACT_ADDRESS"]

    input_path = Path(args.image)

    print("=" * 62)
    print("HH GOA 2026 - FACE -> WEB -> BLOCKCHAIN")
    print("=" * 62)

    print("\n[1/6] Face detection...")
    face_result = detect_and_encode(input_path)
    print(f"      [OK] {len(face_result.encodings)} face(s) detected")
    print("      [OK] face encoding generated")

    print("\n[2/6] Uploading image for genuine web search...")
    image_id = upload_image(input_path, serpapi_key)
    print("      [OK] image uploaded")
    print("      [OK] search request will use returned image ID")

    print("\n[3/6] Searching Google Lens...")
    payload = google_lens_search(
        image_id,
        serpapi_key,
        search_type=args.search_type,
    )

    result_count = sum(
        len(payload.get(key, []) or [])
        for key in ("exact_matches", "visual_matches", "organic_results")
    )
    print(f"      [OK] {result_count} result records returned")

    print("\n[4/6] Validating discovered image...")
    candidates = social_candidates(payload)
    if not candidates:
        raise RuntimeError(
            "No usable social-media result was found. "
            "Try a different input image or search type."
        )

    artifact_path = Path("data/discovered_artifact.jpg")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = None
    source_url = ""
    distance = None
    image_match = None

    for index, item in enumerate(candidates, start=1):
        candidate_image = item.get("image") or item.get("thumbnail")
        candidate_path = artifact_path.with_name(f"social_candidate_{index}.jpg")
        if not candidate_image or not download_image(candidate_image, candidate_path):
            continue

        candidate_image_match = compare_images(input_path, candidate_path)
        if not candidate_image_match.matches:
            continue

        matched, candidate_distance = compare_faces(
            face_result.encodings[0], candidate_path)
        if candidate_distance is None or not matched:
            continue

        shutil.copyfile(candidate_path, artifact_path)
        candidate = item
        source_url = item["link"]
        distance = candidate_distance
        image_match = candidate_image_match
        break

    if not candidate:
        raise RuntimeError(
            "No social-media candidate was an image match and face match. "
            "A different photo of the same person is not accepted."
        )

    print("\n      MATCHING SOCIAL-MEDIA RESULT")
    print("      " + "-" * 50)
    print("      " + format_candidate(candidate))
    print(
        "      [OK] near-duplicate image match "
        f"(crop similarity: {image_match.crop_similarity:.3f})"
    )
    print("      [OK] candidate face detected")
    print(f"      [OK] face distance: {distance:.4f}")
    print("      [OK] face match: YES")

    print("\n[5/6] Registering fingerprint on Ethereum Sepolia...")
    digest = sha256_file(artifact_path)
    print(f"      SHA-256: {digest}")

    w3, account, contract = connect(
        rpc_url,
        private_key,
        contract_address,
    )

    tx_hash = register_hash(
        w3,
        account,
        contract,
        digest,
        source_url,
    )

    print("      [OK] transaction confirmed")
    print(f"      TX: {tx_hash}")
    print(f"      Explorer: https://sepolia.etherscan.io/tx/{tx_hash}")

    print("\n[6/6] Re-verifying against blockchain...")
    on_chain = contract.functions.verify(bytes.fromhex(digest)).call()

    exists, registered_url, timestamp, submitter = on_chain

    print(f"      On-chain record exists: {exists}")
    print(f"      Registered URL: {registered_url}")
    print(f"      Submitter: {submitter}")

    if exists and registered_url == source_url:
        print("\n      [OK] VERIFIED")
        print("      [OK] local fingerprint corresponds to on-chain record")
    else:
        print("\n      [FAIL] VERIFICATION FAILED")

    if args.tamper_test:
        print("\n[TAMPER TEST]")
        tampered = artifact_path.with_name("tampered_artifact.jpg")
        shutil.copyfile(artifact_path, tampered)

        data = bytearray(tampered.read_bytes())
        data[-1] = (data[-1] + 1) % 256
        tampered.write_bytes(data)

        tampered_hash = sha256_file(tampered)

        print(f"      Original: {digest}")
        print(f"      Tampered: {tampered_hash}")

        if tampered_hash != digest:
            print("      [OK] TAMPERING DETECTED")
        else:
            print("      [FAIL] Unexpected hash collision")

    print("\n" + "=" * 62)


if __name__ == "__main__":
    main()
