"""Local browser interface for the face-to-social-to-blockchain verifier."""

import uuid
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from .pipeline import PipelineError, run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_ROOT / "data" / "runs"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/verify")
def verify():
    uploaded = request.files.get("image")
    search_type = request.form.get("search_type", "visual_matches")

    if not uploaded or not uploaded.filename or not _allowed_file(uploaded.filename):
        return render_template(
            "index.html",
            error="Upload a JPG, JPEG, PNG, or WEBP image.",
        ), 400

    run_id = uuid.uuid4().hex
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(uploaded.filename)
    input_path = run_dir / f"input.{filename.rsplit('.', 1)[1].lower()}"
    uploaded.save(input_path)

    try:
        result = run_pipeline(
            input_path,
            search_type=search_type,
            tamper_test=True,
            artifact_dir=run_dir,
        )
    except PipelineError as error:
        return render_template(
            "index.html",
            error=str(error),
            input_url=f"/runs/{run_id}/{input_path.name}",
        )
    except Exception as error:  # Keep implementation details out of the browser.
        return render_template(
            "index.html",
            error=f"Verification could not finish: {error}",
            input_url=f"/runs/{run_id}/{input_path.name}",
        )

    result["input_url"] = f"/runs/{run_id}/{input_path.name}"
    if result.get("artifact_path"):
        result["artifact_url"] = f"/runs/{run_id}/{result['artifact_path'].name}"
    return render_template("index.html", result=result)


@app.get("/runs/<run_id>/<filename>")
def run_file(run_id: str, filename: str):
    return send_from_directory(RUNS_DIR / run_id, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
