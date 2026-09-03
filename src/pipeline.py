"""Reusable end-to-end verification workflow for the CLI and web interface."""

import os
import shutil
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from .blockchain import connect, register_hash
from .face_detector import compare_faces, detect_and_encode
from .hashing import sha256_file
from .image_matcher import compare_images
from .web_search import (
    download_image,
    google_lens_search,
    social_candidates,
    upload_image,
)


class PipelineError(RuntimeError):
    """A user-facing pipeline failure that must not create an on-chain record."""


MAX_CANDIDATES_TO_CHECK = 12
RECORD_REGISTERED_EVENT = "RecordRegistered(bytes32,string,uint256,address)"


def _registration_transaction_hash(w3, contract_address: str, digest: str) -> str | None:
    """Find the transaction that emitted the registration event for a hash."""
    latest_block = w3.eth.block_number
    event_topic = "0x" + w3.keccak(text=RECORD_REGISTERED_EVENT).hex()
    logs = w3.eth.get_logs(
        {
            "address": contract_address,
            "fromBlock": max(0, latest_block - 9999),
            "toBlock": latest_block,
            "topics": [event_topic, "0x" + digest],
        }
    )
    return logs[-1]["transactionHash"].hex() if logs else None


def run_pipeline(
    image_path: str | Path,
    search_type: str = "exact_matches",
    tamper_test: bool = False,
    artifact_dir: str | Path = "data",
    status_callback: Callable[[str], None] | None = None,
) -> dict:
    """Find a matching social image, then create or verify its Sepolia record."""
    load_dotenv()
    input_path = Path(image_path)
    output_dir = Path(artifact_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def report(message: str) -> None:
        if status_callback:
            status_callback(message)

    try:
        serpapi_key = os.environ["SERPAPI_KEY"]
        rpc_url = os.environ["SEPOLIA_RPC_URL"]
        private_key = os.environ["PRIVATE_KEY"]
        contract_address = os.environ["CONTRACT_ADDRESS"]
    except KeyError as error:
        raise PipelineError(f"Missing required .env value: {error.args[0]}") from error

    report("Detecting and encoding the input face")
    face_result = detect_and_encode(input_path)

    report("Uploading the image to Google Lens through SerpApi")
    image_id = upload_image(input_path, serpapi_key)

    report("Searching Google Lens for social-media matches")
    payload = google_lens_search(image_id, serpapi_key, search_type=search_type)
    result_count = sum(
        len(payload.get(key, []) or [])
        for key in ("exact_matches", "visual_matches", "organic_results")
    )
    candidates = social_candidates(payload)
    search_summary = {
        "lens_results": result_count,
        "social_candidates": len(candidates),
        "candidates_checked": 0,
        "candidate_limit": MAX_CANDIDATES_TO_CHECK,
    }
    if not candidates:
        return {
            "outcome": "no_social_result",
            "face_count": len(face_result.encodings),
            "search_type": search_type,
            "result_count": result_count,
            "search_summary": search_summary,
            "message": "Google Lens returned no supported social-media result for this image.",
            "evaluated_candidates": [],
        }

    report("Checking social results for the same image and face")
    artifact_path = output_dir / "discovered_artifact.jpg"
    evaluated_candidates = []
    selected = None
    for index, item in enumerate(candidates[:MAX_CANDIDATES_TO_CHECK], start=1):
        candidate_image = item.get("image") or item.get("thumbnail")
        candidate_path = output_dir / f"social_candidate_{index}.jpg"
        evaluated = {"candidate": item, "candidate_path": candidate_path}

        if not candidate_image:
            evaluated.update(
                status="skipped",
                reason="Google Lens did not provide an image or thumbnail to inspect.",
            )
            evaluated_candidates.append(evaluated)
            continue

        if not download_image(candidate_image, candidate_path, timeout=12):
            evaluated.update(
                status="skipped",
                reason="The result image could not be downloaded for verification.",
            )
            evaluated_candidates.append(evaluated)
            continue

        image_match = compare_images(input_path, candidate_path)
        face_match, face_distance = compare_faces(face_result.encodings[0], candidate_path)
        evaluated.update(
            image_match=image_match,
            face_distance=face_distance,
            face_match=face_match,
        )

        if not image_match.matches and not face_match:
            evaluated.update(
                status="rejected",
                reason="It did not match the uploaded image and its face did not pass verification.",
            )
        elif not image_match.matches:
            evaluated.update(
                status="rejected",
                reason="The same person may appear, but this is not the same image or a qualifying repost/crop.",
            )
        elif face_distance is None:
            evaluated.update(
                status="rejected",
                reason="The image matched visually, but no face could be detected in the candidate.",
            )
        elif not face_match:
            evaluated.update(
                status="rejected",
                reason="The image matched visually, but the candidate face was outside the verification threshold.",
            )
        else:
            evaluated.update(status="verified", reason="Same-image and face checks passed.")
            shutil.copyfile(candidate_path, artifact_path)
            selected = {**evaluated, "artifact_path": artifact_path}

        evaluated_candidates.append(evaluated)
        if selected:
            break

    search_summary["candidates_checked"] = len(evaluated_candidates)

    if not selected:
        face_candidates = [
            item
            for item in evaluated_candidates
            if item.get("face_match") and item.get("face_distance") is not None
        ]
        if face_candidates:
            best = max(
                face_candidates,
                key=lambda item: item["image_match"].crop_similarity,
            )
            return {
                "outcome": "same_person_different_image",
                "face_count": len(face_result.encodings),
                "search_type": search_type,
                "result_count": result_count,
                "search_summary": search_summary,
                "message": (
                    "A social post with the same person was found, but it is a different "
                    "image. No blockchain record was created."
                ),
                "candidate": best["candidate"],
                "artifact_path": best["candidate_path"],
                "image_match": best["image_match"],
                "face_distance": best["face_distance"],
                "evaluated_candidates": evaluated_candidates,
            }

        return {
            "outcome": "social_result_not_verified",
            "face_count": len(face_result.encodings),
            "search_type": search_type,
            "result_count": result_count,
            "search_summary": search_summary,
            "message": (
                "Social-media results were found, but none provided a downloadable "
                "face-verified match. No blockchain record was created."
            ),
            "evaluated_candidates": evaluated_candidates,
        }

    digest = sha256_file(selected["artifact_path"])
    source_url = selected["candidate"]["link"]
    report("Checking the tamper-evident record on Ethereum Sepolia")
    w3, account, contract = connect(rpc_url, private_key, contract_address)
    exists, registered_url, timestamp, submitter = contract.functions.verify(
        bytes.fromhex(digest)
    ).call()

    tx_hash = None
    registration_status = "already_registered" if exists else "registered"
    if not exists:
        report("Registering the matched artifact fingerprint on Ethereum Sepolia")
        tx_hash = register_hash(w3, account, contract, digest, source_url)
        exists, registered_url, timestamp, submitter = contract.functions.verify(
            bytes.fromhex(digest)
        ).call()
    else:
        report("Finding the original Sepolia registration transaction")
        tx_hash = _registration_transaction_hash(w3, contract_address, digest)

    tamper = None
    if tamper_test:
        tampered_path = output_dir / "tampered_artifact.jpg"
        shutil.copyfile(selected["artifact_path"], tampered_path)
        data = bytearray(tampered_path.read_bytes())
        data[-1] = (data[-1] + 1) % 256
        tampered_path.write_bytes(data)
        tampered_hash = sha256_file(tampered_path)
        tamper = {
            "original_hash": digest,
            "tampered_hash": tampered_hash,
            "detected": tampered_hash != digest,
        }

    return {
        "outcome": "verified",
        "face_count": len(face_result.encodings),
        "search_type": search_type,
        "result_count": result_count,
        "search_summary": search_summary,
        "candidate": selected["candidate"],
        "artifact_path": selected["artifact_path"],
        "image_match": selected["image_match"],
        "face_distance": selected["face_distance"],
        "digest": digest,
        "registration_status": registration_status,
        "tx_hash": tx_hash,
        "explorer_url": (
            f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None
        ),
        "on_chain": {
            "exists": exists,
            "source_url": registered_url,
            "timestamp": timestamp,
            "submitter": submitter,
            "contract_address": contract_address,
            "contract_explorer_url": (
                "https://sepolia.etherscan.io/address/"
                f"{contract_address}#events"
            ),
        },
        "tamper": tamper,
        "evaluated_candidates": evaluated_candidates,
    }
