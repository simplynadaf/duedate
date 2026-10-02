"""
Trust-contract tests. These PROVE the mic-drop claims (spec R4-R7, R10):
facts are never invented, deadlines are either present or honestly computed, and the
engine refuses to supply a deadline it cannot ground.
Run: python3 -m pytest tests/ -v   (or: python3 tests/test_engine.py)
"""
import datetime as dt
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from engine import Line, analyze, classify, extract_facts  # noqa: E402


def L(i, t):
    return Line(id=f"L{i}", text=t)


# A realistic 3-day pay-or-quit notice (California style).
PAY_OR_QUIT = [
    L(1, "THREE-DAY NOTICE TO PAY RENT OR QUIT"),
    L(2, "To: Maria Gomez, Tenant in possession"),
    L(3, "Property: 1420 Oak Street, Apt 3B, Los Angeles, CA 90011"),
    L(4, "YOU ARE HEREBY NOTIFIED that rent is now due and payable on the premises."),
    L(5, "The total amount due is $2,450.00."),
    L(6, "You must pay the amount due within THREE (3) days or quit and deliver possession."),
    L(7, "This notice is dated January 6, 2026."),
]


def test_classifies_pay_or_quit_with_citation():
    f = classify(PAY_OR_QUIT)
    assert f.value == "pay_or_quit"
    assert f.cites, "classification must cite the line(s) that triggered it"
    assert "L1" in f.cites or "L6" in f.cites


def test_extracts_amount_only_when_present_and_cited():
    facts = {f.key: f for f in extract_facts(PAY_OR_QUIT)}
    assert facts["amount_due"].value == "$2,450.00"
    assert facts["amount_due"].cites == ["L5"]


def test_computes_deadline_from_days_and_marks_it_computed():
    facts = {f.key: f for f in extract_facts(PAY_OR_QUIT)}
    d = facts["deadline"]
    # 3 days from Jan 6 2026 = Jan 9 2026 (calendar days; notice did not say business days)
    assert d.value == dt.date(2026, 1, 9).isoformat()
    assert d.computed is True
    assert d.rule and "notice date" in d.rule
    assert "L6" in d.cites  # the "within 3 days" line


def test_R7_never_invents_a_date_absent_from_the_notice():
    # No day-count, no deadline, no issue date -> engine must NOT produce a deadline.
    vague = [
        L(1, "NOTICE TO PAY RENT OR QUIT"),
        L(2, "Rent is overdue. Please contact the office."),
    ]
    keys = {f.key for f in extract_facts(vague)}
    assert "deadline" not in keys, "must not fabricate a deadline that is not in the notice"


def test_R10_refuses_when_only_a_day_count_but_no_start_date():
    # "within 5 days" but no notice date and no hint -> honest 'days only', not a guess.
    partial = [
        L(1, "CURE OR QUIT NOTICE"),
        L(2, "You must correct the violation within 5 days."),
    ]
    facts = {f.key: f for f in extract_facts(partial)}
    assert "deadline" not in facts
    assert facts.get("deadline_days_only") and facts["deadline_days_only"].value == "5"


def test_unknown_notice_is_honest_not_guessed():
    f = classify([L(1, "Dear resident, your parking permit expires soon.")])
    assert f.value == "unknown"
    assert f.cites == []


def test_analyze_surfaces_missing_fields():
    vague = [L(1, "NOTICE TO PAY RENT OR QUIT"), L(2, "Rent is overdue.")]
    out = analyze(vague)
    assert "a clear deadline date" in out["missing"]
    assert out["disclaimer"].endswith("not legal advice.")


def test_every_fact_has_a_citation_or_is_explicitly_absent():
    out = analyze(PAY_OR_QUIT)
    for f in out["facts"]:
        if f["key"] in ("notice_type",) and f["value"] == "unknown":
            continue
        assert f["cites"], f"fact {f['key']} must cite a line (trust contract R12)"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); passed += 1
        except Exception:
            print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
