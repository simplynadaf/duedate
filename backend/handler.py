"""
DueDate API Lambda handler. Orchestrates: extract -> deterministic analyze -> guardrailed
narrate -> free-aid routing. Single POST endpoint behind API Gateway (Function URL also OK).

Request JSON (any one of):
  { "text": "...notice text..." , "language": "en"|"es", "state": "CA" }   # sample / paste
  { "s3": {"bucket": "...", "key": "..."}, "language": "...", "state": "..." }  # uploaded
  { "image_b64": "<base64 image/pdf>", "language": "...", "state": "..." }

Response: deterministic facts + cited lines + grounded narration + real aid resources.
Read-only to the tenant's data; no persistence beyond the short-TTL upload bucket.
"""
from __future__ import annotations

import base64
import json
import re

import engine
import extract
import narrate
import aid

_STATE_RE = re.compile(r"\b([A-Z]{2})\s+\d{5}\b")  # ", CA 90011"
_STATE_NAMES = {"california": "CA", "new york": "NY", "washington": "WA",
                "texas": "TX", "florida": "FL"}


def _detect_state(lines: list[dict]) -> str | None:
    blob = " ".join(l["text"] for l in lines)
    m = _STATE_RE.search(blob)
    if m:
        return m.group(1)
    low = blob.lower()
    for name, code in _STATE_NAMES.items():
        if name in low:
            return code
    return None


def _cors(body: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event, context=None):
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS" \
            or event.get("httpMethod") == "OPTIONS":
        return _cors({"ok": True})

    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        req = json.loads(body) if isinstance(body, str) else body
    except (ValueError, TypeError):
        return _cors({"error": "invalid JSON body"}, 400)

    language = (req.get("language") or "en").lower()

    # 1. Extract -> Line[]
    try:
        if req.get("text"):
            lines = extract.lines_from_text(req["text"])
        elif req.get("s3"):
            lines = extract.lines_from_s3(req["s3"]["bucket"], req["s3"]["key"])
        elif req.get("image_b64"):
            lines = extract.lines_from_bytes(base64.b64decode(req["image_b64"]))
        else:
            return _cors({"error": "provide text, s3, or image_b64"}, 400)
    except Exception as e:  # noqa: BLE001 - surface extraction errors cleanly
        return _cors({"error": f"extraction failed: {type(e).__name__}: {e}"}, 502)

    if not lines:
        return _cors({"error": "no text found in document"}, 422)

    # 2. Deterministic analysis (facts are code)
    line_objs = [engine.Line(l["id"], l["text"], l.get("confidence", 99.0)) for l in lines]
    analysis = engine.analyze(line_objs)

    # 3. State detection + real free-aid routing
    state = (req.get("state") or _detect_state(lines) or "").upper() or None
    analysis["state"] = state
    analysis["resources"] = aid.resources_for(state)

    # 4. Guardrailed narration/translation (model may only narrate facts)
    try:
        analysis["narration"] = narrate.narrate(analysis, language)
    except Exception as e:  # noqa: BLE001
        analysis["narration"] = {"summary": "", "checklist": [], "rights": [],
                                 "grounded": False, "error": f"{type(e).__name__}"}

    analysis["language"] = language
    return _cors(analysis)
