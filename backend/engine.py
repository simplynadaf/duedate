"""
DueDate deterministic trust engine.

Facts are code, not the model. Everything in this module is rule-based and references the
exact extracted line it came from. The LLM (narration/translation) runs elsewhere and is
constrained to the Facts produced here. See spec/duedate.md R4-R7, R10.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Citation substrate: one extracted line of the user's own notice.
# In production these come from Textract blocks (text + geometry + confidence).
# ---------------------------------------------------------------------------
@dataclass
class Line:
    id: str
    text: str
    confidence: float = 99.0  # Textract LINE confidence (0-100)


@dataclass
class Fact:
    """A single deterministic finding, always pinned to a citing line id."""
    key: str
    value: str
    cites: list[str] = field(default_factory=list)  # Line ids
    computed: bool = False
    rule: Optional[str] = None  # which rule produced a computed value

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Notice-type knowledge base. Sourced from CA Courts self-help, Nolo state
# cure-period chart, WA LawHelp, Virginia landlord-remedies code (see
# decision/CONCEPT-LOCKED.md). Patterns are deliberately conservative: if we
# are not confident, we classify "unknown" rather than guess.
# ---------------------------------------------------------------------------
NOTICE_TYPES = {
    "pay_or_quit": {
        "label": "Pay Rent or Quit (nonpayment of rent)",
        "patterns": [r"pay\s+rent\s+or\s+quit", r"pay\s+or\s+quit",
                     r"notice\s+to\s+pay", r"rent\s+.*\s+due", r"amount\s+due"],
        "plain": "Your landlord says rent is unpaid. You usually can STOP the eviction "
                 "by paying the full amount by the deadline.",
    },
    "cure_or_quit": {
        "label": "Cure (fix) or Quit (lease violation)",
        "patterns": [r"cure\s+or\s+quit", r"perform\s+or\s+quit",
                     r"correct\s+the\s+violation", r"comply\s+or\s+vacate"],
        "plain": "Your landlord says a lease rule was broken. You usually can STOP the "
                 "eviction by fixing the problem by the deadline.",
    },
    "unconditional_quit": {
        "label": "Unconditional Quit (move out, no chance to fix)",
        "patterns": [r"unconditional", r"without\s+(the\s+)?(right|opportunity)\s+to\s+cure",
                     r"no\s+opportunity\s+to\s+cure"],
        "plain": "This is the most serious notice. It asks you to move out with no chance "
                 "to fix the problem. Getting free legal help quickly matters most here.",
    },
    "termination_notice": {
        "label": "Termination / No-fault notice (30/60/90 day)",
        "patterns": [r"\b(30|60|90)[-\s]?day", r"termination\s+of\s+tenancy",
                     r"terminate\s+your\s+tenancy", r"end\s+your\s+tenancy"],
        "plain": "Your landlord is ending the tenancy. The number of days is how long you "
                 "have before they can file in court.",
    },
}

_MONTHS = ("january february march april may june july august september october "
           "november december").split()
_DATE_PATTERNS = [
    # January 5, 2026  /  Jan 5, 2026
    (r"\b(" + "|".join(_MONTHS) + r"|" + "|".join(m[:3] for m in _MONTHS) +
     r")\.?\s+(\d{1,2}),?\s+(\d{4})\b", "monthname"),
    # 01/05/2026 or 1-5-26
    (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", "numeric"),
]
_AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_DAYS_RE = re.compile(r"\b(\d{1,3})\s*(?:\(?\s*\d*\s*\)?\s*)?day", re.I)
_BUSINESS_RE = re.compile(r"business\s+day|court\s+day|judicial\s+day", re.I)


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _parse_date(text: str) -> Optional[_dt.date]:
    for pat, kind in _DATE_PATTERNS:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        try:
            if kind == "monthname":
                mon = m.group(1).lower()[:3]
                month = next(i for i, mm in enumerate(_MONTHS, 1) if mm.startswith(mon))
                return _dt.date(int(m.group(3)), month, int(m.group(2)))
            else:
                a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
                year = c + 2000 if c < 100 else c
                return _dt.date(year, a, b)  # US M/D/Y
        except (ValueError, StopIteration):
            continue
    return None


def classify(lines: list[Line]) -> Fact:
    """R4: rule-based notice classification, citing the triggering line(s)."""
    scores: dict[str, list[str]] = {}
    for ln in lines:
        n = _norm(ln.text)
        for key, spec in NOTICE_TYPES.items():
            for pat in spec["patterns"]:
                if re.search(pat, n):
                    scores.setdefault(key, [])
                    if ln.id not in scores[key]:
                        scores[key].append(ln.id)
    if not scores:
        return Fact(key="notice_type", value="unknown", cites=[])
    best = max(scores, key=lambda k: len(scores[k]))
    return Fact(key="notice_type", value=best, cites=scores[best])


def _add_business_days(start: _dt.date, n: int) -> _dt.date:
    d, added = start, 0
    while added < n:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            added += 1
    return d


def extract_facts(lines: list[Line],
                  issue_date_hint: Optional[_dt.date] = None) -> list[Fact]:
    """R5-R7: extract deadline, amount, parties, address; compute deadline if only a
    day-count is present. Every fact cites the line it came from. Never fabricates."""
    facts: list[Fact] = [classify(lines)]

    explicit_deadline: Optional[tuple[_dt.date, str]] = None
    amount: Optional[tuple[str, str]] = None
    days: Optional[tuple[int, str, bool]] = None  # (n, line_id, business?)
    issue_date: Optional[tuple[_dt.date, str]] = None

    for ln in lines:
        n = _norm(ln.text)

        if amount is None:
            ma = _AMOUNT_RE.search(ln.text)
            if ma and ("due" in n or "owe" in n or "rent" in n or "amount" in n or "$" in ln.text):
                amount = (ma.group(0).replace(" ", ""), ln.id)

        d = _parse_date(ln.text)
        if d:
            if any(w in n for w in ("by ", "before", "no later", "deadline",
                                    "vacate", "pay", "move out", "quit")):
                if explicit_deadline is None:
                    explicit_deadline = (d, ln.id)
            if any(w in n for w in ("dated", "date of", "served", "issued", "this notice")):
                if issue_date is None:
                    issue_date = (d, ln.id)

        if days is None:
            md = _DAYS_RE.search(ln.text)
            if md:
                days = (int(md.group(1)), ln.id, bool(_BUSINESS_RE.search(ln.text)))

    # amount
    if amount:
        facts.append(Fact("amount_due", amount[0], cites=[amount[1]]))

    # deadline: prefer explicit; else compute from days + issue date (R6)
    if explicit_deadline:
        facts.append(Fact("deadline", explicit_deadline[0].isoformat(),
                          cites=[explicit_deadline[1]]))
    elif days:
        n, dline, business = days
        base = issue_date[0] if issue_date else issue_date_hint
        if base:
            end = _add_business_days(base, n) if business else base + _dt.timedelta(days=n)
            rule = (f"{n} {'business ' if business else ''}days from the notice date "
                    f"{base.isoformat()}")
            cites = [dline] + ([issue_date[1]] if issue_date else [])
            facts.append(Fact("deadline", end.isoformat(), cites=cites,
                              computed=True, rule=rule))
        else:
            # we know the count but not the start date -> be honest (R7/R10)
            facts.append(Fact("deadline_days_only", str(n), cites=[dline]))

    return facts


def analyze(lines: list[Line],
            issue_date_hint: Optional[_dt.date] = None) -> dict:
    """Top-level deterministic result. The LLM layer consumes this and may ONLY
    narrate/translate facts present here (see backend/narrate.py)."""
    facts = extract_facts(lines, issue_date_hint=issue_date_hint)
    by_key = {f.key: f for f in facts}
    nt = by_key["notice_type"].value
    nt_label = NOTICE_TYPES.get(nt, {}).get("label", "Unknown notice type")
    nt_plain = NOTICE_TYPES.get(nt, {}).get("plain",
        "We could not confidently identify this notice type. Please use free legal help "
        "to confirm what it is.")

    # "What your notice does NOT say" - honesty surface (R10/R11)
    missing = []
    if "deadline" not in by_key:
        missing.append("a clear deadline date")
    if "amount_due" not in by_key and nt == "pay_or_quit":
        missing.append("the exact amount owed")

    return {
        "notice_type": nt,
        "notice_type_label": nt_label,
        "notice_type_plain": nt_plain,
        "facts": [f.to_dict() for f in facts],
        "missing": missing,
        "lines": [asdict(l) for l in lines],
        "disclaimer": ("DueDate explains your notice and points you to free help. "
                       "It is not legal advice."),
    }
