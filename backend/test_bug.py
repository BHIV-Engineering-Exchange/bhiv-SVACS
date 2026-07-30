import asyncio
from app.main import upload_image
from fastapi import UploadFile
import io

async def test():
    with open("ship2.jpeg", "rb") as f:
        file_content = f.read()
    
    file = UploadFile(filename="ship1.jpeg", file=io.BytesIO(file_content))
    
    try:
        res = await upload_image(file)
        if "explainable_image_base64" in res:
            del res["explainable_image_base64"]
        print("Success:", res)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    asyncio.run(test())
