def _score_flood(zone):
    if not zone: return 0
    z = str(zone).upper()
    if z.startswith("A"): return 40
    if z.startswith("X"): return 15
    return 0

def _score_fire(h):
    if not h: return 0
    s = str(h).lower()
    if "very" in s: return 30
    if "high" in s: return 20
    if "moderate" in s: return 10
    return 0

def _score_quake(p):
    if p is None: return 0
    if p >= 0.35: return 25
    if p >= 0.20: return 15
    return 0

def _score_storm(n):
    if n >= 5: return 10
    if n >= 2: return 5
    return 0

def rule_score(row: dict) -> int:
    return (_score_flood(row.get("fema_zone")) +
            _score_fire(row.get("fire_class")) +
            _score_quake(row.get("pga_g")) +
            _score_storm(row.get("storm_count_5km", 0)))

def label_from_score(s: int) -> str:
    if s < 25: return "Low"
    if s < 45: return "Moderate"
    if s < 65: return "High"
    return "Very High"
