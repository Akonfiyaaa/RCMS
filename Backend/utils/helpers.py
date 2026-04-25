import base64

# Convert image bytes → base64 (for sending to Flutter)
def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# Convert base64 → bytes (if needed)
def base64_to_image(base64_str: str) -> bytes:
    return base64.b64decode(base64_str)


# Format MongoDB object
def serialize_mongo(doc):
    doc["_id"] = str(doc["_id"])
    return doc