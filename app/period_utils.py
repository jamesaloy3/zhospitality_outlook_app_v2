from __future__ import annotations
from datetime import date

SEASON_WINDOWS = {
    "Q1": (4,5),   # Apr-May
    "Q2": (7,8),   # Jul-Aug
    "Q3": (10,11), # Oct-Nov
    "Q4": (1,2)    # Jan-Feb (prior fiscal Q4 reporting period)
}

def nearest_quarter_season(today: date | None = None) -> tuple[str,int]:
    d = today or date.today()
    y = d.year
    m = d.month
    best = None
    best_dist = 999
    for q, (m1, m2) in SEASON_WINDOWS.items():
        year_for_q = y if q in {"Q1","Q2","Q3"} else y-1
        midpoint = (m1 + m2)/2.0
        dist = abs(m - midpoint)
        if dist < best_dist:
            best_dist = dist
            best = (q, year_for_q)
    return best

def compose_period_string(quarter: str | None, month: int | None, year: int | None) -> str:
    if quarter and year:
        q = quarter.upper().replace(" ", "").replace("-", "")
        if not q.startswith("Q"):
            q = "Q" + q
        return f"{q} {year}"
    if month and year:
        return f"{year}-{int(month):02d}"
    q, y = nearest_quarter_season()
    return f"{q} {y}"
