# Snowflake Log Anomaly Detector

[![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

Enterprise-grade log anomaly detection system using **TF-IDF vectorization** and **Isolation Forest** machine learning, integrated with Snowflake for scalable analysis.

## 🎯 Features

- ✅ **TF-IDF Vectorization** - Semantic text analysis with 100+ features
- ✅ **Isolation Forest ML** - Detects anomalies without predefined rules  
- ✅ **112-Dimensional Analysis** - 12 structured + 100 TF-IDF features
- ✅ **Snowpark Python Integration** - Native Snowflake processing
- ✅ **Interactive Dashboard** - Streamlit UI with cluster visualization
- ✅ **Key-Pair Authentication** - Enterprise-grade security
- ✅ **Stored Procedures** - SQL-callable anomaly detection
- ✅ **Real-Time Analysis** - Process logs at scale

## 📊 How It Works

```
Raw Logs → Parse → Feature Extraction → TF-IDF Vectorization → Isolation Forest → Anomalies
            ↓           ↓                    ↓                      ↓              ↓
        Structure   12 Features         100 Features          ML Model      Results + Viz
```

### The Algorithm

1. **Text Vectorization**: TF-IDF converts log messages into numerical vectors capturing semantic meaning
2. **Feature Engineering**: 12 structured features + 100 TF-IDF = 112 total dimensions
3. **Isolation Forest**: Identifies logs that are "easy to isolate" from normal patterns
4. **Anomaly Scoring**: Each log gets a probability score (0-1)

## 🚀 Quick Start

### Prerequisites

- Snowflake account with appropriate privileges
- Python 3.10+
- Private key for Snowflake authentication (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/sfc-gh-vbatra/log_anomaly_detector.git
cd log_anomaly_detector

# Install dependencies
pip install -r snowflake_requirements.txt

# Configure Snowflake connection
cd snowflake
cp snowflake_config.json.example snowflake_config.json
# Edit snowflake_config.json with your credentials

# Set up Snowflake database objects
snowsql -f setup.sql

# Test connection
python test_connection.py
```

### Run Analysis

```bash
# Upload logs
python upload_logs.py path/to/your/logfile.log

# Run anomaly detection
python snowpark_analyzer.py

# Launch interactive dashboard
streamlit run streamlit_app.py
# Visit: http://localhost:8501
```

## 📁 Project Structure

```
snowflake/
├── setup.sql                      # Snowflake database setup
├── snowpark_analyzer.py           # Main ML engine (TF-IDF + Isolation Forest)
├── streamlit_app.py              # Interactive dashboard with cluster viz
├── stored_procedures.sql         # SQL callable procedures
├── upload_logs.py                # Efficient log uploader
├── test_connection.py            # Connection tester
├── explain_anomalies.py          # Anomaly explainability tool
├── setup_keypair_auth.py         # Key-pair authentication setup
├── quick_start.py                # Automated testing script
├── snowflake_config.json.example # Configuration template
├── KEYPAIR_AUTH_SETUP.md         # Security guide
└── README.md                     # Quick reference
```

## 🔐 Security: Key-Pair Authentication

This system uses **key-pair authentication** (recommended for production):

```bash
# Generate key pair
cd snowflake
python setup_keypair_auth.py

# Register public key in Snowflake
ALTER USER your_username SET RSA_PUBLIC_KEY='<your_public_key>';

# Update config
# Edit snowflake_config.json with private key path
```

See [KEYPAIR_AUTH_SETUP.md](snowflake/KEYPAIR_AUTH_SETUP.md) for detailed instructions.

## 🎨 Interactive Dashboard

The Streamlit dashboard provides:

### 📊 Dashboard Tab
- Real-time statistics
- Anomaly distribution charts
- Summary tables

### 🔮 Cluster View Tab
- **NEW!** 2D visualization of 112-dimensional feature space
- Green dots = Normal logs (clustered)
- Red dots = Anomalous logs (isolated)
- Interactive hover details
- PCA projection with variance explained

### 🚀 Run Analysis Tab
- Configure contamination factor (1-50%)
- Set TF-IDF features (50-500)
- Run analysis on selected files
- View top anomalies

### 📈 History Tab
- Analysis trends over time
- Historical statistics
- Performance tracking

## 🔍 Understanding Anomalies

Logs are flagged as anomalous based on:

1. **Security Indicators** (55% confidence)
   - Failed login attempts
   - Account lockouts
   - Unauthorized access

2. **Rarity** (30% confidence)
   - Messages appearing <5% of time
   - Unique error patterns

3. **Length Anomalies** (10% confidence)
   - Unusually verbose/terse messages

4. **TF-IDF Patterns** (variable)
   - Rare word combinations
   - Unusual semantic content

### Example

```
Message: "failed login attempts, account locked"
Anomaly Probability: 0.4856 (High)

Why anomalous?
• 🚫 Contains "failed" (failure indicator)
• 🔐 Contains "locked" (security event)
• 📉 Appears in only 3.3% of logs (rare)
• 📏 39 chars vs average 24 chars (62% longer)
```

Run `python explain_anomalies.py` for detailed analysis!

## 🎛️ Tuning Parameters

### Contamination Factor

Controls how many logs are flagged:

| Value | Use Case |
|-------|----------|
| 0.01 (1%) | Production monitoring (strict) |
| 0.05 (5%) | Security analysis |
| **0.10 (10%)** | **General analysis** ✅ |
| 0.15 (15%) | Development/debugging |
| 0.30 (30%) | Exploratory analysis |

### TF-IDF Features

Controls semantic analysis depth:

| Value | Best For |
|-------|----------|
| 50 | Large datasets (>100K logs) |
| **100** | **Most use cases** ✅ |
| 200 | Security/forensics |
| 500 | Research/deep analysis |

## 📚 SQL Queries

### View Anomalies

```sql
-- Top anomalies
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
ORDER BY anomaly_probability DESC 
LIMIT 20;

-- Search patterns
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
AND MESSAGE LIKE '%failed%'
ORDER BY anomaly_probability DESC;

-- Summary statistics
SELECT * FROM anomaly_summary;

-- Analysis history
SELECT * FROM anomaly_runs 
ORDER BY run_timestamp DESC;
```

### Run via Stored Procedures

```sql
-- Parse logs
CALL parse_raw_logs('ALL');

-- Detect anomalies (10% contamination, 100 TF-IDF features)
CALL detect_log_anomalies('ALL', 0.1, 100);
```

## 🔧 Advanced Usage

### Python API

```python
from snowflake.snowpark import Session
from snowpark_analyzer import SnowparkLogAnalyzer, load_snowflake_config

# Connect
config = load_snowflake_config('snowflake_config.json')
session = Session.builder.configs(config).create()

# Analyze
analyzer = SnowparkLogAnalyzer(session)
results = analyzer.run_full_pipeline(
    contamination=0.1,    # 10% expected anomalies
    max_features=100      # TF-IDF features
)

# View top anomalies
anomalies = results[results['is_anomaly'] == True]
print(f"Found {len(anomalies)} anomalies")

# Save model for reuse
analyzer.save_model('./models')

session.close()
```

### Batch Processing

```python
# Process multiple files
log_files = ['app.log', 'server.log', 'security.log']

for log_file in log_files:
    analyzer.run_full_pipeline(
        file_name=log_file,
        contamination=0.1,
        max_features=100
    )
```

## 📈 Performance

- **Scalability**: Handles millions of logs via Snowflake compute
- **Speed**: Vectorization + ML in minutes (not hours)
- **Efficiency**: Bulk operations via Snowpark
- **Storage**: All results persisted in Snowflake tables

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Isolation Forest**: Liu et al. (2008)
- **TF-IDF**: Salton & McGill (1983)
- **Snowflake**: For the amazing platform
- **scikit-learn**: For ML algorithms

## 📞 Support

- 📖 [Full Deployment Guide](SNOWFLAKE_DEPLOYMENT_GUIDE.md)
- 🔐 [Key-Pair Auth Setup](snowflake/KEYPAIR_AUTH_SETUP.md)
- 🔍 [Anomaly Detection Explained](snowflake/ANOMALY_DETECTION_EXPLAINED.md)
- 💬 Issues: [GitHub Issues](https://github.com/sfc-gh-vbatra/log_anomaly_detector/issues)

## 🌟 Star This Repo

If you find this useful, please ⭐ star this repository!

---

**Built with ❤️ for the Snowflake community**

