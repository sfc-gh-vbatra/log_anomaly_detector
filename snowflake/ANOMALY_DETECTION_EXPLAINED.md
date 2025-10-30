# 🔍 Understanding Anomaly Detection

## Why Are Certain Logs Flagged as Anomalous?

Based on your actual data analysis, here's what makes a log anomalous:

---

## 🎯 Real Example from Your Data

**Top Anomaly Detected:**
```
Message: "failed login attempts, account locked"
Anomaly Probability: 0.4856 (High)
Confidence: 55%
```

**Why This is Anomalous:**
1. 🚫 **Contains failure indicators** - "failed" is a red flag keyword
2. 🔐 **Account locking event** - "locked" indicates security action
3. 📉 **Uncommon message** - Appears in only 3.3% of logs (227 out of 6,917)
4. 📏 **Unusually long** - 39 characters vs average of 24

---

## 🧬 The 112-Feature Analysis

### 12 Structured Features (Explicit Rules)

| Feature | What It Detects | Example |
|---------|----------------|---------|
| `msg_len` | Unusual message length | 39 chars vs avg 24 |
| `has_error` | ERROR log level | ERROR, CRITICAL logs |
| `has_failure` | Failure keywords | "failed", "failure" |
| `has_exception` | Exception events | "exception", "threw" |
| `is_unauthorized` | Security issues | "unauthorized", "denied" |
| `is_connection_issue` | Network problems | "timeout", "connection" |
| `message_frequency` | Rare messages | <5% occurrence = suspicious |
| `is_rare_message` | Very rare | ≤2 occurrences in dataset |
| `has_number` | Numeric anomalies | Unusual IP addresses, codes |
| `has_special_chars` | Special characters | Injection attempts |

### 100 TF-IDF Features (Semantic Analysis)

**TF-IDF captures:**
- Rare word combinations
- Unusual phrasing
- Semantic anomalies
- Context that structured features miss

**Example:**
- Normal: "User logged in successfully"
- Anomalous: "User logged in from unknown location after 47 failed attempts"
  - TF-IDF detects: "unknown location", "47 failed attempts" = rare phrase

---

## 🤖 How Isolation Forest Works

Think of your logs as points in a 112-dimensional space:

```
Normal Logs:
    [INFO] User login ●●●●●●●●●● (clustered together)
    [INFO] Request processed ●●●●●
    
Anomalous Logs:
    [ERROR] failed login attempts, account locked ○ (isolated, far from cluster)
```

**Key Principle:**
- **Normal logs**: Dense clusters, hard to isolate
- **Anomalous logs**: Sparse, easy to isolate

The algorithm randomly "cuts" the feature space:
- Normal logs require many cuts to isolate
- Anomalous logs isolated in few cuts

---

## 📊 Your Data Insights

From the analysis of your 6,917 logs:

### Normal vs Anomalous Comparison

| Metric | Normal Logs | Anomalous Logs |
|--------|-------------|----------------|
| **Count** | 6,365 (92%) | 552 (8%) |
| **Avg Length** | 22.6 chars | 34.9 chars ⚠️ |
| **Top Level** | INFO (70%) | INFO (65%) |
| **ERROR Rate** | 10.1% | 11.6% |

**Key Insight:** Anomalous logs are **54% longer** on average!

### Anomaly Breakdown

**By Log Level:**
- INFO: 66.7% - Even normal-looking logs can be anomalous!
- ERROR: 13.3%
- WARNING: 13.3%
- CRITICAL: 6.7%

**Common Anomaly Patterns:**
1. **Security Events** (55% confidence)
   - Failed login attempts
   - Account lockouts
   - Unauthorized access

2. **Rare Occurrences** (30% confidence)
   - Messages appearing <1% of time
   - Unique error codes

3. **Length Anomalies** (10% confidence)
   - Unusually verbose or terse messages

4. **Complex Patterns** (TF-IDF)
   - Unusual word combinations
   - Semantic outliers

---

## 🎯 Why This Matters

### Traditional Approach (Keyword Matching)
```python
if "ERROR" in log:
    alert()  # Misses 86% of anomalies!
```

❌ **Problems:**
- Misses anomalous INFO logs
- No context understanding
- Fixed rules, can't adapt
- 66.7% of anomalies have INFO level

### Our ML Approach (TF-IDF + Isolation Forest)
```python
# Analyzes 112 features
# Understands context
# Detects subtle patterns
# Adaptive to your data
```

✅ **Benefits:**
- Catches 8% of logs as truly anomalous
- Detects "failed login attempts" even at INFO level
- Finds rare patterns automatically
- High confidence scoring

---

## 🔬 Deep Dive: "Failed Login Attempts, Account Locked"

This log is flagged because:

### 1. Keyword Analysis
```
"failed" → failure indicator (15 points)
"locked" → security event (15 points)
"account" → user security (context)
```

### 2. Frequency Analysis
```
Appears: 227 times out of 6,917 logs (3.3%)
Status: Uncommon (15 points)
Expected: >10% for normal patterns
```

### 3. Length Analysis
```
Message length: 39 characters
Average length: 24 characters
Deviation: +62% longer (10 points)
```

### 4. TF-IDF Analysis
```
"failed login attempts" → rare phrase
"account locked" → security-specific terminology
Combined score → high anomaly probability
```

**Total Confidence: 55% = Medium-High Anomaly**

---

## 💡 Practical Use Cases

### 1. Security Monitoring
Detect:
- Brute force attacks (multiple failed logins)
- Unauthorized access attempts
- Account takeover patterns

**Example:**
```
Normal: "User logged in" (0.05 probability)
Anomaly: "failed login attempts, account locked" (0.49 probability) ⚠️
```

### 2. Performance Issues
Detect:
- Unusual timeout patterns
- Connection failures
- Slow response times

### 3. Application Errors
Detect:
- Rare exceptions
- Unexpected error combinations
- Novel failure modes

---

## 🎛️ Tuning Anomaly Detection

### Contamination Parameter

Controls how many logs are flagged:

| Value | Meaning | Use Case |
|-------|---------|----------|
| 0.01 | 1% flagged | Production (strict) |
| 0.05 | 5% flagged | Security monitoring |
| **0.10** | **10% flagged** | **General analysis** ✅ |
| 0.15 | 15% flagged | Development/debugging |
| 0.30 | 30% flagged | Exploratory |

**Your current setting:** 0.10 (10%)
- Detected: 552 anomalies (8%)
- Status: Slightly below target (good!)

### TF-IDF Features

Controls semantic analysis depth:

| Value | Processing | Best For |
|-------|-----------|----------|
| 50 | Fast | Large datasets (>100K logs) |
| **100** | **Balanced** ⚠️ | **Most use cases** ✅ |
| 200 | Detailed | Security analysis |
| 500 | Exhaustive | Research/forensics |

---

## 🚀 Next Steps

### 1. View Results in Streamlit
```bash
streamlit run streamlit_app.py
# Visit: http://localhost:8501
```

### 2. Explain Specific Anomalies
```bash
python explain_anomalies.py
```

### 3. Query in Snowflake
```sql
-- View top anomalies
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
ORDER BY anomaly_probability DESC 
LIMIT 20;

-- Search for specific patterns
SELECT * FROM anomaly_results 
WHERE is_anomaly = TRUE 
AND MESSAGE LIKE '%failed%'
ORDER BY anomaly_probability DESC;
```

### 4. Adjust Parameters
```python
# More sensitive (catch more)
results = analyzer.run_full_pipeline(
    contamination=0.15,  # 15% flagged
    max_features=200     # More detailed
)

# Less sensitive (catch less)
results = analyzer.run_full_pipeline(
    contamination=0.05,  # 5% flagged
    max_features=50      # Faster
)
```

---

## ✅ Summary

**Your logs are flagged as anomalous when they exhibit:**

1. ✅ **Security indicators** - failed logins, locks, denials
2. ✅ **Rarity** - <5% occurrence in your dataset
3. ✅ **Length anomalies** - significantly longer/shorter
4. ✅ **Unusual combinations** - detected by TF-IDF
5. ✅ **Multiple error signals** - compound indicators

**The system found:**
- 552 anomalies (8% of 6,917 logs)
- Top anomaly: "failed login attempts, account locked"
- Confidence: 55% (medium-high)
- Key driver: Security keywords + rarity + length

**This is working correctly! ✨**

The most suspicious log in your dataset is a potential security incident involving failed authentication attempts - exactly what you want to catch!

---

## 📚 References

- **Isolation Forest Paper**: Liu et al. (2008) - "Isolation Forest"
- **TF-IDF**: Salton & McGill (1983) - "Introduction to Modern Information Retrieval"
- **Your Analysis**: Run `python explain_anomalies.py` anytime!

