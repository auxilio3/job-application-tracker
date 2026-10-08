"""Unit tests for form validation. These don't need a database."""

import json
from datetime import datetime

from werkzeug.datastructures import MultiDict

from validation import (
    key_interview_datetime,
    parse_application_form,
    parse_company_form,
    parse_contact_form,
    parse_job_form,
)


def test_company_requires_name_and_valid_website():
    data, errors = parse_company_form(MultiDict({"company_name": " ", "website": "not a site"}))
    assert "company_name" in errors
    assert "website" in errors


def test_company_accepts_homework_style_website():
    # Assignment 2 stores websites without https://
    data, errors = parse_company_form(MultiDict({"company_name": "Acme", "website": "www.acme.com",
                                                 "city": "  "}))
    assert errors == {}
    assert data["website"] == "www.acme.com"
    assert data["city"] is None


def test_job_salary_range_and_requirements_json():
    form = MultiDict({
        "company_id": "1", "job_title": "Analyst", "salary_min": "$70,000",
        "salary_max": "60000", "requirements": "Python, SQL, python", "is_active": "on",
    })
    data, errors = parse_job_form(form, company_ids={1})
    assert data["salary_min"] == 70000
    assert "salary_max" in errors                      # max < min
    assert json.loads(data["requirements"]) == ["Python", "SQL"]
    assert data["is_active"] is True


def test_job_rejects_unknown_company_and_type_but_keeps_existing_type():
    form = MultiDict({"company_id": "42", "job_title": "X", "job_type": "Freelance"})
    _, errors = parse_job_form(form, company_ids={1, 2})
    assert "company_id" in errors and "job_type" in errors
    # A job that already had a non-standard type can be saved unchanged.
    form = MultiDict({"company_id": "1", "job_title": "X", "job_type": "Freelance"})
    _, errors = parse_job_form(form, company_ids={1}, current_type="Freelance")
    assert errors == {}


def test_application_interviews_parsed_and_blank_rows_skipped():
    form = MultiDict([
        ("job_id", "3"), ("application_date", "2025-01-13"), ("status", "Interview Scheduled"),
        ("interview_date", "2025-01-20"), ("interview_time", "14:00"),
        ("interview_round", "Technical"), ("interview_interviewer", "Michael"), ("interview_notes", ""),
        ("interview_date", ""), ("interview_time", ""),
        ("interview_round", ""), ("interview_interviewer", ""), ("interview_notes", ""),
    ])
    data, errors = parse_application_form(form, job_ids={3})
    assert errors == {}
    interviews = json.loads(data["interview_data"])
    assert len(interviews) == 1 and interviews[0]["round"] == "Technical"
    assert data["interview_date"] == datetime(2025, 1, 20, 14, 0)
    assert data["cover_letter_sent"] is False


def test_application_rejects_future_date_bad_status_and_early_response():
    form = MultiDict({"job_id": "3", "application_date": "2999-01-01", "status": "Ghosted"})
    _, errors = parse_application_form(form, job_ids={3})
    assert "application_date" in errors and "status" in errors

    form = MultiDict({"job_id": "3", "application_date": "2025-01-10", "status": "Applied",
                      "response_date": "2025-01-05"})
    _, errors = parse_application_form(form, job_ids={3})
    assert "response_date" in errors


def test_key_interview_prefers_next_upcoming_then_latest():
    rows = [{"date": "2025-01-10", "time": "09:00"},
            {"date": "2025-03-01", "time": ""},
            {"date": "2025-02-01", "time": "13:30"}]
    assert key_interview_datetime(rows, now=datetime(2025, 1, 15)) == datetime(2025, 2, 1, 13, 30)
    assert key_interview_datetime(rows, now=datetime(2026, 1, 1)) == datetime(2025, 3, 1, 0, 0)
    assert key_interview_datetime([]) is None


def test_contact_requires_names_and_company():
    form = MultiDict({"first_name": "", "last_name": "", "email": "sam@", "phone": "call me",
                      "company_id": ""})
    _, errors = parse_contact_form(form, company_ids={1})
    for field in ("first_name", "last_name", "email", "phone", "company_id"):
        assert field in errors
