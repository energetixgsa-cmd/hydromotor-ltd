import json
import hashlib
import base64
from PIL import Image


def canonical_snapshot(data: dict) -> tuple[str, str]:
    """
    Convert dict to canonical JSON (text) and SHA256 hex.
    """
    json_text = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    hash_hex = hashlib.sha256(json_text.encode('utf-8')).hexdigest()
    return json_text, hash_hex


def validate_signature(base64str: str) -> bytes:
    """
    Decode base64 signature, validate as PNG, return raw bytes.
    """
    from io import BytesIO
    import binascii
    limit = 512 * 1024
    try:
        if not isinstance(base64str, (str, bytes)) or len(base64str) > 4 * ((limit + 2) // 3):
            raise ValueError('Invalid signature size')
        raw = base64.b64decode(base64str, validate=True)
        if not raw or len(raw) > limit:
            raise ValueError('Invalid signature size')
        with Image.open(BytesIO(raw)) as image:
            if image.format != 'PNG' or not all(1 <= n <= 2048 for n in image.size):
                raise ValueError('Signature must be a PNG up to 2048 pixels per side')
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            image.load()
            rgba = image.convert('RGBA')
            background = Image.new('RGBA', rgba.size, 'white')
            visible = Image.alpha_composite(background, rgba).convert('RGB')
            if all(low == high for low, high in visible.getextrema()):
                raise ValueError('Signature is blank')
        return raw
    except (binascii.Error, OSError, SyntaxError, TypeError, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid PNG signature') from exc
