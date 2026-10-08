-- =====================================================================
-- Job Application Tracker - Database Schema (MySQL 8.0+)
--
-- Builds the job_tracker database from scratch:
--   * the four tables from Assignment 2 (same columns and foreign keys)
--   * the two JSON columns required by the project spec:
--       jobs.requirements          - JSON array of required skills
--       applications.interview_data - JSON array of interview rounds
--   * the indexes from Assignment 3
--
-- WARNING: this DROPS any existing job_tracker database first.
-- If you already built job_tracker in the homework and want to keep
-- that data, run upgrade_homework_db.sql instead.
--
--   Run:  MySQL Workbench -> File -> Open SQL Script -> schema.sql -> ⚡
--   Then (optional) sample_data.sql for demo data.
-- =====================================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker;
USE job_tracker;

-- ---------------------------------------------------------------------
-- companies (Assignment 2)
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- jobs (Assignment 2 + requirements JSON from the project spec)
--   requirements example: ["Python", "SQL", "Git"]
-- ---------------------------------------------------------------------
CREATE TABLE jobs (
    job_id          INT AUTO_INCREMENT PRIMARY KEY,
    company_id      INT NOT NULL,
    job_title       VARCHAR(100) NOT NULL,
    job_description TEXT,
    salary_min      DECIMAL(10,2),
    salary_max      DECIMAL(10,2),
    job_type        VARCHAR(20),
    posting_url     VARCHAR(500),
    date_posted     DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requirements    JSON,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    CONSTRAINT chk_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
    CONSTRAINT chk_requirements_array
        CHECK (requirements IS NULL OR JSON_TYPE(requirements) = 'ARRAY')
);

-- ---------------------------------------------------------------------
-- applications (Assignment 2 + interview_data JSON from the project spec)
--   interview_data example:
--   [{"date": "2025-01-20", "time": "10:00", "round": "Phone Screen",
--     "interviewer": "Michael Chen", "notes": "Asked about SQL joins"}]
--   interview_date (from Assignment 2) is kept in sync by the app:
--   it holds the next upcoming interview, or the latest past one.
-- ---------------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT AUTO_INCREMENT PRIMARY KEY,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            VARCHAR(30) DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    response_date     DATE,
    interview_date    DATETIME,
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    interview_data    JSON,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    CONSTRAINT chk_interview_array
        CHECK (interview_data IS NULL OR JSON_TYPE(interview_data) = 'ARRAY')
);

-- ---------------------------------------------------------------------
-- contacts (Assignment 2)
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT AUTO_INCREMENT PRIMARY KEY,
    company_id   INT NOT NULL,
    first_name   VARCHAR(50) NOT NULL,
    last_name    VARCHAR(50) NOT NULL,
    email        VARCHAR(100),
    phone        VARCHAR(20),
    job_title    VARCHAR(100),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- ---------------------------------------------------------------------
-- Indexes (Assignment 3). Foreign key columns get indexes automatically.
-- ---------------------------------------------------------------------
CREATE INDEX idx_job_title        ON jobs(job_title);
CREATE INDEX idx_company_type     ON jobs(company_id, job_type);
CREATE INDEX idx_app_status       ON applications(status);
CREATE INDEX idx_company_industry ON companies(industry);
