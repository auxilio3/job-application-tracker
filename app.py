"""Job Application Tracker - Flask application.

Pages:
    /                   Dashboard (statistics overview)
    /companies          Companies    - list / add / view / edit / delete
    /jobs               Jobs         - list / add / view / edit / delete
    /applications       Applications - list / add / view / edit / delete
    /contacts           Contacts     - list / add / view / edit / delete
    /match              Job Match    - rank jobs by skill match %

Uses the job_tracker tables built in Assignments 2-3, plus the two JSON
columns from the project spec (jobs.requirements, applications.interview_data).

Run with:  python app.py   (see README.md for setup)
"""

import json
import os
from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from database import execute, query_all, query_one, run_transaction
from matching import parse_skills, rank_jobs
from validation import (
    JOB_TYPES,
    STATUSES,
    parse_application_form,
    parse_company_form,
    parse_contact_form,
    parse_job_form,
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

# Statuses that mean the employer replied, and that mean you got an interview.
RESPONDED = {"Phone Screen", "Interview Scheduled", "Interview Completed",
             "Offer Received", "Offer Accepted", "Rejected"}
INTERVIEWED = {"Interview Scheduled", "Interview Completed", "Offer Received", "Offer Accepted"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(value, default=None):
    """MySQL Connector returns JSON columns as str/bytes; turn them into
    Python objects. Bad or empty values fall back to `default`."""
    if value is None or value == "":
        return default
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value


def get_or_404(sql, params):
    row = query_one(sql, params)
    if row is None:
        abort(404)
    return row


def company_choices():
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def job_choices():
    return query_all(
        """SELECT j.job_id, j.job_title, c.company_name
           FROM jobs j JOIN companies c ON c.company_id = j.company_id
           ORDER BY c.company_name, j.job_title"""
    )


def company_name_taken(name, exclude_id=None):
    """Company names should be unique (case-insensitive)."""
    row = query_one(
        "SELECT company_id FROM companies WHERE LOWER(company_name) = LOWER(%s) "
        "AND (%s IS NULL OR company_id <> %s)",
        (name, exclude_id, exclude_id),
    )
    return row is not None


def int_arg(name):
    """Read an optional integer query-string argument (?company_id=3)."""
    value = request.args.get(name, "")
    return int(value) if value.isdigit() else None


@app.template_filter("money")
def money(value):
    return f"${value:,.0f}" if value is not None else ""


@app.template_filter("nicedate")
def nicedate(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    text = value.strftime("%b %d, %Y").replace(" 0", " ")
    if isinstance(value, datetime) and (value.hour or value.minute):
        text += value.strftime(", %H:%M")
    return text


@app.template_filter("as_options")
def as_options(values):
    """Turn ["A", "B"] into [("A", "A"), ("B", "B")] for the select macro."""
    return [(v, v) for v in values]


@app.template_filter("ext_url")
def ext_url(value):
    """Homework data stores sites like 'www.example.com'; make them clickable."""
    if value and "://" not in value:
        return "https://" + value
    return value


@app.template_filter("status_group")
def status_group(status):
    """Map a status to a color group used by the CSS (status-<group>)."""
    s = (status or "").lower()
    if s.startswith("offer"):
        return "offer"
    if "interview" in s:
        return "interview"
    if "screen" in s:
        return "screening"
    if s in ("applied", "rejected", "withdrawn"):
        return s
    return "other"


SECTION_BY_PREFIX = {"company": "companies", "job": "jobs",
                     "application": "applications", "contact": "contacts"}


@app.context_processor
def inject_globals():
    # Which navbar item to highlight, e.g. "job_edit" -> "jobs".
    endpoint = request.endpoint or ""
    if endpoint in ("dashboard", "job_match"):
        section = endpoint
    else:
        section = SECTION_BY_PREFIX.get(endpoint.split("_")[0], endpoint)
    return {"STATUSES": STATUSES, "JOB_TYPES": JOB_TYPES,
            "today": date.today(), "nav_section": section}


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(MySQLError)
def database_error(error):
    app.logger.exception("Database error")
    return render_template("db_error.html", error=error), 500


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    counts = query_one(
        """SELECT
             (SELECT COUNT(*) FROM companies)                 AS companies,
             (SELECT COUNT(*) FROM jobs)                      AS jobs,
             (SELECT COUNT(*) FROM jobs WHERE is_active)      AS active_jobs,
             (SELECT COUNT(*) FROM applications)              AS applications,
             (SELECT COUNT(*) FROM contacts)                  AS contacts"""
    )

    status_rows = query_all(
        "SELECT status, COUNT(*) AS total FROM applications GROUP BY status"
    )
    by_status = {s: 0 for s in STATUSES}
    for r in status_rows:                       # keeps any non-standard statuses too
        by_status[r["status"] or "(none)"] = r["total"]

    total_apps = counts["applications"]
    responded = sum(n for s, n in by_status.items() if s in RESPONDED)
    interviewed = sum(n for s, n in by_status.items() if s in INTERVIEWED)
    rates = {
        "response": round(100 * responded / total_apps) if total_apps else 0,
        "interview": round(100 * interviewed / total_apps) if total_apps else 0,
        "avg_salary": query_one(
            "SELECT AVG((salary_min + salary_max) / 2) AS avg FROM jobs "
            "WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL")["avg"],
    }

    # JSON_TABLE turns each interview object inside interview_data into a row.
    upcoming = query_all(
        """SELECT a.application_id, j.job_title, c.company_name,
                  it.idate, it.itime, it.round_name
           FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id,
           JSON_TABLE(a.interview_data, '$[*]' COLUMNS (
               idate      DATE        PATH '$.date'  NULL ON EMPTY NULL ON ERROR,
               itime      VARCHAR(5)  PATH '$.time'  NULL ON EMPTY NULL ON ERROR,
               round_name VARCHAR(50) PATH '$.round' NULL ON EMPTY NULL ON ERROR
           )) AS it
           WHERE it.idate >= CURDATE()
           ORDER BY it.idate, it.itime
           LIMIT 5"""
    )

    # Same idea for the requirements array: which skills do jobs ask for most?
    top_skills = query_all(
        """SELECT MIN(s.skill) AS skill, COUNT(*) AS total
           FROM jobs,
           JSON_TABLE(jobs.requirements, '$[*]' COLUMNS (
               skill VARCHAR(60) PATH '$'
           )) AS s
           GROUP BY LOWER(s.skill)
           ORDER BY total DESC, skill
           LIMIT 8"""
    )

    recent = query_all(
        """SELECT a.application_id, a.application_date, a.status,
                  j.job_title, c.company_name
           FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           ORDER BY a.application_date DESC, a.application_id DESC
           LIMIT 5"""
    )

    return render_template(
        "dashboard.html", counts=counts, by_status=by_status, rates=rates,
        upcoming=upcoming, top_skills=top_skills, recent=recent,
    )


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@app.route("/companies")
def companies():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    rows = query_all(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)     AS job_count,
                  (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
           FROM companies c
           WHERE %s = '' OR c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s
           ORDER BY c.company_name""",
        (q, like, like, like),
    )
    return render_template("companies.html", companies=rows, q=q)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    jobs = query_all(
        """SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count
           FROM jobs j WHERE j.company_id = %s ORDER BY j.date_posted DESC""",
        (company_id,),
    )
    contacts = query_all(
        CONTACT_SELECT + " WHERE k.company_id = %s ORDER BY k.last_name, k.first_name",
        (company_id,),
    )
    app_count = sum(j["app_count"] for j in jobs)
    return render_template(
        "company_detail.html", company=company, jobs=jobs, contacts=contacts, app_count=app_count
    )


def company_params(data):
    return (data["company_name"], data["industry"], data["website"],
            data["city"], data["state"], data["notes"])


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    data, errors = {}, {}
    if request.method == "POST":
        data, errors = parse_company_form(request.form)
        if not errors and company_name_taken(data["company_name"]):
            errors["company_name"] = "A company with this name already exists."
        if not errors:
            new_id = execute(
                """INSERT INTO companies (company_name, industry, website, city, state, notes)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                company_params(data),
            )
            flash(f"Added {data['company_name']}.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
    return render_template("company_form.html", company=data, errors=errors, editing=False)


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    errors = {}
    if request.method == "POST":
        data, errors = parse_company_form(request.form)
        if not errors and company_name_taken(data["company_name"], company_id):
            errors["company_name"] = "A company with this name already exists."
        if not errors:
            execute(
                """UPDATE companies
                   SET company_name = %s, industry = %s, website = %s,
                       city = %s, state = %s, notes = %s
                   WHERE company_id = %s""",
                company_params(data) + (company_id,),
            )
            flash("Company updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        company = {**data, "company_id": company_id}
    return render_template("company_form.html", company=company, errors=errors, editing=True)


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = get_or_404("SELECT company_name FROM companies WHERE company_id = %s", (company_id,))
    # The homework foreign keys don't cascade, so delete children first.
    # One transaction: if any step fails, nothing is deleted.
    run_transaction([
        ("""DELETE a FROM applications a JOIN jobs j ON j.job_id = a.job_id
            WHERE j.company_id = %s""", (company_id,)),
        ("DELETE FROM jobs WHERE company_id = %s", (company_id,)),
        ("DELETE FROM contacts WHERE company_id = %s", (company_id,)),
        ("DELETE FROM companies WHERE company_id = %s", (company_id,)),
    ])
    flash(f"Deleted {company['company_name']} and everything linked to it.", "success")
    return redirect(url_for("companies"))


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

JOB_SELECT = """
    SELECT j.*, c.company_name,
           (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count
    FROM jobs j
    JOIN companies c ON c.company_id = j.company_id
"""


def with_requirements(job):
    job["requirements"] = load_json(job.get("requirements"), [])
    return job


@app.route("/jobs")
def jobs():
    q = request.args.get("q", "").strip()
    job_type = request.args.get("type", "")
    company_id = int_arg("company_id")
    show = request.args.get("show", "")            # "", "active" or "closed"
    like = f"%{q}%"
    rows = query_all(
        JOB_SELECT + """
        WHERE (%s = '' OR j.job_title LIKE %s OR c.company_name LIKE %s)
          AND (%s = '' OR j.job_type = %s)
          AND (%s IS NULL OR j.company_id = %s)
          AND (%s = '' OR (%s = 'active' AND j.is_active) OR (%s = 'closed' AND NOT j.is_active))
        ORDER BY j.date_posted DESC, j.job_id DESC""",
        (q, like, like, job_type, job_type, company_id, company_id, show, show, show),
    )
    return render_template(
        "jobs.html", jobs=[with_requirements(r) for r in rows],
        q=q, job_type=job_type, company_id=company_id, show=show, companies=company_choices(),
    )


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = with_requirements(get_or_404(JOB_SELECT + " WHERE j.job_id = %s", (job_id,)))
    applications = query_all(
        "SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC", (job_id,)
    )
    return render_template("job_detail.html", job=job, applications=applications)


def job_params(data):
    return (data["company_id"], data["job_title"], data["job_description"], data["salary_min"],
            data["salary_max"], data["job_type"], data["posting_url"], data["date_posted"],
            data["is_active"], data["requirements"])


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    companies_list = company_choices()
    if not companies_list:
        flash("Add a company first. Every job belongs to a company.", "warning")
        return redirect(url_for("company_new"))
    data, errors = {"company_id": int_arg("company_id"), "is_active": True}, {}
    if request.method == "POST":
        data, errors = parse_job_form(request.form, {c["company_id"] for c in companies_list})
        if not errors:
            new_id = execute(
                """INSERT INTO jobs (company_id, job_title, job_description, salary_min, salary_max,
                                     job_type, posting_url, date_posted, is_active, requirements)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                job_params(data),
            )
            flash(f"Added {data['job_title']}.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
    return render_template("job_form.html", job=data, errors=errors,
                           companies=companies_list, editing=False)


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = with_requirements(get_or_404("SELECT * FROM jobs WHERE job_id = %s", (job_id,)))
    job["requirements_text"] = ", ".join(job["requirements"])
    current_type = job["job_type"]
    companies_list = company_choices()
    errors = {}
    if request.method == "POST":
        data, errors = parse_job_form(request.form, {c["company_id"] for c in companies_list},
                                      current_type=current_type)
        if not errors:
            execute(
                """UPDATE jobs
                   SET company_id = %s, job_title = %s, job_description = %s, salary_min = %s,
                       salary_max = %s, job_type = %s, posting_url = %s, date_posted = %s,
                       is_active = %s, requirements = %s
                   WHERE job_id = %s""",
                job_params(data) + (job_id,),
            )
            flash("Job updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        job = {**data, "job_id": job_id}
    return render_template("job_form.html", job=job, errors=errors, current_type=current_type,
                           companies=companies_list, editing=True)


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = get_or_404("SELECT job_title FROM jobs WHERE job_id = %s", (job_id,))
    run_transaction([
        ("DELETE FROM applications WHERE job_id = %s", (job_id,)),
        ("DELETE FROM jobs WHERE job_id = %s", (job_id,)),
    ])
    flash(f"Deleted {job['job_title']}.", "success")
    return redirect(url_for("jobs"))


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

APP_SELECT = """
    SELECT a.*, j.job_title, j.company_id, c.company_name
    FROM applications a
    JOIN jobs j      ON j.job_id = a.job_id
    JOIN companies c ON c.company_id = j.company_id
"""


def with_interviews(application):
    application["interviews"] = load_json(application.get("interview_data"), [])
    return application


@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    rows = query_all(
        APP_SELECT + """
        WHERE (%s = '' OR a.status = %s)
        ORDER BY a.application_date DESC, a.application_id DESC""",
        (status, status),
    )
    # Filter buttons: the standard statuses plus any others found in the data.
    extra = [r["status"] for r in query_all("SELECT DISTINCT status FROM applications")
             if r["status"] and r["status"] not in STATUSES]
    return render_template(
        "applications.html", applications=[with_interviews(r) for r in rows],
        status=status, status_filters=STATUSES + sorted(extra),
    )


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = with_interviews(
        get_or_404(APP_SELECT + " WHERE a.application_id = %s", (application_id,))
    )
    contacts = query_all(
        CONTACT_SELECT + " WHERE k.company_id = %s ORDER BY k.last_name, k.first_name",
        (application["company_id"],),
    )
    return render_template("application_detail.html", application=application, contacts=contacts)


def application_params(data):
    return (data["job_id"], data["application_date"], data["status"], data["resume_version"],
            data["cover_letter_sent"], data["response_date"], data["interview_date"],
            data["notes"], data["interview_data"])


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    jobs_list = job_choices()
    if not jobs_list:
        flash("Add a job first. Every application is for a specific job.", "warning")
        return redirect(url_for("job_new"))
    data = {"job_id": int_arg("job_id"), "application_date": date.today(),
            "status": "Applied", "interviews": []}
    errors = {}
    if request.method == "POST":
        data, errors = parse_application_form(request.form, {j["job_id"] for j in jobs_list})
        if not errors:
            new_id = execute(
                """INSERT INTO applications (job_id, application_date, status, resume_version,
                                             cover_letter_sent, response_date, interview_date,
                                             notes, interview_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                application_params(data),
            )
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
    return render_template("application_form.html", application=data, errors=errors,
                           jobs=jobs_list, editing=False, current_status=None)


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    application = with_interviews(
        get_or_404("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    )
    current_status = application["status"]
    jobs_list = job_choices()
    errors = {}
    if request.method == "POST":
        data, errors = parse_application_form(request.form, {j["job_id"] for j in jobs_list},
                                              current_status=current_status)
        if not errors:
            execute(
                """UPDATE applications
                   SET job_id = %s, application_date = %s, status = %s, resume_version = %s,
                       cover_letter_sent = %s, response_date = %s, interview_date = %s,
                       notes = %s, interview_data = %s
                   WHERE application_id = %s""",
                application_params(data) + (application_id,),
            )
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        application = {**data, "application_id": application_id}
    return render_template("application_form.html", application=application, errors=errors,
                           jobs=jobs_list, editing=True, current_status=current_status)


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    get_or_404("SELECT application_id FROM applications WHERE application_id = %s",
               (application_id,))
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

CONTACT_SELECT = """
    SELECT k.*, CONCAT(k.first_name, ' ', k.last_name) AS contact_name, c.company_name
    FROM contacts k
    JOIN companies c ON c.company_id = k.company_id
"""


@app.route("/contacts")
def contacts():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    rows = query_all(
        CONTACT_SELECT + """
        WHERE %s = ''
           OR CONCAT(k.first_name, ' ', k.last_name) LIKE %s
           OR k.job_title LIKE %s
           OR c.company_name LIKE %s
        ORDER BY k.last_name, k.first_name""",
        (q, like, like, like),
    )
    return render_template("contacts.html", contacts=rows, q=q)


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = get_or_404(CONTACT_SELECT + " WHERE k.contact_id = %s", (contact_id,))
    return render_template("contact_detail.html", contact=contact)


def contact_params(data):
    return (data["company_id"], data["first_name"], data["last_name"], data["email"],
            data["phone"], data["job_title"], data["linkedin_url"], data["notes"])


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    companies_list = company_choices()
    if not companies_list:
        flash("Add a company first. Every contact belongs to a company.", "warning")
        return redirect(url_for("company_new"))
    data, errors = {"company_id": int_arg("company_id")}, {}
    if request.method == "POST":
        data, errors = parse_contact_form(request.form, {c["company_id"] for c in companies_list})
        if not errors:
            new_id = execute(
                """INSERT INTO contacts (company_id, first_name, last_name, email, phone,
                                         job_title, linkedin_url, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                contact_params(data),
            )
            flash(f"Added {data['first_name']} {data['last_name']}.", "success")
            return redirect(url_for("contact_detail", contact_id=new_id))
    return render_template("contact_form.html", contact=data, errors=errors,
                           companies=companies_list, editing=False)


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404(CONTACT_SELECT + " WHERE k.contact_id = %s", (contact_id,))
    companies_list = company_choices()
    errors = {}
    if request.method == "POST":
        data, errors = parse_contact_form(request.form, {c["company_id"] for c in companies_list})
        if not errors:
            execute(
                """UPDATE contacts
                   SET company_id = %s, first_name = %s, last_name = %s, email = %s,
                       phone = %s, job_title = %s, linkedin_url = %s, notes = %s
                   WHERE contact_id = %s""",
                contact_params(data) + (contact_id,),
            )
            flash("Contact updated.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        contact = {**data, "contact_id": contact_id,
                   "contact_name": contact["contact_name"]}
    return render_template("contact_form.html", contact=contact, errors=errors,
                           companies=companies_list, editing=True)


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = get_or_404(CONTACT_SELECT + " WHERE k.contact_id = %s", (contact_id,))
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    flash(f"Deleted {contact['contact_name']}.", "success")
    return redirect(url_for("contacts"))


# ---------------------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------------------

@app.route("/match")
def job_match():
    skills_text = request.args.get("skills", "")
    skills = parse_skills(skills_text)
    min_percent = request.args.get("min", "0")
    min_percent = int(min_percent) if min_percent.isdigit() else 0
    job_type = request.args.get("type", "")
    include_closed = request.args.get("closed") == "1"

    results, unscored = None, 0
    if skills:
        rows = query_all(
            """SELECT j.job_id, j.job_title, j.job_type, j.salary_min, j.salary_max,
                      j.date_posted, j.is_active, j.requirements, c.company_name,
                      EXISTS (SELECT 1 FROM applications a WHERE a.job_id = j.job_id) AS applied
               FROM jobs j
               JOIN companies c ON c.company_id = j.company_id
               WHERE (%s = '' OR j.job_type = %s)
                 AND (%s OR j.is_active)""",
            (job_type, job_type, include_closed),
        )
        jobs_list = [with_requirements(r) for r in rows]
        unscored = sum(1 for j in jobs_list if not j["requirements"])
        results = rank_jobs(skills, jobs_list, min_percent=min_percent)

    return render_template(
        "job_match.html", skills_text=skills_text, skills=skills, results=results,
        min_percent=min_percent, job_type=job_type, include_closed=include_closed,
        unscored=unscored,
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
