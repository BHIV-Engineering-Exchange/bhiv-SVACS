r"""
verify_determinism.py

Checks that the SVACS image pipeline gives the same answer for the same
image: it sends one image several times and compares every field of the
responses. Use it for the "deterministic execution" evidence the Phase 2
brief asks for.

Fields that legitimately differ between requests are ignored:
  * trace_id
  * any UUID inside a string (for example the trace id inside crop image URLs)
Everything else is compared: class, confidence, top predictions, boxes,
risk level, ship names, OCR text and so on. The evidence image is compared
by its SHA-256 and reported separately.

Usage (backend must be running):
  python verify_determinism.py PATH\TO\image.jpg
  python verify_determinism.py image.jpg --runs 10
  python verify_determinism.py image.jpg --key YOUR_KEY      (or set SVACS_API_KEY)

Across a restart (cold start versus warm):
  python verify_determinism.py image.jpg --save baseline.json
  ... stop and start the backend ...
  python verify_determinism.py image.jpg --compare baseline.json

Numbers are treated as equal if they differ by no more than --tolerance
(default 1e-6). The largest difference actually seen is always printed, so
the result can be quoted exactly. Writes determinism_report.json.

Exit code: 0 identical, 1 differences found, 2 could not run.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("This script needs the 'requests' package (it is in the backend venv).")
    sys.exit(2)

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
IGNORED_KEYS = {"trace_id"}
IMAGE_KEY = "explainable_image_base64"


def normalise(value, evidence):
    """Drop request-specific values; hash the evidence image."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in IGNORED_KEYS:
                continue
            if key == IMAGE_KEY:
                evidence.append(hashlib.sha256((item or "").encode("utf-8")).hexdigest())
                continue
            out[key] = normalise(item, evidence)
        return out
    if isinstance(value, list):
        return [normalise(item, evidence) for item in value]
    if isinstance(value, str):
        return UUID.sub("<id>", value)
    return value


def compare(a, b, path, tolerance, differences, deviation):
    """Collect differences between two normalised structures."""
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            differences.append((path, a, b))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        gap = abs(a - b)
        deviation[0] = max(deviation[0], gap)
        if gap > tolerance:
            differences.append((path, a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                differences.append(("%s.%s" % (path, key), a.get(key, "<missing>"), b.get(key, "<missing>")))
            else:
                compare(a[key], b[key], "%s.%s" % (path, key), tolerance, differences, deviation)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            differences.append((path + ".length", len(a), len(b)))
        for index, (x, y) in enumerate(zip(a, b)):
            compare(x, y, "%s[%d]" % (path, index), tolerance, differences, deviation)
    elif a != b:
        differences.append((path, a, b))


def send(url, image_path, key, timeout):
    headers = {"X-API-Key": key} if key else {}
    with open(image_path, "rb") as handle:
        response = requests.post(
            url,
            files={"file": (os.path.basename(image_path), handle, "image/jpeg")},
            headers=headers,
            timeout=timeout,
        )
    if response.status_code in (401, 403):
        raise RuntimeError(
            "The server rejected the API key (HTTP %d). Pass --key or set SVACS_API_KEY."
            % response.status_code
        )
    if response.status_code != 200:
        raise RuntimeError("HTTP %d from the server: %s" % (response.status_code, response.text[:300]))
    return response.json()


def short(value):
    text = json.dumps(value) if not isinstance(value, str) else value
    return text if len(text) <= 60 else text[:57] + "..."


def main():
    parser = argparse.ArgumentParser(description="Check that the pipeline is deterministic.")
    parser.add_argument("image", help="Path to the test image")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--endpoint", default="/intelligence/image")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--key", default=os.getenv("SVACS_API_KEY", ""))
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--save", help="Save the first normalised response to this file")
    parser.add_argument("--compare", help="Also compare every run with a saved baseline")
    parser.add_argument("--report", default="determinism_report.json")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print("Image not found: %s" % args.image)
        sys.exit(2)
    if args.runs < 2:
        print("--runs must be at least 2")
        sys.exit(2)

    url = args.url.rstrip("/") + args.endpoint
    with open(args.image, "rb") as handle:
        image_sha = hashlib.sha256(handle.read()).hexdigest()
    print("Image: %s" % args.image)
    print("Image SHA-256: %s" % image_sha)
    print("Endpoint: %s   runs: %d   tolerance: %g" % (url, args.runs, args.tolerance))
    print("")

    results, evidence_hashes = [], []
    for number in range(1, args.runs + 1):
        evidence = []
        try:
            raw = send(url, args.image, args.key, args.timeout)
        except requests.exceptions.ConnectionError:
            print("Could not connect to %s. Is the backend running?" % url)
            sys.exit(2)
        except RuntimeError as err:
            print(str(err))
            sys.exit(2)
        results.append(normalise(raw, evidence))
        evidence_hashes.append(evidence[0] if evidence else "")
        print("  run %d: class=%s  confidence=%s" % (number, raw.get("vessel_class"), raw.get("confidence_score")))

    baselines = [("run 1", results[0])]
    if args.compare:
        with open(args.compare, "r", encoding="utf-8") as handle:
            baselines.append(("baseline file", json.load(handle)["response"]))

    differences, deviation = [], [0.0]
    for label, base in baselines:
        for number, current in enumerate(results, start=1):
            if label == "run 1" and number == 1:
                continue
            found = []
            compare(base, current, "response", args.tolerance, found, deviation)
            differences.extend(("run %d vs %s" % (number, label), p, x, y) for p, x, y in found)

    same_evidence = len(set(evidence_hashes)) == 1
    identical = not differences

    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            json.dump({"image_sha256": image_sha, "response": results[0]}, handle, indent=2)
        print("\nBaseline saved to %s" % args.save)

    print("")
    print("Largest numeric difference seen: %g" % deviation[0])
    print("Evidence image identical across runs: %s" % ("yes" if same_evidence else "NO"))
    if identical:
        print("RESULT: IDENTICAL. All %d runs gave the same response." % args.runs)
    else:
        print("RESULT: DIFFERENCES FOUND (%d)" % len(differences))
        for where, path, x, y in differences[:25]:
            print("  %s  %s: %s  !=  %s" % (where, path, short(x), short(y)))
        if len(differences) > 25:
            print("  ... and %d more" % (len(differences) - 25))

    report = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": url,
        "image_sha256": image_sha,
        "runs": args.runs,
        "tolerance": args.tolerance,
        "compared_with_baseline_file": bool(args.compare),
        "identical": identical,
        "largest_numeric_difference": deviation[0],
        "evidence_image_identical": same_evidence,
        "differences": [
            {"where": w, "path": p, "first": short(x), "second": short(y)} for w, p, x, y in differences
        ],
    }
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("Report written to %s" % args.report)
    sys.exit(0 if identical else 1)


if __name__ == "__main__":
    main()
