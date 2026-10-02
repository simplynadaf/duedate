"""
Free legal-aid routing (spec R13). Real, well-known national entry points plus a
jurisdiction hook. We route to REAL help and never pretend to be it. Minimal by design;
expandable without code changes.
"""

# National, free, verifiable entry points (US).
NATIONAL = [
    {"name": "LawHelp.org - find free legal aid near you",
     "url": "https://www.lawhelp.org/find-help", "scope": "national"},
    {"name": "Legal Services Corporation - find a local LSC-funded aid office",
     "url": "https://www.lsc.gov/about-lsc/what-legal-aid/get-legal-help",
     "scope": "national"},
    {"name": "211 - call 211 for local housing and legal referrals",
     "url": "https://www.211.org/", "scope": "national"},
]

# Optional state hooks (demo scope). Add states without touching app code.
STATE = {
    "CA": [{"name": "California Courts Self-Help - Eviction",
            "url": "https://selfhelp.courts.ca.gov/eviction", "scope": "CA"}],
    "NY": [{"name": "New York Right to Counsel / Housing Court Answers",
            "url": "https://www.housingcourtanswers.org/", "scope": "NY"}],
    "WA": [{"name": "WashingtonLawHelp - Eviction and Your Defense",
            "url": "https://www.washingtonlawhelp.org/", "scope": "WA"}],
}


def resources_for(state: str | None = None) -> list[dict]:
    out = list(NATIONAL)
    if state and state.upper() in STATE:
        out = STATE[state.upper()] + out
    return out
