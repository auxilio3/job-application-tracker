-- =====================================================================
-- Sample data for the Job Application Tracker.
-- This is the same data built up in Assignments 2-5, plus required
-- skills for every job (for Job Match) and some interview history.
--
-- Run AFTER schema.sql. Do not run this on a homework database that
-- already has this data (you would get duplicates) - use
-- upgrade_homework_db.sql for that instead.
-- =====================================================================

USE job_tracker;

-- Workbench's "safe updates" mode blocks UPDATEs that don't filter by a
-- key column. Turn it off for this script, then back on at the end.
SET SQL_SAFE_UPDATES = 0;

-- ---------- Assignment 2 ----------
INSERT INTO companies (company_name, industry, website, city, state) VALUES
('Tech Solutions Inc',  'Technology',      'www.techsolutions.com',      'Miami',         'Florida'),
('Data Analytics Corp', 'Data Science',    'www.dataanalytics.com',      'Austin',        'Texas'),
('Cloud Systems LLC',   'Cloud Computing', 'www.cloudsystems.com',       'Seattle',       'Washington'),
('Digital Innovations', 'Software',        'www.digitalinnovations.com', 'San Francisco', 'California'),
('Smart Tech Group',    'AI/ML',           'www.smarttech.com',          'Boston',        'Massachusetts');

INSERT INTO jobs (company_id, job_title, salary_min, salary_max, job_type, date_posted) VALUES
(1, 'Software Developer',     70000,  90000, 'Full-time', '2025-01-15'),
(1, 'Database Administrator', 75000,  95000, 'Full-time', '2025-01-10'),
(2, 'Data Analyst',           65000,  85000, 'Full-time', '2025-01-12'),
(3, 'Cloud Engineer',         80000, 100000, 'Full-time', '2025-01-08'),
(4, 'Junior Developer',       55000,  70000, 'Full-time', '2025-01-14'),
(4, 'Senior Developer',       95000, 120000, 'Full-time', '2025-01-14'),
(5, 'ML Engineer',            90000, 115000, 'Full-time', '2025-01-11');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent) VALUES
(1, '2025-01-16', 'Applied',             'v2.1', TRUE),
(3, '2025-01-13', 'Interview Scheduled', 'v2.1', TRUE),
(4, '2025-01-09', 'Rejected',            'v2.0', FALSE),
(5, '2025-01-15', 'Applied',             'v2.1', TRUE),
(7, '2025-01-12', 'Phone Screen',        'v2.1', TRUE);

INSERT INTO contacts (company_id, first_name, last_name, email, job_title) VALUES
(1, 'Sarah',   'Johnson',  'sjohnson@techsolutions.com', 'HR Manager'),
(2, 'Michael', 'Chen',     'mchen@dataanalytics.com',    'Technical Recruiter'),
(3, 'Emily',   'Williams', 'ewilliams@cloudsystems.com', 'Hiring Manager'),
(4, 'David',   'Brown',    NULL,                         'Senior Developer'),
(5, 'Lisa',    'Garcia',   'lgarcia@smarttech.com',      'Talent Acquisition');

UPDATE applications SET status = 'Interview Completed' WHERE application_id = 3;

-- ---------- Assignment 3 ----------
INSERT INTO jobs (company_id, job_title, salary_min, salary_max, job_type, date_posted) VALUES
(1, 'QA Engineer',          60000,  80000, 'Full-time',  '2025-01-05'),
(2, 'Business Analyst',     65000,  85000, 'Full-time',  '2025-01-06'),
(2, 'Data Scientist',       85000, 110000, 'Full-time',  '2025-01-07'),
(3, 'DevOps Engineer',      80000, 105000, 'Full-time',  '2025-01-08'),
(3, 'Security Analyst',     75000,  95000, 'Full-time',  '2025-01-09'),
(4, 'UI/UX Designer',       60000,  80000, 'Full-time',  '2025-01-10'),
(5, 'Product Manager',      90000, 120000, 'Full-time',  '2025-01-11'),
(1, 'Technical Writer',     55000,  75000, 'Contract',   '2025-01-12'),
(2, 'Intern - Data',        30000,  40000, 'Internship', '2025-01-13'),
(4, 'Intern - Development', 32000,  42000, 'Internship', '2025-01-14');

-- ---------- Assignment 4 (the committed parts) ----------
INSERT INTO companies (company_name, industry, city, state)
VALUES ('New Tech Corp', 'Technology', 'Denver', 'Colorado');

INSERT INTO jobs (company_id, job_title, salary_min, salary_max, job_type)
VALUES ((SELECT company_id FROM companies WHERE company_name = 'New Tech Corp'),
        'Software Architect', 120000, 150000, 'Full-time');

UPDATE applications SET status = 'Interview Completed' WHERE application_id = 2;

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent)
VALUES (6, '2025-01-20', 'Applied', 'v3.0', TRUE);

UPDATE companies SET notes = 'Applied to Senior Developer position on 2025-01-20'
WHERE company_id = 4;

INSERT INTO contacts (company_id, first_name, last_name, email, job_title)
VALUES (4, 'Robert', 'Kim', 'rkim@digitalinnovations.com', 'Engineering Manager');

-- ---------- Assignment 5 ----------
UPDATE applications SET status = 'Offer Accepted' WHERE application_id = 1;

-- ---------- Project additions: skills, interviews, details ----------
-- Required skills for each job (JSON arrays), matched by job title.
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Java', 'SQL', 'Git')                                  WHERE job_title = 'Software Developer';
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'MySQL', 'Performance Tuning', 'Backup and Recovery', 'Linux') WHERE job_title = 'Database Administrator';
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'Excel', 'Tableau', 'Python')                             WHERE job_title = 'Data Analyst';
UPDATE jobs SET requirements = JSON_ARRAY('AWS', 'Linux', 'Terraform', 'Networking', 'Python')             WHERE job_title = 'Cloud Engineer';
UPDATE jobs SET requirements = JSON_ARRAY('JavaScript', 'HTML', 'CSS', 'Git')                              WHERE job_title = 'Junior Developer';
UPDATE jobs SET requirements = JSON_ARRAY('Java', 'Spring', 'SQL', 'System Design', 'AWS')                 WHERE job_title = 'Senior Developer';
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Machine Learning', 'TensorFlow', 'SQL')               WHERE job_title = 'ML Engineer';
UPDATE jobs SET requirements = JSON_ARRAY('Selenium', 'Python', 'Test Automation', 'SQL')                  WHERE job_title = 'QA Engineer';
UPDATE jobs SET requirements = JSON_ARRAY('Excel', 'SQL', 'Requirements Gathering', 'Tableau')             WHERE job_title = 'Business Analyst';
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Machine Learning', 'Statistics', 'SQL')               WHERE job_title = 'Data Scientist';
UPDATE jobs SET requirements = JSON_ARRAY('Docker', 'Kubernetes', 'Linux', 'CI/CD', 'AWS')                 WHERE job_title = 'DevOps Engineer';
UPDATE jobs SET requirements = JSON_ARRAY('SIEM', 'Splunk', 'Incident Response', 'Networking', 'Linux')    WHERE job_title = 'Security Analyst';
UPDATE jobs SET requirements = JSON_ARRAY('Figma', 'User Research', 'HTML', 'CSS')                         WHERE job_title = 'UI/UX Designer';
UPDATE jobs SET requirements = JSON_ARRAY('Agile', 'Roadmapping', 'SQL', 'Communication')                  WHERE job_title = 'Product Manager';
UPDATE jobs SET requirements = JSON_ARRAY('Documentation', 'Markdown', 'Git', 'Communication')             WHERE job_title = 'Technical Writer';
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'SQL', 'Excel')                                        WHERE job_title = 'Intern - Data';
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Git', 'HTML')                                         WHERE job_title = 'Intern - Development';
UPDATE jobs SET requirements = JSON_ARRAY('System Design', 'Java', 'AWS', 'Microservices')                 WHERE job_title = 'Software Architect';

-- Interview history (JSON) for a few applications. interview_date holds
-- the next upcoming interview, or the latest one if none are upcoming.
UPDATE applications
SET interview_data = JSON_ARRAY(
        JSON_OBJECT('date', '2025-01-22', 'time', '10:00', 'round', 'Phone Screen',
                    'interviewer', 'Sarah Johnson', 'notes', 'Culture fit and salary range.'),
        JSON_OBJECT('date', '2025-01-29', 'time', '14:00', 'round', 'Technical',
                    'interviewer', 'Dev team', 'notes', 'Live coding in Python; went well.')),
    interview_date = '2025-01-29 14:00:00',
    response_date  = '2025-01-20',
    notes = 'Offer accepted on 2025-02-05.'
WHERE application_id = 1;

UPDATE applications
SET interview_data = JSON_ARRAY(
        JSON_OBJECT('date', '2025-01-21', 'time', '11:00', 'round', 'Technical',
                    'interviewer', 'Michael Chen', 'notes', 'SQL joins and a Tableau dashboard walkthrough.')),
    interview_date = '2025-01-21 11:00:00',
    response_date  = '2025-01-17'
WHERE application_id = 2;

UPDATE applications
SET interview_data = JSON_ARRAY(
        JSON_OBJECT('date', '2025-01-15', 'time', '09:30', 'round', 'Hiring Manager',
                    'interviewer', 'Emily Williams', 'notes', '')),
    interview_date = '2025-01-15 09:30:00',
    response_date  = '2025-01-12',
    notes = 'Waiting to hear back after the hiring manager round.'
WHERE application_id = 3;

UPDATE applications
SET interview_data = JSON_ARRAY(
        JSON_OBJECT('date', '2026-11-05', 'time', '15:00', 'round', 'Phone Screen',
                    'interviewer', 'Lisa Garcia', 'notes', 'Review ML project from portfolio.')),
    interview_date = '2026-11-05 15:00:00',
    response_date  = '2025-01-18'
WHERE application_id = 5;

UPDATE jobs SET is_active = FALSE WHERE job_title = 'Cloud Engineer';

SET SQL_SAFE_UPDATES = 1;
