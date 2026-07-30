import cv2
import numpy as np
import base64

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decodes a base64 string into an OpenCV image (numpy array)."""
    # Remove prefix if present
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    
    img_data = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")
    return img

def encode_image_base64(img: np.ndarray) -> str:
    """Encodes an OpenCV image into a base64 string."""
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def preprocess_for_inference(img: np.ndarray) -> np.ndarray:
    """Basic preprocessing if needed (YOLO handles most internally, but here for extensibility)."""
    # Future enhancement: contrast adjustment, normalization, etc.
    return img

def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decodes raw image bytes into an OpenCV image (numpy array)."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")
    return img

