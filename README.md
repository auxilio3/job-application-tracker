# Job Application Tracker

A full-stack web app for tracking a job search: the companies you're
interested in, the jobs they post, the applications you send, and the
people you talk to. A **Job Match** page ranks every job by how many of
its required skills you already have.

Built with **MySQL**, **Python / Flask**, and **HTML / CSS (Bootstrap 5)**.

## Features

- **Dashboard**: record counts, applications by status, response and
  interview rates, upcoming interviews, recent applications, and the
  skills employers ask for most
- **Full CRUD for all four tables** (companies, jobs, applications,
  contacts): list pages with search/filters, detail pages, add/edit forms,
  and delete with a confirmation dialog
- **Transactions for multi-step deletes**: deleting a company removes its
  applications, jobs, and contacts in one transaction, so a failure rolls
  everything back (see Assignment 4)
- **Server-side validation** on every form: required fields, lengths,
  URLs, emails, phone numbers, dates, salary ranges, and valid foreign keys
- **Interview tracking**: each application stores any number of interview
  rounds in a JSON column; the dashboard reads them with `JSON_TABLE`
- **Job Match**: enter your skills and see jobs ranked by match % with
  the skills you have and the ones you're missing

## Database design

The tables are the ones built in the course homework: **Assignment 2**
(columns and foreign keys) and **Assignment 3** (indexes). The project
spec adds two JSON columns:

| Table | Purpose | Project additions |
|---|---|---|
| `companies` | Employers | — |
| `jobs` | Postings; `company_id` → companies | `requirements` JSON array of skills, used by Job Match |
| `applications` | Applications sent; `job_id` → jobs | `interview_data` JSON array of interview rounds |
| `contacts` | Recruiters, hiring managers, referrals; `company_id` → companies | — |

Other design points:

- **Foreign keys** are the homework's plain `REFERENCES` (no cascade). The
  app deletes child rows first inside a transaction, so a company or job
  can be deleted cleanly and atomically.
- **CHECK constraints** make sure the salary minimum is ≤ the maximum and
  that both JSON columns hold arrays.
- **Indexes** from Assignment 3: `idx_job_title`, `idx_company_type`
  (composite), `idx_app_status`, and `idx_company_industry`.
- **`interview_date`** (from Assignment 2) is kept in sync automatically:
  it stores the next upcoming interview from `interview_data`, or the
  latest one if none are upcoming.
- The dashboard reads both JSON columns with MySQL's `JSON_TABLE`.

See [`schema.sql`](schema.sql).

## Setup (Windows)

### 1. Prerequisites

- Python 3.10 or newer (tick **"Add python.exe to PATH"** when installing)
- MySQL Server 8.0+ and MySQL Workbench (installed in Assignment 1)
- Git

### 2. Get the code

In a terminal (VS Code: **Ctrl + `**):

```powershell
cd ~\Documents
git clone https://github.com/auxilio3/job-application-tracker.git
cd job-application-tracker
```

### 3. Create the database (MySQL Workbench)

Open Workbench, connect to your local instance, then use
**File → Open SQL Script** and click the ⚡ button to run:

| Your situation | Run |
|---|---|
| **New computer / no job_tracker database** | `schema.sql`, then `sample_data.sql` |
| **You already built job_tracker in the homework** and want to keep it | `upgrade_homework_db.sql` only |

⚠️ `schema.sql` **drops** any existing `job_tracker` database. That's
what you want on a fresh machine, but don't run it over your homework
data.

### 4. Install the Python packages

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell says running scripts is disabled, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate
again. On macOS/Linux use `source venv/bin/activate`.

### 5. Configure the connection

```powershell
copy .env.example .env
```

Open `.env` and set `DB_PASSWORD` to your MySQL root password. `.env` is in
`.gitignore`, so the password never gets committed.

### 6. Run it

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. Press **Ctrl + C** in the terminal to stop.

### Running the tests

The unit tests cover the matching algorithm and form validation and don't
need a database:

```powershell
pytest
```

## How Job Match works

1. Your input is split on commas into a list of skills.
2. Each skill is normalized (lowercase, trimmed, extra spaces removed) and a
   few common abbreviations are expanded (`py` → `python`, `IR` →
   `incident response`, and so on).
3. For each job, **match % = required skills you have ÷ total required
   skills**, rounded to a whole percent.
4. Jobs are sorted by match %, then by number of matched skills, then by
   newest posting. Jobs where you have none of the skills, jobs that list no
   requirements, and closed postings (unless you tick "Include closed
   postings") are left out.

Example: with skills `Python, SQL, Excel`, the **Intern - Data** job
(Python, SQL, Excel) scores **100% (3/3)**, and **Data Analyst** (SQL,
Excel, Tableau, Python) scores **75% (3/4)** with *Missing: Tableau*.

The logic is in [`matching.py`](matching.py), kept separate from Flask so
it can be unit tested.

## Project structure

```
job-application-tracker/
├── app.py                   # Flask routes (dashboard, CRUD, job match)
├── database.py              # MySQL connection, query + transaction helpers
├── matching.py              # Job Match algorithm
├── validation.py            # Server-side form validation
├── schema.sql               # Builds job_tracker from scratch (homework tables + JSON)
├── sample_data.sql          # Homework data (Assignments 2-5) + skills + interviews
├── upgrade_homework_db.sql  # Adds the project columns to an existing homework DB
├── templates/
│   ├── base.html            # Layout, navbar, shared delete dialog
│   ├── macros.html          # Reusable form fields, badges, buttons
│   ├── dashboard.html
│   ├── companies.html    company_detail.html     company_form.html
│   ├── jobs.html         job_detail.html         job_form.html
│   ├── applications.html application_detail.html application_form.html
│   ├── contacts.html     contact_detail.html     contact_form.html
│   ├── job_match.html
│   └── 404.html  db_error.html
├── static/style.css
├── tests/                   # pytest unit tests
├── AI_USAGE.md              # How generative AI was used
├── requirements.txt
└── .env.example
```

## Security notes

- Every query uses parameterized placeholders (`%s`), never string
  formatting, so form input can't inject SQL (Assignment 5).
- Jinja2 auto-escapes all output, which blocks stored XSS from form fields.
- Deletes only happen through `POST` requests, so a link or page load
  can't delete data.
- Database credentials are read from environment variables, not
  hard-coded.

## AI usage

See [AI_USAGE.md](AI_USAGE.md).
