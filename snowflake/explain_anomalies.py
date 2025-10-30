#!/usr/bin/env python3
"""
Explain why specific logs were flagged as anomalies
Provides human-readable reasoning for anomaly detection results
"""

from snowflake.snowpark import Session
from snowpark_analyzer import load_snowflake_config
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def explain_anomaly(log_entry, all_logs_df):
    """
    Explain why a specific log was flagged as an anomaly.
    
    Args:
        log_entry: Row from the anomaly results
        all_logs_df: DataFrame with all logs for comparison
    """
    reasons = []
    score = 0
    
    # Parse the log entry
    message = log_entry.get('MESSAGE', '')
    log_level = log_entry.get('LOG_LEVEL', 'INFO')
    msg_len = len(message)
    
    # 1. Check log level severity
    if log_level in ['ERROR', 'CRITICAL']:
        reasons.append(f"❗ High severity level: {log_level}")
        score += 25
    
    # 2. Check for critical keywords
    keywords = {
        'fail': '🚫 Contains failure indicators',
        'exception': '💥 Exception detected',
        'unauthorized': '🔒 Unauthorized access attempt',
        'timeout': '⏱️  Timeout issue',
        'connection': '🔌 Connection problem',
        'denied': '⛔ Access denied',
        'attack': '⚠️  Potential security threat',
        'locked': '🔐 Account locking event',
        'breach': '🚨 Security breach indicator',
        'malicious': '☠️  Malicious activity'
    }
    
    message_lower = message.lower()
    for keyword, description in keywords.items():
        if keyword in message_lower:
            reasons.append(f"{description}")
            score += 15
    
    # 3. Check message frequency (rarity)
    message_counts = all_logs_df['MESSAGE'].value_counts()
    frequency = message_counts.get(message, 0)
    total_logs = len(all_logs_df)
    rarity_pct = (frequency / total_logs) * 100
    
    if rarity_pct < 1:
        reasons.append(f"🦄 Extremely rare message (appears {frequency} times, {rarity_pct:.2f}% of logs)")
        score += 30
    elif rarity_pct < 5:
        reasons.append(f"📉 Uncommon message (appears {frequency} times, {rarity_pct:.1f}% of logs)")
        score += 15
    
    # 4. Check message length anomaly
    avg_length = all_logs_df['MESSAGE'].str.len().mean()
    std_length = all_logs_df['MESSAGE'].str.len().std()
    
    if msg_len > avg_length + (2 * std_length):
        reasons.append(f"📏 Unusually long message ({msg_len} chars vs avg {avg_length:.0f})")
        score += 10
    elif msg_len < avg_length - (2 * std_length):
        reasons.append(f"📏 Unusually short message ({msg_len} chars vs avg {avg_length:.0f})")
        score += 10
    
    # 5. Check for special characters
    special_chars = sum(not c.isalnum() and not c.isspace() for c in message)
    if special_chars > 10:
        reasons.append(f"🔣 High special character count ({special_chars} characters)")
        score += 5
    
    # 6. Check for numeric anomalies
    import re
    numbers = re.findall(r'\d+', message)
    if len(numbers) > 5:
        reasons.append(f"🔢 Multiple numeric values ({len(numbers)} numbers found)")
        score += 5
    
    # 7. Multiple error indicators
    error_indicators = ['error', 'fail', 'exception', 'denied', 'invalid', 'unable', 'cannot']
    error_count = sum(1 for indicator in error_indicators if indicator in message_lower)
    if error_count >= 2:
        reasons.append(f"⚡ Multiple error indicators ({error_count} error-related terms)")
        score += 10
    
    return reasons, min(score, 100)


def analyze_top_anomalies(session, limit=10):
    """Analyze and explain the top anomalies."""
    
    print("=" * 80)
    print("  🔍 ANOMALY EXPLANATION REPORT")
    print("=" * 80)
    
    # Load anomaly results
    print("\n📊 Loading anomaly data from Snowflake...")
    anomalies_query = f"""
        SELECT * FROM anomaly_results 
        WHERE is_anomaly = TRUE 
        ORDER BY anomaly_probability DESC 
        LIMIT {limit}
    """
    anomalies_df = session.sql(anomalies_query).to_pandas()
    
    # Load all logs for comparison
    all_logs_df = session.sql("SELECT * FROM anomaly_results").to_pandas()
    
    if anomalies_df.empty:
        print("⚠️  No anomalies found!")
        return
    
    print(f"✅ Analyzing top {len(anomalies_df)} anomalies out of {len(all_logs_df)} total logs\n")
    
    # Analyze each anomaly
    for idx, row in anomalies_df.iterrows():
        print("─" * 80)
        print(f"\n🚨 ANOMALY #{idx + 1}")
        print(f"   Anomaly Probability: {row['ANOMALY_PROBABILITY']:.4f}")
        print(f"   Log Level: {row['LOG_LEVEL']}")
        print(f"   Message: {row['MESSAGE'][:100]}{'...' if len(row['MESSAGE']) > 100 else ''}")
        
        # Get explanation
        reasons, confidence = explain_anomaly(row, all_logs_df)
        
        print(f"\n   📋 Why This is Anomalous (Confidence: {confidence}%):")
        if reasons:
            for reason in reasons:
                print(f"      • {reason}")
        else:
            print("      • Complex pattern detected by TF-IDF vectorization")
            print("      • Unusual combination of words/features")
        
        print()
    
    print("=" * 80)
    
    # Summary statistics
    print("\n📈 ANOMALY STATISTICS\n")
    
    # By log level
    level_counts = anomalies_df['LOG_LEVEL'].value_counts()
    print("   Anomalies by Log Level:")
    for level, count in level_counts.items():
        pct = (count / len(anomalies_df)) * 100
        print(f"      {level:12} : {count:4} ({pct:5.1f}%)")
    
    # Average probability
    avg_prob = anomalies_df['ANOMALY_PROBABILITY'].mean()
    max_prob = anomalies_df['ANOMALY_PROBABILITY'].max()
    min_prob = anomalies_df['ANOMALY_PROBABILITY'].min()
    
    print(f"\n   Anomaly Probability Range:")
    print(f"      Average : {avg_prob:.4f}")
    print(f"      Maximum : {max_prob:.4f}")
    print(f"      Minimum : {min_prob:.4f}")
    
    print("\n" + "=" * 80)


def compare_normal_vs_anomaly(session):
    """Compare characteristics of normal vs anomalous logs."""
    
    print("\n" + "=" * 80)
    print("  📊 NORMAL vs ANOMALOUS LOGS COMPARISON")
    print("=" * 80 + "\n")
    
    df = session.sql("SELECT * FROM anomaly_results").to_pandas()
    
    normal = df[df['IS_ANOMALY'] == False]
    anomalous = df[df['IS_ANOMALY'] == True]
    
    print(f"   Normal Logs    : {len(normal):5} ({len(normal)/len(df)*100:5.1f}%)")
    print(f"   Anomalous Logs : {len(anomalous):5} ({len(anomalous)/len(df)*100:5.1f}%)")
    
    print("\n   Message Length:")
    print(f"      Normal    : {normal['MESSAGE'].str.len().mean():6.1f} chars (avg)")
    print(f"      Anomalous : {anomalous['MESSAGE'].str.len().mean():6.1f} chars (avg)")
    
    print("\n   Log Level Distribution:")
    print("\n   Normal Logs:")
    for level, count in normal['LOG_LEVEL'].value_counts().head(5).items():
        pct = (count / len(normal)) * 100
        print(f"      {level:12} : {pct:5.1f}%")
    
    print("\n   Anomalous Logs:")
    for level, count in anomalous['LOG_LEVEL'].value_counts().head(5).items():
        pct = (count / len(anomalous)) * 100
        print(f"      {level:12} : {pct:5.1f}%")
    
    print("\n" + "=" * 80)


def interactive_search(session):
    """Interactive search for specific log patterns."""
    
    print("\n" + "=" * 80)
    print("  🔎 SEARCH SPECIFIC ANOMALIES")
    print("=" * 80 + "\n")
    
    print("Search for anomalies containing specific keywords:")
    print("Examples: 'failed', 'unauthorized', 'timeout', 'exception'\n")
    
    keyword = input("Enter keyword to search (or press Enter to skip): ").strip()
    
    if keyword:
        query = f"""
            SELECT LOG_LEVEL, MESSAGE, ANOMALY_PROBABILITY 
            FROM anomaly_results 
            WHERE IS_ANOMALY = TRUE 
            AND LOWER(MESSAGE) LIKE LOWER('%{keyword}%')
            ORDER BY ANOMALY_PROBABILITY DESC 
            LIMIT 10
        """
        results = session.sql(query).to_pandas()
        
        if not results.empty:
            print(f"\n✅ Found {len(results)} anomalies containing '{keyword}':\n")
            for idx, row in results.iterrows():
                print(f"   {idx+1}. [{row['LOG_LEVEL']}] {row['MESSAGE'][:70]}...")
                print(f"      Probability: {row['ANOMALY_PROBABILITY']:.4f}\n")
        else:
            print(f"\n⚠️  No anomalies found containing '{keyword}'")


if __name__ == "__main__":
    print("\n🔌 Connecting to Snowflake...")
    config = load_snowflake_config('snowflake_config.json')
    session = Session.builder.configs(config).create()
    print("✅ Connected!\n")
    
    # Main analysis
    analyze_top_anomalies(session, limit=15)
    
    # Comparison
    compare_normal_vs_anomaly(session)
    
    # Interactive search
    # interactive_search(session)
    
    print("\n💡 TIP: Anomalies are detected using 112 features:")
    print("   • 12 structured features (errors, patterns, frequency)")
    print("   • 100 TF-IDF features (semantic text analysis)")
    print("   • Isolation Forest identifies unusual combinations\n")
    
    session.close()
    print("✅ Analysis complete!\n")

