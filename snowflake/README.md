# Snowflake Log Anomaly Detection

This directory contains all the files needed to deploy and run the log anomaly detection system on Snowflake.

## 📁 Directory Contents

| File | Description |
|------|-------------|
| `setup.sql` | SQL script to create database, tables, and stages |
| `stored_procedures.sql` | Snowflake stored procedures for anomaly detection |
| `snowpark_analyzer.py` | Main Python module with TF-IDF vectorization and Isolation Forest |
| `streamlit_app.py` | Interactive Streamlit web interface |
| `snowflake_config.json.example` | Example configuration file |

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/vbatra/demos/python-for-devops/log_analyser
pip install -r snowflake_requirements.txt
```

### 2. Configure Snowflake
```bash
cd snowflake
cp snowflake_config.json.example snowflake_config.json
# Edit snowflake_config.json with your credentials
```

### 3. Run Setup SQL
```bash
snowsql -f setup.sql
```

### 4. Launch Streamlit App
```bash
streamlit run streamlit_app.py
```

## 📖 Full Documentation

See the complete deployment guide: [`SNOWFLAKE_DEPLOYMENT_GUIDE.md`](../SNOWFLAKE_DEPLOYMENT_GUIDE.md)

## 🔑 Key Features

- ✅ **TF-IDF Vectorization** - Converts log text into numerical features
- ✅ **Isolation Forest** - Machine learning for anomaly detection
- ✅ **Snowpark Integration** - Process data directly in Snowflake
- ✅ **Interactive UI** - Streamlit dashboard for visualization
- ✅ **Stored Procedures** - Run analysis directly from SQL
- ✅ **Scalable** - Handles large log volumes efficiently

## 🤖 How It Works

1. **Upload** log files to Snowflake stage or via Streamlit
2. **Parse** logs to extract structure (timestamp, level, message)
3. **Vectorize** using TF-IDF (default: 100 features)
4. **Extract** 12 structured features (error flags, patterns, etc.)
5. **Standardize** all features for ML processing
6. **Detect** anomalies using Isolation Forest
7. **Visualize** results in Streamlit dashboard

## 📊 Example Usage

### Python API
```python
from snowflake.snowpark import Session
from snowpark_analyzer import SnowparkLogAnalyzer
import json

# Connect
with open('snowflake_config.json', 'r') as f:
    config = json.load(f)
session = Session.builder.configs(config).create()

# Analyze
analyzer = SnowparkLogAnalyzer(session)
results = analyzer.run_full_pipeline(
    contamination=0.1,  # 10% expected anomalies
    max_features=100    # TF-IDF features
)

# View anomalies
anomalies = results[results['is_anomaly'] == True]
print(f"Found {len(anomalies)} anomalies")
```

### SQL Interface
```sql
-- Run analysis
CALL detect_log_anomalies('ALL', 0.1, 100);

-- View results
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
ORDER BY anomaly_probability DESC;
```

## ⚙️ Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `contamination` | 0.1 | Expected proportion of anomalies (0.1 = 10%) |
| `max_features` | 100 | Number of TF-IDF features to extract |
| `min_df` | 2 | Minimum document frequency for TF-IDF |
| `max_df` | 0.8 | Maximum document frequency for TF-IDF |
| `ngram_range` | (1, 2) | Use unigrams and bigrams |

## 🎯 Tuning Guidelines

| Use Case | Contamination | Max Features |
|----------|---------------|--------------|
| Production Monitoring | 0.05 | 100 |
| Security Analysis | 0.15 | 200 |
| General Debugging | 0.10 | 100 |
| Large Log Volumes | 0.05 | 50 |

## 📈 Performance Tips

- Start with smaller `max_features` (50-100) for faster processing
- Use file-specific analysis for large datasets
- Adjust warehouse size based on log volume
- Enable Snowflake result caching for repeated queries

## 🔧 Troubleshooting

**Connection Issues?**
- Verify credentials in `snowflake_config.json`
- Check warehouse is running: `SHOW WAREHOUSES;`
- Ensure role has necessary privileges

**No Anomalies Detected?**
- Increase `contamination` parameter
- Check logs were uploaded: `SELECT COUNT(*) FROM raw_logs;`
- Verify log parsing: `SELECT * FROM parsed_logs LIMIT 10;`

**Too Many Anomalies?**
- Decrease `contamination` parameter
- Increase `min_df` in TF-IDF settings
- Review log patterns for data quality

## 📞 Next Steps

1. Read the [Full Deployment Guide](../SNOWFLAKE_DEPLOYMENT_GUIDE.md)
2. Review [setup.sql](setup.sql) for database schema
3. Explore [snowpark_analyzer.py](snowpark_analyzer.py) for ML details
4. Customize [streamlit_app.py](streamlit_app.py) for your needs

---

**Ready to get started?** Follow the Quick Start above or read the full deployment guide! 🚀

