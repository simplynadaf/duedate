"""
Textract adapter (spec R1). Converts a document (bytes or S3 object) into the Line[]
citation substrate the engine consumes. Falls back cleanly for plain-text samples so the
app and tests run without a Textract call.
"""
from __future__ import annotations

import os
import boto3

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_textract = boto3.client("textract", region_name=_REGION)


def lines_from_bytes(data: bytes) -> list[dict]:
    """Call Textract DetectDocumentText on raw image/PDF bytes; return [{id,text,confidence}]."""
    resp = _textract.detect_document_text(Document={"Bytes": data})
    return _lines_from_blocks(resp.get("Blocks", []))


def lines_from_s3(bucket: str, key: str) -> list[dict]:
    resp = _textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}})
    return _lines_from_blocks(resp.get("Blocks", []))


def _lines_from_blocks(blocks: list[dict]) -> list[dict]:
    out = []
    i = 0
    for b in blocks:
        if b.get("BlockType") == "LINE" and b.get("Text"):
            i += 1
            out.append({"id": f"L{i}", "text": b["Text"],
                        "confidence": round(b.get("Confidence", 99.0), 1)})
    return out


def lines_from_text(text: str) -> list[dict]:
    """Deterministic fallback: treat each non-empty input line as an extracted LINE."""
    out = []
    for i, raw in enumerate((ln for ln in text.splitlines() if ln.strip()), 1):
        out.append({"id": f"L{i}", "text": raw.strip(), "confidence": 100.0})
    return out
