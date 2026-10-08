"""Unit tests for the Job Match algorithm. Run with:  pytest"""

from matching import match_job, normalize_skill, parse_skills, rank_jobs


def test_normalize_ignores_case_spacing_and_aliases():
    assert normalize_skill("  Python ") == "python"
    assert normalize_skill("Incident   Response") == "incident response"
    assert normalize_skill("py") == "python"
    assert normalize_skill("JS") == "javascript"


def test_parse_skills_splits_and_dedupes():
    assert parse_skills("Python, SQL;flask\n python ,, ") == ["Python", "SQL", "flask"]
    assert parse_skills("") == []
    assert parse_skills(None) == []


def test_spec_example():
    """The example from the project spec: Python, SQL, Flask."""
    user = ["Python", "SQL", "Flask"]
    jobs = [
        {"job_title": "Data Analyst", "requirements": ["Python", "SQL", "Tableau"]},
        {"job_title": "Software Developer", "requirements": ["Python", "SQL", "Flask"]},
    ]
    ranked = rank_jobs(user, jobs)
    assert [r["job_title"] for r in ranked] == ["Software Developer", "Data Analyst"]
    assert ranked[0]["percent"] == 100 and ranked[0]["matched_count"] == 3
    assert ranked[1]["percent"] == 67 and ranked[1]["missing"] == ["Tableau"]


def test_match_is_case_insensitive_and_keeps_job_spelling():
    result = match_job(["splunk", "LINUX"], ["Splunk", "Linux", "SIEM"])
    assert result["matched"] == ["Splunk", "Linux"]
    assert result["missing"] == ["SIEM"]
    assert result["percent"] == 67


def test_duplicate_requirements_count_once():
    result = match_job(["Python"], ["Python", "python", "SQL"])
    assert result["total"] == 2
    assert result["percent"] == 50


def test_job_without_requirements_is_skipped():
    assert match_job(["Python"], []) is None
    assert match_job(["Python"], None) is None
    assert rank_jobs(["Python"], [{"job_title": "Mystery", "requirements": []}]) == []


def test_min_percent_filter():
    jobs = [
        {"job_title": "A", "requirements": ["Python"]},
        {"job_title": "B", "requirements": ["Python", "C++", "Go", "Rust"]},
    ]
    assert [r["job_title"] for r in rank_jobs(["python"], jobs, min_percent=50)] == ["A"]


def test_zero_overlap_jobs_are_not_listed():
    jobs = [{"job_title": "Unrelated", "requirements": ["HIPAA", "Auditing"]}]
    assert rank_jobs(["Python"], jobs) == []


def test_ties_prefer_more_matches_then_newest():
    jobs = [
        {"job_title": "Old", "requirements": ["SQL", "Excel"], "date_posted": "2026-01-01"},
        {"job_title": "New", "requirements": ["SQL", "Excel"], "date_posted": "2026-09-01"},
        {"job_title": "Bigger", "requirements": ["SQL", "Excel", "Python", "Go"], "date_posted": "2025-01-01"},
    ]
    ranked = rank_jobs(["SQL", "Python"], jobs)
    # All three are 50%; Bigger matches 2 skills so it wins, then newest first.
    assert [r["job_title"] for r in ranked] == ["Bigger", "New", "Old"]
