"""Skill-matching logic for the Job Match page.

Match % for a job = (required skills the user has) / (required skills).
Skills are compared case-insensitively after normalizing spacing and a
few common abbreviations, so "python", " Python " and "py" all match.

This module has no database or Flask code in it, so it can be unit
tested on its own (see tests/test_matching.py).
"""

import re

# Common shorthand -> the canonical name used in job requirements.
# Keys and values are already in normalized (lowercase) form.
ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "ir": "incident response",
    "incident handling": "incident response",
    "nist": "nist csf",
    "re": "reverse engineering",
}


def normalize_skill(skill):
    """Lowercase, trim, collapse inner whitespace, and apply aliases."""
    cleaned = re.sub(r"\s+", " ", str(skill)).strip().lower()
    return ALIASES.get(cleaned, cleaned)


def parse_skills(text):
    """Split a comma/semicolon/newline separated string into a list of
    unique skills, keeping the user's original spelling and order."""
    seen = set()
    skills = []
    for piece in re.split(r"[,;\n]", text or ""):
        piece = re.sub(r"\s+", " ", piece).strip()
        key = normalize_skill(piece)
        if piece and key not in seen:
            seen.add(key)
            skills.append(piece)
    return skills


def match_job(user_skills, required_skills):
    """Compare one job's requirements against the user's skills.

    Returns a dict with the matched and missing requirement names (in the
    job's own spelling), the counts, and the match percentage (0-100).
    Returns None when the job lists no requirements, since a percentage
    would be meaningless.
    """
    if not required_skills:
        return None

    user_set = {normalize_skill(s) for s in user_skills}
    matched, missing = [], []
    seen = set()
    for req in required_skills:
        key = normalize_skill(req)
        if not key or key in seen:  # skip blanks / duplicate requirements
            continue
        seen.add(key)
        (matched if key in user_set else missing).append(req)

    total = len(matched) + len(missing)
    if total == 0:
        return None
    return {
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total": total,
        "percent": round(100 * len(matched) / total),
    }


def rank_jobs(user_skills, jobs, min_percent=0):
    """Score every job and return those at or above min_percent, best first.
    Jobs where the user has none of the required skills are left out.

    `jobs` is a list of dicts that each have a "requirements" list (plus
    any other columns, which are passed through untouched). Ties are
    broken by number of matched skills, then by most recent posting.
    """
    results = []
    for job in jobs:
        score = match_job(user_skills, job.get("requirements") or [])
        if score is None or score["percent"] < min_percent:
            continue
        if score["matched_count"] == 0:  # no overlap at all: not a match
            continue
        results.append({**job, **score})

    results.sort(key=lambda r: str(r.get("date_posted") or ""), reverse=True)
    results.sort(key=lambda r: (r["percent"], r["matched_count"]), reverse=True)
    return results
