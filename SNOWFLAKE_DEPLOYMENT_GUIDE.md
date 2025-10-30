# Snowflake Deployment Guide
## Log Anomaly Detection System with TF-IDF Vectorization & Isolation Forest

This guide will help you deploy and run the log anomaly detection system on Snowflake.

---

## 🎯 Overview

This system uses:
- **TF-IDF (Term Frequency-Inverse Document Frequency)** for text vectorization
- **Isolation Forest** algorithm for anomaly detection
- **Snowpark Python** for processing within Snowflake
- **Streamlit** for interactive visualization

### Architecture

```
┌─────────────────┐
│   Log Files     │
│  (.log / .txt)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Snowflake      │
│  Stage Upload   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Raw Logs       │
│  Table          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse & Clean  │
│  (UDF/Sproc)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TF-IDF         │
│  Vectorization  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Isolation      │
│  Forest Model   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Anomaly        │
│  Results        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit UI   │
│  Visualization  │
└─────────────────┘
```

---

## 📋 Prerequisites

1. **Snowflake Account** with appropriate privileges
2. **Python 3.8+** installed locally
3. **Snowflake Role** with:
   - CREATE DATABASE
   - CREATE SCHEMA
   - CREATE TABLE
   - CREATE STAGE
   - CREATE WAREHOUSE
   - CREATE PROCEDURE
   - USAGE on WAREHOUSE

---

## 🚀 Step 1: Install Dependencies

### Option A: Using the Snowflake requirements file
```bash
pip install -r snowflake_requirements.txt
```

### Option B: Install packages individually
```bash
pip install snowflake-snowpark-python>=1.11.0
pip install snowflake-connector-python>=3.6.0
pip install scikit-learn>=1.3.0
pip install pandas numpy scipy
pip install streamlit plotly
pip install joblib nltk
```

---

## 🔧 Step 2: Configure Snowflake Connection

### Create Configuration File

1. Copy the example config:
```bash
cd snowflake
cp snowflake_config.json.example snowflake_config.json
```

2. Edit `snowflake_config.json` with your credentials:
```json
{
  "account": "your_account.region",
  "user": "your_username",
  "password": "your_password",
  "role": "your_role",
  "warehouse": "LOG_ANALYZER_WH",
  "database": "LOG_ANALYTICS",
  "schema": "ANOMALY_DETECTION"
}
```

**Security Note:** Never commit `snowflake_config.json` to version control!

### Alternative: Use Environment Variables

Create a `.env` file:
```bash
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=LOG_ANALYZER_WH
SNOWFLAKE_DATABASE=LOG_ANALYTICS
SNOWFLAKE_SCHEMA=ANOMALY_DETECTION
```

---

## 🏗️ Step 3: Set Up Snowflake Objects

### Run Setup Script

1. Open Snowflake Web UI or use SnowSQL
2. Execute the setup script:

```bash
snowsql -f snowflake/setup.sql
```

Or manually copy and paste the SQL from `snowflake/setup.sql` into Snowflake UI.

This creates:
- ✅ Database: `LOG_ANALYTICS`
- ✅ Schema: `ANOMALY_DETECTION`
- ✅ Warehouse: `LOG_ANALYZER_WH`
- ✅ Tables: `raw_logs`, `parsed_logs`, `log_features`, `anomaly_results`
- ✅ Stage: `log_files_stage`
- ✅ Views: `anomaly_summary`

### Verify Setup

```sql
USE DATABASE LOG_ANALYTICS;
USE SCHEMA ANOMALY_DETECTION;

SHOW TABLES;
SHOW STAGES;
```

---

## 📤 Step 4: Upload Log Files

### Option A: Upload via Snowflake Stage

1. Upload files to stage:
```sql
PUT file:///path/to/your/logfile.log @log_files_stage AUTO_COMPRESS=FALSE;
```

2. Load into raw_logs table:
```sql
COPY INTO raw_logs (file_name, raw_line)
FROM (
    SELECT 
        METADATA$FILENAME as file_name,
        $1 as raw_line
    FROM @log_files_stage/logfile.log
)
FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = 'NONE' RECORD_DELIMITER = '\n');
```

### Option B: Use Python Script

```python
from snowflake.snowpark import Session
import json

# Load config
with open('snowflake/snowflake_config.json', 'r') as f:
    config = json.load(f)

# Create session
session = Session.builder.configs(config).create()

# Read log file
with open('logs/test.txt', 'r') as f:
    lines = f.readlines()

# Create DataFrame
import pandas as pd
df = pd.DataFrame({
    'file_name': ['test.txt'] * len(lines),
    'raw_line': [line.strip() for line in lines]
})

# Upload to Snowflake
sp_df = session.create_dataframe(df)
sp_df.write.mode("append").save_as_table("raw_logs")

print(f"✅ Uploaded {len(lines)} log lines")
```

### Option C: Use Streamlit App

Run the Streamlit app (see Step 6) and use the **Upload Logs** tab.

---

## 🤖 Step 5: Run Anomaly Detection

### Option A: Using Python Script

```python
from snowflake.snowpark import Session
from snowflake.snowpark_analyzer import SnowparkLogAnalyzer
import json

# Load config
with open('snowflake/snowflake_config.json', 'r') as f:
    config = json.load(f)

# Create session
session = Session.builder.configs(config).create()

# Create analyzer
analyzer = SnowparkLogAnalyzer(session)

# Run full pipeline with TF-IDF vectorization
results = analyzer.run_full_pipeline(
    file_name=None,  # None = process all files
    contamination=0.1,  # 10% expected anomalies
    max_features=100  # Number of TF-IDF features
)

# View results
print("\n🚨 Top Anomalies:")
anomalies = results[results['is_anomaly'] == True].sort_values(
    'anomaly_probability', ascending=False
).head(10)
print(anomalies[['LOG_LEVEL', 'MESSAGE', 'anomaly_probability']])

# Save model for later use
analyzer.save_model('./models')

session.close()
```

### Option B: Using Stored Procedures

First, deploy the stored procedures:
```sql
-- Execute the stored_procedures.sql file
-- (Copy contents from snowflake/stored_procedures.sql)
```

Then call them:
```sql
-- Parse all raw logs
CALL parse_raw_logs('ALL');

-- Detect anomalies with 10% contamination and 100 TF-IDF features
CALL detect_log_anomalies('ALL', 0.1, 100);

-- View results
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
ORDER BY anomaly_probability DESC 
LIMIT 100;
```

### Option C: Use Streamlit App (Recommended)

See Step 6 below.

---

## 🎨 Step 6: Launch Streamlit UI

The Streamlit app provides an interactive interface for:
- Uploading log files
- Running anomaly detection with TF-IDF vectorization
- Visualizing results
- Viewing historical trends

### Launch the App

```bash
cd snowflake
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

### Streamlit Configuration (Optional)

Create `.streamlit/secrets.toml` for credentials:

```toml
[snowflake]
account = "your_account.region"
user = "your_username"
password = "your_password"
role = "your_role"
warehouse = "LOG_ANALYZER_WH"
database = "LOG_ANALYTICS"
schema = "ANOMALY_DETECTION"
```

---

## 📊 Understanding the Results

### Anomaly Score
- **-1**: Anomaly detected
- **1**: Normal log entry

### Anomaly Probability
- Higher values indicate stronger anomaly signals
- Values are derived from the Isolation Forest algorithm
- Normalized scores from the model

### Feature Extraction

The system extracts:

1. **Structured Features (12 features)**:
   - `msg_len`: Message length
   - `has_error`: ERROR level indicator
   - `has_warning`: WARNING level indicator
   - `has_critical`: CRITICAL level indicator
   - `has_failure`: Contains "fail" keyword
   - `has_exception`: Contains "exception"
   - `is_unauthorized`: Contains "unauthorized"
   - `is_connection_issue`: Network/connection related
   - `has_number`: Contains numeric values
   - `has_special_chars`: Count of special characters
   - `message_frequency`: How often this message appears
   - `is_rare_message`: Rare message indicator

2. **TF-IDF Features (configurable, default 100)**:
   - Vectorized representation of log text
   - Captures semantic meaning
   - Uses unigrams and bigrams
   - Normalized by document frequency

**Total Features = 12 + TF-IDF features (e.g., 112 features total)**

---

## 🔍 Querying Results

### View All Anomalies
```sql
SELECT 
    log_level,
    message,
    anomaly_probability,
    detection_timestamp
FROM anomaly_results
WHERE is_anomaly = TRUE
ORDER BY anomaly_probability DESC;
```

### Summary Statistics
```sql
SELECT * FROM anomaly_summary;
```

### Analysis History
```sql
SELECT * FROM anomaly_runs 
ORDER BY run_timestamp DESC 
LIMIT 10;
```

### Top N Anomalies by File
```sql
SELECT 
    file_name,
    log_level,
    message,
    anomaly_probability
FROM anomaly_results
WHERE is_anomaly = TRUE
    AND file_name = 'your_file.log'
ORDER BY anomaly_probability DESC
LIMIT 20;
```

### Anomaly Trend Over Time
```sql
SELECT 
    DATE_TRUNC('hour', detection_timestamp) as hour,
    COUNT(*) as anomaly_count
FROM anomaly_results
WHERE is_anomaly = TRUE
GROUP BY hour
ORDER BY hour DESC;
```

---

## 🎛️ Tuning Parameters

### Contamination Factor
- **Low (0.01-0.05)**: Very strict, finds only extreme anomalies
- **Medium (0.05-0.15)**: Balanced (recommended)
- **High (0.15-0.30)**: More permissive, catches more potential issues

### TF-IDF Features
- **50-100**: Fast processing, good for smaller log sets
- **100-200**: Better accuracy, moderate processing time
- **200-500**: Maximum detail, slower processing

### When to Adjust

| Scenario | Contamination | TF-IDF Features |
|----------|--------------|-----------------|
| Production monitoring | 0.05 | 100 |
| Security analysis | 0.15 | 200 |
| General debugging | 0.10 | 100 |
| Large log volumes | 0.05 | 50-100 |

---

## 🔧 Troubleshooting

### Connection Issues
```python
# Test connection
from snowflake.snowpark import Session
import json

with open('snowflake/snowflake_config.json', 'r') as f:
    config = json.load(f)

try:
    session = Session.builder.configs(config).create()
    print(f"✅ Connected: {session.get_current_account()}")
    session.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### No Anomalies Detected
- Increase contamination factor
- Check if logs have sufficient variety
- Verify log parsing is working correctly

### Too Many Anomalies
- Decrease contamination factor
- Increase min_df parameter in TF-IDF
- Review log quality and patterns

### Memory Issues
- Reduce max_features
- Process files in smaller batches
- Increase Snowflake warehouse size

---

## 📈 Best Practices

1. **Start Small**: Test with a small log file first
2. **Iterate on Contamination**: Adjust based on results
3. **Monitor Performance**: Track warehouse credit usage
4. **Regular Cleanup**: Archive old anomaly results
5. **Version Models**: Save trained models with timestamps
6. **Document Patterns**: Keep notes on recurring anomalies

---

## 🔐 Security Considerations

1. **Never commit** `snowflake_config.json` to version control
2. Use Snowflake's **key pair authentication** in production
3. Implement **row-level security** for sensitive logs
4. Use **masked columns** for PII in logs
5. Enable **Snowflake audit logging**
6. Rotate credentials regularly

---

## 📚 Additional Resources

- [Snowpark Python Documentation](https://docs.snowflake.com/en/developer-guide/snowpark/python/index.html)
- [Isolation Forest Algorithm](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [TF-IDF Vectorization](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

## 🆘 Support

For issues or questions:
1. Check logs in Snowflake query history
2. Review Streamlit terminal output
3. Verify all prerequisites are met
4. Check Snowflake warehouse is running

---

## 📝 Example Workflow

```bash
# 1. Setup
pip install -r snowflake_requirements.txt
cd snowflake
cp snowflake_config.json.example snowflake_config.json
# Edit snowflake_config.json with your credentials

# 2. Initialize Snowflake
snowsql -f setup.sql

# 3. Upload logs (using Python)
python << EOF
from snowflake.snowpark import Session
import json, pandas as pd

with open('snowflake_config.json', 'r') as f:
    config = json.load(f)

session = Session.builder.configs(config).create()

with open('../logs/test.txt', 'r') as f:
    lines = [line.strip() for line in f if line.strip()]

df = pd.DataFrame({
    'file_name': ['test.txt'] * len(lines),
    'raw_line': lines
})

session.create_dataframe(df).write.mode("append").save_as_table("raw_logs")
print(f"✅ Uploaded {len(lines)} logs")
session.close()
EOF

# 4. Run analysis
python << EOF
from snowflake.snowpark import Session
from snowpark_analyzer import SnowparkLogAnalyzer
import json

with open('snowflake_config.json', 'r') as f:
    config = json.load(f)

session = Session.builder.configs(config).create()
analyzer = SnowparkLogAnalyzer(session)
results = analyzer.run_full_pipeline(contamination=0.1, max_features=100)
print(f"\n✅ Found {results['is_anomaly'].sum()} anomalies")
session.close()
EOF

# 5. Launch UI
streamlit run streamlit_app.py
```

---

## 🎉 Congratulations!

You've successfully deployed the Log Anomaly Detection system with TF-IDF vectorization and Isolation Forest on Snowflake! 🚀

