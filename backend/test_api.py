import requests
import base64
import json
import cv2
import numpy as np
import sys
import os

def test_vision_runtime(image_path: str):
    # 1. Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: Could not find image at {image_path}")
        return

    print(f"Loading image from {image_path}...")
    
    # 2. Prepare the file upload
    filename = os.path.basename(image_path)
    
    # 3. Make the POST request with file
    url = "http://localhost:8000/api/v1/analyze?return_explainable_image=true"
    print(f"Sending request to {url}...")
    
    # 4. Make the POST request
    try:
        with open(image_path, "rb") as image_file:
            files = {"file": (filename, image_file, "image/jpeg")}
            response = requests.post(url, files=files)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if response is not None:
            print(f"Response: {response.text}")
        return

    # 5. Process the response
    result = response.json()
    
    print("\n--- Response ---")
    print(f"Replay ID: {result.get('replay_id')}")
    
    print(f"\nDetections ({len(result.get('detections', []))}):")
    for d in result.get('detections', []):
        print(f"  - {d['label']} (Confidence: {d['confidence']:.2f})")
        
    print(f"\nOCR Results ({len(result.get('ocr_results', []))}):")
    for o in result.get('ocr_results', []):
        print(f"  - '{o['text']}' (Confidence: {o['confidence']:.2f})")

    # 6. Save the explainable image if returned
    explainable_b64 = result.get('explainable_image_base64')
    if explainable_b64:
        img_data = base64.b64decode(explainable_b64)
        output_path = f"explained_{result.get('replay_id')}.jpg"
        with open(output_path, "wb") as f:
            f.write(img_data)
        print(f"\nSaved explainable evidence image to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <path_to_image.jpg>")
    else:
        test_vision_runtime(sys.argv[1])
