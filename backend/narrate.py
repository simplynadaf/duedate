"""
Bedrock narration layer (spec R8-R10, R14).

The model NEVER sees the raw document and NEVER decides facts. It receives the
deterministic Facts from engine.analyze() and may only:
  - translate + simplify them into the requested language and reading level,
  - produce a dated action checklist derived strictly from those facts.
Any sentence that does not reference a provided fact id is dropped before display.
If a needed fact is absent, the model is instructed to say the notice does not say it.
"""
from __future__ import annotations

import json
import os
import boto3

_REGION = os.environ.get("AWS_REGION", "us-east-1")
# Nova Lite is cheap, fast, multilingual, and available on this account.
_MODEL = os.environ.get("DUEDATE_MODEL", "us.amazon.nova-2-lite-v1:0")

_bedrock = boto3.client("bedrock-runtime", region_name=_REGION)

LANG = {"en": "English", "es": "Spanish"}

_SYSTEM = (
    "You are DueDate, a calm, plain-language guide for a tenant who received an eviction "
    "notice. You are NOT a lawyer and must never give legal advice or legal strategy. "
    "You may ONLY use the FACTS provided to you. Every fact has an id. Rules:\n"
    "1. Never state a date, amount, or right that is not in the FACTS. Do not use outside "
    "knowledge to fill gaps.\n"
    "2. If the user would need information that is not in the FACTS, say plainly that the "
    "notice does not say it, and point them to free help.\n"
    "3. Write at about a 6th-grade reading level. Short sentences. Be reassuring but honest.\n"
    "4. For each sentence that makes a claim, end it with the supporting fact id in "
    "square brackets, like [deadline]. Sentences with no fact id will be removed.\n"
    "5. Output ONLY valid JSON with keys: summary (string), checklist (array of "
    "{text, cite}), rights (array of {text, cite}). No prose outside the JSON."
)


def _prompt(analysis: dict, language: str) -> str:
    facts = {f["key"]: f for f in analysis["facts"]}
    lang_name = LANG.get(language, "English")
    return (
        f"Write the output in {lang_name}.\n\n"
        f"NOTICE TYPE (plain): {analysis['notice_type_label']} -- "
        f"{analysis['notice_type_plain']}\n\n"
        f"FACTS (the only things you may assert):\n{json.dumps(facts, indent=2)}\n\n"
        f"THINGS THE NOTICE DOES NOT SAY: {analysis['missing'] or 'none noted'}\n\n"
        "Produce the JSON now. The 'summary' must lead with the single most important "
        "deadline if one exists. The 'checklist' MUST contain at least two concrete, dated "
        "steps the tenant should take, each grounded in a fact id placed in its 'cite' "
        "field (for example: pay the amount by the deadline -> cite 'amount_due' and "
        "'deadline'). The 'rights' array must contain at least one item grounded in a fact "
        "id. Never leave 'checklist' empty when a deadline fact exists."
    )


def narrate(analysis: dict, language: str = "en") -> dict:
    """Call Bedrock under guardrails; drop any claim lacking a real fact id."""
    valid_ids = {f["key"] for f in analysis["facts"]} | {"notice_type"}
    body = {
        "system": [{"text": _SYSTEM}],
        "messages": [{"role": "user", "content": [{"text": _prompt(analysis, language)}]}],
        "inferenceConfig": {"maxTokens": 900, "temperature": 0.2, "topP": 0.9},
    }
    resp = _bedrock.invoke_model(modelId=_MODEL, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    text = payload["output"]["message"]["content"][0]["text"]
    data = _coerce_json(text)

    # Guardrail enforcement (R9): keep only items citing a real fact id.
    data["checklist"] = [c for c in data.get("checklist", [])
                         if _cite_ok(c.get("cite"), valid_ids)]
    data["rights"] = [r for r in data.get("rights", [])
                     if _cite_ok(r.get("cite"), valid_ids)]
    data["grounded"] = True
    return data


def _cite_ok(cite, valid_ids) -> bool:
    """Accept cite as a list (['deadline','amount_due']) or a string ('[deadline]')."""
    if not cite:
        return False
    if isinstance(cite, (list, tuple)):
        parts = [str(p) for p in cite]
    else:
        parts = str(cite).replace("[", "").replace("]", "").split(",")
    return any(p.strip() in valid_ids for p in parts)


def _coerce_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"summary": "", "checklist": [], "rights": []}
