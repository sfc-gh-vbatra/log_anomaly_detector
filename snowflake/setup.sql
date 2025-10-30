-- Snowflake Setup Script for Log Anomaly Detection System
-- This script creates the necessary database objects

-- Step 1: Create Database and Schema
CREATE DATABASE IF NOT EXISTS LOG_ANALYTICS;
USE DATABASE LOG_ANALYTICS;

CREATE SCHEMA IF NOT EXISTS ANOMALY_DETECTION;
USE SCHEMA ANOMALY_DETECTION;

-- Step 2: Create Warehouse (adjust size based on your needs)
CREATE WAREHOUSE IF NOT EXISTS LOG_ANALYZER_WH
    WITH WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

USE WAREHOUSE LOG_ANALYZER_WH;

-- Step 3: Create File Format for Log Files
CREATE OR REPLACE FILE FORMAT log_file_format
    TYPE = 'CSV'
    FIELD_DELIMITER = 'NONE'
    SKIP_HEADER = 0
    FIELD_OPTIONALLY_ENCLOSED_BY = NONE
    ESCAPE_UNENCLOSED_FIELD = NONE
    RECORD_DELIMITER = '\n'
    NULL_IF = ('NULL', 'null', '')
    COMPRESSION = 'AUTO';

-- Step 4: Create Stage for Log File Uploads
CREATE OR REPLACE STAGE log_files_stage
    FILE_FORMAT = log_file_format
    DIRECTORY = (ENABLE = TRUE);

-- Step 5: Create Raw Logs Table
CREATE OR REPLACE TABLE raw_logs (
    log_id NUMBER AUTOINCREMENT,
    file_name VARCHAR(500),
    raw_line VARCHAR(16777216),
    ingestion_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (log_id)
);

-- Step 6: Create Parsed Logs Table
CREATE OR REPLACE TABLE parsed_logs (
    log_id NUMBER,
    file_name VARCHAR(500),
    timestamp_extracted TIMESTAMP_NTZ,
    log_level VARCHAR(50),
    message VARCHAR(16777216),
    message_length NUMBER,
    parsed_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (log_id) REFERENCES raw_logs(log_id)
);

-- Step 7: Create Feature Table
CREATE OR REPLACE TABLE log_features (
    log_id NUMBER,
    type_code NUMBER,
    msg_len NUMBER,
    has_error NUMBER,
    has_failure NUMBER,
    has_exception NUMBER,
    is_unauthorized NUMBER,
    is_connection_issue NUMBER,
    message_frequency NUMBER,
    has_number NUMBER,
    feature_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (log_id) REFERENCES raw_logs(log_id)
);

-- Step 8: Create Anomaly Results Table
CREATE OR REPLACE TABLE anomaly_results (
    log_id NUMBER,
    file_name VARCHAR(500),
    log_level VARCHAR(50),
    message VARCHAR(16777216),
    anomaly_score NUMBER,
    anomaly_probability FLOAT,
    is_anomaly BOOLEAN,
    detection_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (log_id) REFERENCES raw_logs(log_id)
);

-- Step 9: Create Summary View
CREATE OR REPLACE VIEW anomaly_summary AS
SELECT 
    file_name,
    COUNT(*) as total_logs,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) as anomaly_count,
    ROUND(100.0 * SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) / COUNT(*), 2) as anomaly_percentage,
    MAX(detection_timestamp) as last_analysis
FROM anomaly_results
GROUP BY file_name
ORDER BY last_analysis DESC;

-- Step 10: Create Historical Tracking Table
CREATE OR REPLACE TABLE anomaly_runs (
    run_id NUMBER AUTOINCREMENT,
    file_name VARCHAR(500),
    total_logs NUMBER,
    anomalies_detected NUMBER,
    contamination_factor FLOAT,
    run_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (run_id)
);

-- Grant necessary privileges (adjust as per your role setup)
-- GRANT USAGE ON WAREHOUSE LOG_ANALYZER_WH TO ROLE YOUR_ROLE;
-- GRANT ALL PRIVILEGES ON DATABASE LOG_ANALYTICS TO ROLE YOUR_ROLE;
-- GRANT ALL PRIVILEGES ON SCHEMA ANOMALY_DETECTION TO ROLE YOUR_ROLE;

-- Show created objects
SHOW TABLES IN SCHEMA LOG_ANALYTICS.ANOMALY_DETECTION;
SHOW STAGES IN SCHEMA LOG_ANALYTICS.ANOMALY_DETECTION;

SELECT 'Snowflake setup complete! 🎉' AS status;

