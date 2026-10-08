-- =====================================================================
-- Upgrade an existing homework job_tracker database for the project.
--
-- Use this INSTEAD of schema.sql if you already built job_tracker in
-- Assignments 1-5. It keeps all of your existing data and only ADDS:
--   * jobs.requirements          (JSON array of required skills)
--   * applications.interview_data (JSON array of interview rounds)
--   * CHECK constraints on those columns and on the salary range
--   * required skills for the homework jobs, so Job Match has data
--
-- Run it ONE time. If you run it again you'll get a "Duplicate ..."
-- error on the first ALTER. That's harmless: it means it already ran.
-- =====================================================================

USE job_tracker;
SET SQL_SAFE_UPDATES = 0;

ALTER TABLE jobs
    ADD COLUMN requirements JSON,
    ADD CONSTRAINT chk_requirements_array
        CHECK (requirements IS NULL OR JSON_TYPE(requirements) = 'ARRAY'),
    ADD CONSTRAINT chk_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max);

ALTER TABLE applications
    ADD COLUMN interview_data JSON,
    ADD CONSTRAINT chk_interview_array
        CHECK (interview_data IS NULL OR JSON_TYPE(interview_data) = 'ARRAY');

-- Fill in the new columns inside one transaction (Assignment 4):
-- either every UPDATE below is saved, or none are.
START TRANSACTION;

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

-- Copy any interview_date you already entered into the new
-- interview_data list, so no interview information is lost.
UPDATE applications
SET interview_data = JSON_ARRAY(JSON_OBJECT(
        'date',  DATE_FORMAT(interview_date, '%Y-%m-%d'),
        'time',  DATE_FORMAT(interview_date, '%H:%i'),
        'round', 'Interview', 'interviewer', '', 'notes', ''))
WHERE interview_date IS NOT NULL AND interview_data IS NULL;

COMMIT;

SET SQL_SAFE_UPDATES = 1;

-- Check: every job should now show its skills.
SELECT job_id, job_title, requirements FROM jobs;
