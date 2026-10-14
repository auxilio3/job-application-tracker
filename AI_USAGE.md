# AI Usage Documentation

## Tools Used

- **Claude (Anthropic, model claude-opus-5-5)**: generated the first full
  version of the application from the project spec: the schema, Flask
  routes, validation, templates, Job Match algorithm, tests, and README.
  It also tested the app against a real MySQL 8 server and fixed the bugs
  it found. I also used it to walk me through setup step by step: MySQL
  Workbench, the Python virtual environment, and Git.

## Key Prompts

1. Uploaded the project specification document and asked: *"going to need
   your help w this i alr have a public github w some things."* Then
   shared the repo link.
2. Chose **"Build it all, I'll review"** when Claude asked how much it
   should build, and **"Send me files, I commit"** for how code gets to
   GitHub.
3. Uploaded Assignments 1-5 and said: *"the project instructions say to
   use the schema tables from our hw."* Claude then rebuilt the schema,
   app, and sample data around the Assignment 2 tables.
4. Asked why my project structure looked different from the instructor's.
   Claude explained that every required file was there, plus extra files
   for detail pages, forms, validation, and tests.
5. Asked whether `404.html` and `db_error.html` were needed, since they
   weren't in the instructor's structure. They are: `app.py` uses them for
   error pages.
6. Pointed out that `README.md` was missing from the project structure list
   inside the README, and had it added.
7. Setup questions, such as why the ⚡ button in Workbench was greyed out
   (I wasn't connected to the server yet) and why `schema.sql` couldn't be
   found (Workbench was showing a different Documents folder).

## What Worked Well

- **Reusing the homework schema.** The tables are exactly the ones from
  Assignment 2, with the Assignment 3 indexes. Only the two JSON columns the
  project rubric asks for were added.
- **Applying the homework concepts.** Deletes run as transactions with
  rollback on error (Assignment 4). All queries are parameterized and
  use the same `mysql-connector-python` patterns (Assignment 5).
- **JSON columns used for real.** `requirements` powers Job Match, and
  `interview_data` stores multiple interview rounds that the dashboard
  reads with MySQL's `JSON_TABLE`.
- **Separating logic from Flask.** Putting the matching algorithm and
  validation in their own modules made them unit-testable without a
  database (17 pytest tests).
- **Testing against a real database caught real problems.** While building,
  Claude ran every page and every create/edit/delete path against MySQL
  8.0 and found:
  - Ubuntu's MySQL `root` account uses socket auth, so the app couldn't log
    in with a password. Fixed by reading credentials from `.env` and adding
    a friendly "can't reach the database" page instead of a crash.
  - Job Match listed jobs at **0%** under "Any" minimum, which isn't a
    match. Changed the algorithm to leave out jobs with zero overlapping
    skills and added a test for it.
  - The navbar highlighted "Jobs" while on the Job Match page, because
    `job_match` starts with `job`. Fixed with an explicit mapping.
  - A template combined an HTML link with `|safe` in a way that would have
    escaped the link. Fixed with parentheses.

- **Mistakes caught when switching to the homework schema:**
  - The first version used a different schema (from the spec's table
    list), and its `schema.sql` would have **dropped the homework
    database**. Caught before it ran.
  - Workbench's "safe updates" mode blocks `UPDATE ... WHERE job_title = ...`,
    so the SQL scripts turn it off temporarily.
  - The homework foreign keys don't cascade, so deleting a company with
    jobs would fail. Fixed by deleting the child rows first, inside one
    transaction.
  - Homework websites are stored as `www.example.com` with no `https://`,
    so the validation was loosened and links get `https://` added
    for display.

## What I Modified

- **Switched the project to the homework schema.** The first version used
  the table list from the project spec. I realized the project is supposed
  to use the tables we built in the homework, gave Claude Assignments 1-5,
  and had the schema, sample data, and app rebuilt around the Assignment 2
  tables.
- **Rebuilt my database from scratch.** I ran `schema.sql` and
  `sample_data.sql` in MySQL Workbench, then checked the row counts with a
  query (6 companies, 18 jobs, 6 applications, 6 contacts).
- **Removed an unused file.** I deleted `upgrade_homework_db.sql` because I
  rebuilt the database instead of upgrading it, and updated the README and
  SQL comments that mentioned it.
- **Fixed the README.** I noticed `README.md` was missing from its own
  project structure list and had it added.
- **Tested the app myself.** I ran it locally and checked the dashboard
  numbers against the database. I also tried Job Match with
  `Python, SQL, Excel` and got the expected results (Intern - Data at 100%).
- **Committed in small steps.** I made the Git commits myself, one feature
  at a time, so the history shows how the project was put together.

## Lessons Learned

- **AI only knows what you give it.** It built a working app from the
  spec, but it didn't know about our homework tables until I uploaded the
  assignments. Giving it the full context up front would have saved a
  rebuild.
- **Check before running anything destructive.** The first `schema.sql`
  started with `DROP DATABASE`, which would have erased my homework data.
  I learned to read what a script does before running it.
- **Compare the output against the requirements.** Checking the project
  structure, README, and file list against the instructor's spec caught
  things the AI missed.
- **The homework concepts showed up in a real app.** Indexes (Assignment 3),
  transactions with rollback (Assignment 4), and parameterized queries
  (Assignment 5) all appear in the project.
- **Security takeaway.** Before trusting AI-written code, I would check
  that every query is parameterized, that passwords aren't hard-coded
  (this project keeps them in `.env`, which Git ignores), and that delete
  actions can't be triggered by just visiting a link.
