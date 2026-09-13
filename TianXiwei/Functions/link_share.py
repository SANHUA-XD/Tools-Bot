"""
Stateless encode/decode for the /link -> https://t.me/Bot?start=req_<encoded>
deep-link flow (ported from the Link-Share-Bot reference, simplified -
no shortener/verification/premium/timers, just the core encode-a-chat-id-
into-a-start-param mechanic).
"""

import base64


def encode_chat_id(chat_id: int) -> str:
    raw = str(chat_id).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_chat_id(encoded: str) -> int | None:
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        return int(raw.decode("ascii"))
    except Exception:
        return None
