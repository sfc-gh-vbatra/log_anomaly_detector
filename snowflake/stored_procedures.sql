-- Snowflake Stored Procedures for Log Anomaly Detection
-- These procedures can be called directly from Snowflake

USE DATABASE LOG_ANALYTICS;
USE SCHEMA ANOMALY_DETECTION;
USE WAREHOUSE LOG_ANALYZER_WH;

-- Stored Procedure 1: Parse Logs from Raw Table
CREATE OR REPLACE PROCEDURE parse_raw_logs(FILE_NAME_FILTER VARCHAR)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'parse_logs'
AS
$$
import re
from snowflake.snowpark import Session

def parse_logs(session: Session, file_name_filter: str) -> str:
    """Parse raw logs and populate parsed_logs table."""
    
    # Build query
    if file_name_filter and file_name_filter.upper() != 'ALL':
        where_clause = f"WHERE file_name = '{file_name_filter}'"
    else:
        where_clause = ""
    
    # Parse logs using SQL
    parse_sql = f"""
    INSERT INTO parsed_logs (log_id, file_name, log_level, message, message_length)
    SELECT 
        log_id,
        file_name,
        CASE 
            WHEN raw_line LIKE '%ERROR%' THEN 'ERROR'
            WHEN raw_line LIKE '%WARNING%' OR raw_line LIKE '%WARN%' THEN 'WARNING'
            WHEN raw_line LIKE '%CRITICAL%' OR raw_line LIKE '%FATAL%' THEN 'CRITICAL'
            WHEN raw_line LIKE '%DEBUG%' THEN 'DEBUG'
            WHEN raw_line LIKE '%SUMMARY%' THEN 'SUMMARY'
            ELSE 'INFO'
        END as log_level,
        REGEXP_REPLACE(raw_line, '^\\d{{4}}-\\d{{2}}-\\d{{2}}\\s+\\d{{2}}:\\d{{2}}:\\d{{2}}\\s*', '') as message,
        LENGTH(REGEXP_REPLACE(raw_line, '^\\d{{4}}-\\d{{2}}-\\d{{2}}\\s+\\d{{2}}:\\d{{2}}:\\d{{2}}\\s*', '')) as message_length
    FROM raw_logs
    {where_clause}
    """
    
    result = session.sql(parse_sql).collect()
    row_count = session.sql(f"SELECT COUNT(*) FROM parsed_logs {where_clause}").collect()[0][0]
    
    return f"Successfully parsed {row_count} logs"
$$;

-- Stored Procedure 2: Run Anomaly Detection with Vectorization
CREATE OR REPLACE PROCEDURE detect_log_anomalies(
    FILE_NAME_FILTER VARCHAR,
    CONTAMINATION FLOAT,
    MAX_FEATURES INT
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas', 'scikit-learn', 'numpy')
HANDLER = 'detect_anomalies'
AS
$$
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from snowflake.snowpark import Session

def detect_anomalies(session: Session, file_name_filter: str, contamination: float, max_features: int) -> str:
    """Detect anomalies using TF-IDF vectorization and Isolation Forest."""
    
    # Load parsed logs
    if file_name_filter and file_name_filter.upper() != 'ALL':
        query = f"SELECT * FROM parsed_logs WHERE file_name = '{file_name_filter}'"
    else:
        query = "SELECT * FROM parsed_logs"
    
    df = session.sql(query).to_pandas()
    
    if df.empty:
        return "No logs found to analyze"
    
    # Extract structured features
    df['msg_len'] = df['MESSAGE'].fillna('').str.len()
    df['has_error'] = (df['LOG_LEVEL'] == 'ERROR').astype(int)
    df['has_warning'] = (df['LOG_LEVEL'] == 'WARNING').astype(int)
    df['has_critical'] = (df['LOG_LEVEL'] == 'CRITICAL').astype(int)
    df['has_failure'] = df['MESSAGE'].fillna('').str.contains(r'fail(ed|ure)?', case=False, regex=True).astype(int)
    df['has_exception'] = df['MESSAGE'].fillna('').str.contains('exception', case=False).astype(int)
    df['is_unauthorized'] = df['MESSAGE'].fillna('').str.contains('unauthorized', case=False).astype(int)
    df['is_connection_issue'] = df['MESSAGE'].fillna('').str.contains('connection|network|timeout', case=False, regex=True).astype(int)
    df['has_number'] = df['MESSAGE'].fillna('').str.contains(r'\\d+', regex=True).astype(int)
    
    # Message frequency
    message_counts = df['MESSAGE'].value_counts()
    df['message_frequency'] = df['MESSAGE'].map(message_counts)
    
    # Vectorize with TF-IDF
    messages = df['MESSAGE'].fillna('').tolist()
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=2,
        max_df=0.8,
        ngram_range=(1, 2),
        lowercase=True,
        stop_words='english'
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(messages)
        tfidf_features = tfidf_matrix.toarray()
        tfidf_df = pd.DataFrame(tfidf_features, index=df.index)
    except:
        tfidf_df = pd.DataFrame()
    
    # Combine features
    structured_features = ['msg_len', 'has_error', 'has_warning', 'has_critical',
                          'has_failure', 'has_exception', 'is_unauthorized',
                          'is_connection_issue', 'has_number', 'message_frequency']
    
    if not tfidf_df.empty:
        feature_matrix = pd.concat([df[structured_features], tfidf_df], axis=1)
    else:
        feature_matrix = df[structured_features]
    
    feature_matrix = feature_matrix.fillna(0)
    
    # Standardize
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)
    
    # Isolation Forest
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    
    anomaly_scores = model.fit_predict(scaled_features)
    anomaly_probabilities = -model.score_samples(scaled_features)
    
    # Add results
    df['anomaly_score'] = anomaly_scores
    df['anomaly_probability'] = anomaly_probabilities
    df['is_anomaly'] = (anomaly_scores == -1)
    
    # Save to Snowflake
    results_df = df[['LOG_ID', 'FILE_NAME', 'LOG_LEVEL', 'MESSAGE', 
                     'anomaly_score', 'anomaly_probability', 'is_anomaly']]
    
    sp_df = session.create_dataframe(results_df)
    sp_df.write.mode("append").save_as_table("anomaly_results")
    
    # Record run
    anomaly_count = int((anomaly_scores == -1).sum())
    total_count = len(df)
    
    run_df = pd.DataFrame([{
        'file_name': file_name_filter if file_name_filter else 'ALL',
        'total_logs': total_count,
        'anomalies_detected': anomaly_count,
        'contamination_factor': contamination
    }])
    
    session.create_dataframe(run_df).write.mode("append").save_as_table("anomaly_runs")
    
    return f"Detected {anomaly_count} anomalies out of {total_count} logs ({100*anomaly_count/total_count:.1f}%) using {feature_matrix.shape[1]} features"
$$;

-- Stored Procedure 3: Upload and Process Log File
CREATE OR REPLACE PROCEDURE process_log_file(
    STAGE_NAME VARCHAR,
    FILE_PATTERN VARCHAR,
    CONTAMINATION FLOAT
)
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- Step 1: Load from stage
    LET copy_result STRING;
    COPY INTO raw_logs (file_name, raw_line)
    FROM (
        SELECT 
            METADATA$FILENAME as file_name,
            $1 as raw_line
        FROM @:STAGE_NAME/:FILE_PATTERN
    )
    FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = 'NONE' RECORD_DELIMITER = '\n')
    ON_ERROR = 'CONTINUE';
    
    -- Step 2: Parse logs
    CALL parse_raw_logs('ALL');
    
    -- Step 3: Detect anomalies
    CALL detect_log_anomalies('ALL', :CONTAMINATION, 100);
    
    RETURN 'Log file processed successfully';
END;
$$;

-- Example usage queries (commented out):
/*
-- Parse all raw logs
CALL parse_raw_logs('ALL');

-- Detect anomalies with 10% contamination and 100 TF-IDF features
CALL detect_log_anomalies('ALL', 0.1, 100);

-- Process a specific file
CALL detect_log_anomalies('my_logs.txt', 0.15, 150);

-- View results
SELECT * FROM anomaly_results WHERE is_anomaly = TRUE ORDER BY anomaly_probability DESC LIMIT 100;

-- View summary
SELECT * FROM anomaly_summary;

-- View run history
SELECT * FROM anomaly_runs ORDER BY run_timestamp DESC;
*/

