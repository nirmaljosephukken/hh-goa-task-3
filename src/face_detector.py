from dataclasses import dataclass
from pathlib import Path

import face_recognition
import numpy as np


@dataclass
class FaceResult:
    locations: list
    encodings: list


def detect_and_encode(image_path: str | Path) -> FaceResult:
    image = face_recognition.load_image_file(str(image_path))
    locations = face_recognition.face_locations(image, model="hog")
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)

    if not encodings:
        raise ValueError("No face detected in the input image.")

    return FaceResult(locations=locations, encodings=encodings)


def compare_faces(input_encoding, candidate_image_path: str | Path,
                  tolerance: float = 0.60) -> tuple[bool, float | None]:
    candidate = face_recognition.load_image_file(str(candidate_image_path))
    locations = face_recognition.face_locations(candidate, model="hog")
    encodings = face_recognition.face_encodings(candidate, known_face_locations=locations)

    if not encodings:
        return False, None

    input_vector = np.asarray(input_encoding, dtype=float)
    candidate_vector = np.asarray(encodings[0], dtype=float)
    distances = face_recognition.face_distance(
        np.asarray([input_vector]),
        candidate_vector,
    )
    distance = float(distances[0])
    return distance <= tolerance, distance
