# demo_pipeline.py — save in C:\Projects\svacs-demo\
import requests
import json
import sys
import os

SAMACHAR_URL = "https://showing-wizard-buffer.ngrok-free.dev/api/v1/intelligence/image"
SVACS_URL    = "http://127.0.0.1:8000/intelligence/samachar"

def run_demo(image_path: str):
    print("=" * 60)
    print("  SVACS DEMO — Image → Samachar → Intelligence")
    print("=" * 60)
    print(f"\n  Image: {os.path.basename(image_path)}")
    print(f"  Size:  {os.path.getsize(image_path):,} bytes")

    # Step 1: Send to Samachar
    print("\n  [1] Sending to Samachar Vision Runtime...")
    with open(image_path, "rb") as f:
        files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
        r = requests.post(SAMACHAR_URL, files=files, timeout=120)

    if r.status_code != 200:
        print(f"  [ERROR] Samachar returned {r.status_code}: {r.text[:200]}")
        return

    samachar = r.json()
    print(f"  [OK] Vision confidence : {samachar.get('vision_confidence', 0):.2f}")
    print(f"  [OK] OCR results       : {[o['text'] for o in samachar.get('ocr_results', [])]}")
    print(f"  [OK] Trace ID          : {samachar.get('trace_id')}")

    # Step 2: Send to SVACS
    print("\n  [2] Sending to SVACS Intelligence Engine...")
    r2 = requests.post(SVACS_URL, json=samachar, timeout=30)

    if r2.status_code != 200:
        print(f"  [ERROR] SVACS returned {r2.status_code}: {r2.text[:200]}")
        return

    result = r2.json()
    print(f"\n  {'='*50}")
    print(f"  VESSEL IDENTIFICATION RESULT")
    print(f"  {'='*50}")
    print(f"  Vessel Class     : {result['vessel_class'].upper()}")
    print(f"  Confidence       : {result['confidence_score']:.2%}")
    print(f"  Risk Level       : {result['risk_level']}")
    print(f"  Validation       : {result['validation_status']}")
    print(f"  OCR Operator     : {result['ocr_operator'] or 'Not identified'}")
    print(f"  Operator Action  : {'Required' if result['operator_action_required'] else 'Not required'}")
    print(f"\n  Explanation:")
    print(f"  {result['explanation']}")
    print(f"\n  Evidence Chain:")
    for e in result['evidence_chain']:
        print(f"    - {e}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_demo(sys.argv[1])
    else:
        # Default: run on both images
        for img in os.listdir(r"C:\SVACS-images"):
            path = os.path.join(r"C:\SVACS-images", img)
            run_demo(path)
            print()