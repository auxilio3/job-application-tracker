"""Server-side form validation.

Every form is checked here before anything touches the database. The
browser also does basic checks (required, type="email", etc.), but those
can be bypassed, so the server never trusts them.

Each parse_* function takes request.form and returns (data, errors):
  data   - dict of cleaned values ready to insert (None for blank optionals)
  errors - dict of field name -> message; empty means the form is valid

Field names and lengths match the homework tables (Assignment 2).
"""

import json
import re
from datetime import date, datetime
from urllib.parse import urlparse

from matching import parse_skills

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]

# The status values used in Assignments 2-5, in pipeline order.
STATUSES = [
    "Applied",
    "Phone Screen",
    "Interview Scheduled",
    "Interview Completed",
    "Offer Received",
    "Offer Accepted",
    "Rejected",
    "Withdrawn",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+()\-.\s xext]{7,20}$", re.IGNORECASE)
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
# Homework data stores websites like "www.techsolutions.com", so a scheme
# is optional; anything with a dot in the host name is accepted.
HOST_RE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(:\d+)?$")


class Form:
    """Small helper that collects cleaned values and errors for one form."""

    def __init__(self, form):
        self.form = form
        self.data = {}
        self.errors = {}

    def raw(self, name):
        return (self.form.get(name) or "").strip()

    def text(self, name, label, max_len, required=False):
        value = self.raw(name)
        if not value:
            if required:
                self.errors[name] = f"{label} is required."
            self.data[name] = None
        elif len(value) > max_len:
            self.errors[name] = f"{label} must be {max_len} characters or fewer."
            self.data[name] = value
        else:
            self.data[name] = value
        return self.data[name]

    def url(self, name, label, max_len):
        value = self.text(name, label, max_len)
        if value and name not in self.errors:
            parsed = urlparse(value if "://" in value else "http://" + value)
            if parsed.scheme not in ("http", "https") or not HOST_RE.match(parsed.netloc):
                self.errors[name] = f"{label} must be a web address like www.example.com."
        return value

    def email(self, name, label, max_len):
        value = self.text(name, label, max_len)
        if value and name not in self.errors and not EMAIL_RE.match(value):
            self.errors[name] = f"{label} doesn't look like a valid email address."
        return value

    def phone(self, name, label, max_len):
        value = self.text(name, label, max_len)
        if value and name not in self.errors and not PHONE_RE.match(value):
            self.errors[name] = f"{label} can only contain digits, spaces, and + ( ) - ."
        return value

    def money(self, name, label, maximum=99_999_999):
        """Salary: whole dollars, commas and $ allowed (fits DECIMAL(10,2))."""
        value = self.raw(name).replace(",", "").replace("$", "")
        if not value:
            self.data[name] = None
            return None
        try:
            number = float(value)
        except ValueError:
            self.errors[name] = f"{label} must be a number."
            self.data[name] = value
            return None
        if not 0 <= number <= maximum:
            self.errors[name] = f"{label} must be between 0 and {maximum:,}."
        self.data[name] = round(number, 2)
        return self.data[name]

    def date(self, name, label, required=False, allow_future=True):
        value = self.raw(name)
        if not value:
            if required:
                self.errors[name] = f"{label} is required."
            self.data[name] = None
            return None
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            self.errors[name] = f"{label} must be a valid date (YYYY-MM-DD)."
            self.data[name] = value
            return None
        if not allow_future and parsed > date.today():
            self.errors[name] = f"{label} can't be in the future."
        self.data[name] = parsed
        return parsed

    def choice(self, name, label, options, required=False, keep=None):
        """A value from a fixed list. `keep` lets an existing value that is
        not in the list (e.g. older homework data) be saved unchanged."""
        value = self.raw(name)
        if not value:
            if required:
                self.errors[name] = f"{label} is required."
            self.data[name] = None
        elif value not in options and value != keep:
            self.errors[name] = f"{label} must be one of: {', '.join(options)}."
            self.data[name] = None
        else:
            self.data[name] = value
        return self.data[name]

    def foreign_key(self, name, label, valid_ids, required=False):
        value = self.raw(name)
        if not value:
            if required:
                self.errors[name] = f"Please choose a {label.lower()}."
            self.data[name] = None
            return None
        try:
            fk = int(value)
        except ValueError:
            fk = None
        if fk not in valid_ids:
            self.errors[name] = f"Please choose a valid {label.lower()}."
            self.data[name] = None
            return None
        self.data[name] = fk
        return fk

    def checkbox(self, name):
        self.data[name] = self.form.get(name) in ("on", "1", "true", "yes")
        return self.data[name]


def parse_company_form(form):
    f = Form(form)
    f.text("company_name", "Company name", 100, required=True)
    f.text("industry", "Industry", 50)
    f.url("website", "Website", 200)
    f.text("city", "City", 50)
    f.text("state", "State", 50)
    f.text("notes", "Notes", 5000)
    return f.data, f.errors


def parse_job_form(form, company_ids, current_type=None):
    f = Form(form)
    f.foreign_key("company_id", "Company", company_ids, required=True)
    f.text("job_title", "Job title", 100, required=True)
    f.text("job_description", "Job description", 10000)
    f.choice("job_type", "Job type", JOB_TYPES, keep=current_type)
    low = f.money("salary_min", "Minimum salary")
    high = f.money("salary_max", "Maximum salary")
    if low is not None and high is not None and low > high:
        f.errors["salary_max"] = "Maximum salary can't be lower than the minimum."
    f.url("posting_url", "Posting URL", 500)
    f.date("date_posted", "Date posted")
    f.checkbox("is_active")

    raw_skills = f.raw("requirements")
    skills = parse_skills(raw_skills)
    if any(len(s) > 60 for s in skills):
        f.errors["requirements"] = "Each skill must be 60 characters or fewer."
    f.data["requirements_text"] = raw_skills          # to refill the form
    f.data["requirements"] = json.dumps(skills) if skills else None
    return f.data, f.errors


def parse_application_form(form, job_ids, current_status=None):
    f = Form(form)
    f.foreign_key("job_id", "Job", job_ids, required=True)
    applied = f.date("application_date", "Application date", required=True, allow_future=False)
    f.choice("status", "Status", STATUSES, required=True, keep=current_status)
    f.text("resume_version", "Resume version", 50)
    f.checkbox("cover_letter_sent")
    responded = f.date("response_date", "Response date", allow_future=False)
    if (isinstance(applied, date) and isinstance(responded, date)
            and responded < applied):
        f.errors["response_date"] = "Response date can't be before the application date."
    f.text("notes", "Notes", 5000)

    interviews, interview_errors = parse_interviews(form)
    if interview_errors:
        f.errors["interview_data"] = " ".join(interview_errors)
    f.data["interviews"] = interviews                  # to refill the form
    f.data["interview_data"] = json.dumps(interviews) if interviews else None
    f.data["interview_date"] = key_interview_datetime(interviews)
    return f.data, f.errors


def parse_interviews(form):
    """Read the repeating interview rows (parallel lists of inputs) into a
    list of dicts, skipping rows that were left completely blank."""
    columns = {
        "date": form.getlist("interview_date"),
        "time": form.getlist("interview_time"),
        "round": form.getlist("interview_round"),
        "interviewer": form.getlist("interview_interviewer"),
        "notes": form.getlist("interview_notes"),
    }
    row_count = max((len(v) for v in columns.values()), default=0)
    interviews, errors = [], []
    for i in range(row_count):
        row = {key: (values[i].strip() if i < len(values) else "")
               for key, values in columns.items()}
        if not any(row.values()):
            continue
        n = len(interviews) + 1
        if not row["date"]:
            errors.append(f"Interview {n} needs a date.")
        else:
            try:
                datetime.strptime(row["date"], "%Y-%m-%d")
            except ValueError:
                errors.append(f"Interview {n} has an invalid date.")
        if row["time"] and not TIME_RE.match(row["time"]):
            errors.append(f"Interview {n} time must be HH:MM.")
        if len(row["round"]) > 50 or len(row["interviewer"]) > 100 or len(row["notes"]) > 1000:
            errors.append(f"Interview {n} has a field that is too long.")
        interviews.append(row)
    interviews.sort(key=lambda r: (r["date"], r["time"]))
    return interviews, errors


def key_interview_datetime(interviews, now=None):
    """Value for the homework's applications.interview_date column: the next
    upcoming interview, or the most recent one if none are upcoming."""
    now = now or datetime.now()
    moments = []
    for row in interviews:
        try:
            moments.append(datetime.strptime(
                f"{row['date']} {row.get('time') or '00:00'}", "%Y-%m-%d %H:%M"))
        except (ValueError, KeyError):
            continue
    if not moments:
        return None
    upcoming = [m for m in moments if m >= now]
    return min(upcoming) if upcoming else max(moments)


def parse_contact_form(form, company_ids):
    f = Form(form)
    f.foreign_key("company_id", "Company", company_ids, required=True)
    f.text("first_name", "First name", 50, required=True)
    f.text("last_name", "Last name", 50, required=True)
    f.text("job_title", "Job title", 100)
    f.email("email", "Email", 100)
    f.phone("phone", "Phone", 20)
    f.url("linkedin_url", "LinkedIn URL", 200)
    f.text("notes", "Notes", 5000)
    return f.data, f.errors
