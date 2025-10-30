#!/usr/bin/env python3
"""
Quick Start Script for Snowflake Log Anomaly Detection
Run this after completing setup.sql to test the system
"""

import sys
import json
import os
from pathlib import Path

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_config():
    """Check if configuration file exists."""
    if not os.path.exists('snowflake_config.json'):
        print("❌ Configuration file not found!")
        print("\n📝 Please create snowflake_config.json:")
        print("   cp snowflake_config.json.example snowflake_config.json")
        print("   # Then edit with your credentials")
        return False
    return True

def test_connection():
    """Test Snowflake connection."""
    print_header("Testing Snowflake Connection")
    
    try:
        from snowflake.snowpark import Session
        from snowpark_analyzer import load_snowflake_config
        
        print("📡 Loading configuration...")
        config = load_snowflake_config('snowflake_config.json')
        
        print("🔌 Connecting to Snowflake...")
        session = Session.builder.configs(config).create()
        
        account = session.get_current_account()
        database = session.get_current_database()
        schema = session.get_current_schema()
        warehouse = session.get_current_warehouse()
        
        print(f"✅ Connected successfully!")
        print(f"   Account: {account}")
        print(f"   Database: {database}")
        print(f"   Schema: {schema}")
        print(f"   Warehouse: {warehouse}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def check_tables():
    """Verify required tables exist."""
    print_header("Checking Database Tables")
    
    try:
        from snowflake.snowpark import Session
        from snowpark_analyzer import load_snowflake_config
        
        config = load_snowflake_config('snowflake_config.json')
        session = Session.builder.configs(config).create()
        
        required_tables = ['RAW_LOGS', 'PARSED_LOGS', 'ANOMALY_RESULTS', 'ANOMALY_RUNS']
        
        for table in required_tables:
            try:
                count = session.sql(f"SELECT COUNT(*) FROM {table}").collect()[0][0]
                print(f"✅ {table}: {count} rows")
            except Exception as e:
                print(f"❌ {table}: Not found or error")
                print(f"   Run setup.sql first: snowsql -f setup.sql")
                session.close()
                return False
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def upload_sample_logs():
    """Upload sample log data."""
    print_header("Uploading Sample Logs")
    
    # Check if sample log exists
    sample_log = Path('../logs/test.txt')
    if not sample_log.exists():
        print("⚠️  No sample log file found at ../logs/test.txt")
        print("   Creating a sample log file...")
        
        # Create sample logs
        sample_data = """2025-10-30 10:00:01 INFO Application started successfully
2025-10-30 10:00:05 INFO User login: user123
2025-10-30 10:00:10 INFO Processing request from 192.168.1.100
2025-10-30 10:00:15 ERROR Database connection failed: timeout after 30s
2025-10-30 10:00:20 WARNING Retry attempt 1/3
2025-10-30 10:00:25 ERROR Database connection failed: timeout after 30s
2025-10-30 10:00:30 WARNING Retry attempt 2/3
2025-10-30 10:00:35 INFO Database connection established
2025-10-30 10:00:40 INFO Query executed successfully
2025-10-30 10:00:45 INFO User logout: user123
2025-10-30 10:00:50 CRITICAL Unauthorized access attempt from 10.0.0.1
2025-10-30 10:00:55 ERROR Authentication failed for user: hacker
2025-10-30 10:01:00 WARNING Multiple failed login attempts detected
2025-10-30 10:01:05 INFO Security alert triggered
2025-10-30 10:01:10 INFO System normal operation resumed"""
        
        sample_log.parent.mkdir(exist_ok=True)
        with open(sample_log, 'w') as f:
            f.write(sample_data)
        print(f"✅ Created sample log at {sample_log}")
    
    try:
        from snowflake.snowpark import Session
        from snowpark_analyzer import load_snowflake_config
        import pandas as pd
        
        config = load_snowflake_config('snowflake_config.json')
        session = Session.builder.configs(config).create()
        
        # Read log file
        with open(sample_log, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        print(f"📤 Uploading {len(lines)} log lines...")
        
        # Insert lines one by one or in batches using explicit SQL
        # This allows auto-increment and default values to work
        for i, line in enumerate(lines):
            if i % 50 == 0 and i > 0:
                print(f"   Progress: {i}/{len(lines)} lines...")
            
            # Escape single quotes in the line
            escaped_line = line.replace("'", "''")
            escaped_filename = sample_log.name.replace("'", "''")
            
            session.sql(f"""
                INSERT INTO raw_logs (file_name, raw_line) 
                VALUES ('{escaped_filename}', '{escaped_line}')
            """).collect()
        
        print(f"✅ Uploaded {len(lines)} log lines to RAW_LOGS")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def run_analysis():
    """Run anomaly detection."""
    print_header("Running Anomaly Detection")
    
    try:
        from snowflake.snowpark import Session
        from snowpark_analyzer import SnowparkLogAnalyzer, load_snowflake_config
        
        config = load_snowflake_config('snowflake_config.json')
        session = Session.builder.configs(config).create()
        
        print("🤖 Initializing analyzer with TF-IDF vectorization...")
        analyzer = SnowparkLogAnalyzer(session)
        
        print("📊 Running full pipeline...")
        print("   - Parsing logs")
        print("   - Extracting features")
        print("   - Vectorizing with TF-IDF (100 features)")
        print("   - Training Isolation Forest")
        print("   - Detecting anomalies (10% contamination)")
        
        results = analyzer.run_full_pipeline(
            file_name=None,
            contamination=0.1,
            max_features=100
        )
        
        if not results.empty:
            anomaly_count = results['is_anomaly'].sum()
            total_count = len(results)
            
            print(f"\n✅ Analysis Complete!")
            print(f"   Total Logs: {total_count}")
            print(f"   Anomalies: {anomaly_count} ({100*anomaly_count/total_count:.1f}%)")
            
            # Show top anomalies
            anomalies = results[results['is_anomaly'] == True].sort_values(
                'anomaly_probability', ascending=False
            ).head(5)
            
            if not anomalies.empty:
                print("\n🚨 Top 5 Anomalies:")
                for idx, row in anomalies.iterrows():
                    print(f"   {row['LOG_LEVEL']}: {row['MESSAGE'][:60]}...")
                    print(f"      Probability: {row['anomaly_probability']:.4f}")
        else:
            print("⚠️  No results generated")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_results():
    """Display results summary."""
    print_header("Viewing Results")
    
    try:
        from snowflake.snowpark import Session
        from snowpark_analyzer import load_snowflake_config
        
        config = load_snowflake_config('snowflake_config.json')
        session = Session.builder.configs(config).create()
        
        # Query summary
        summary = session.sql("SELECT * FROM anomaly_summary").to_pandas()
        
        if not summary.empty:
            print("📊 Anomaly Summary:")
            for _, row in summary.iterrows():
                print(f"\n   File: {row['FILE_NAME']}")
                print(f"   Total Logs: {row['TOTAL_LOGS']}")
                print(f"   Anomalies: {row['ANOMALY_COUNT']} ({row['ANOMALY_PERCENTAGE']:.1f}%)")
        else:
            print("ℹ️  No summary data available")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error viewing results: {e}")
        return False

def main():
    """Main execution flow."""
    print_header("Snowflake Log Anomaly Detection - Quick Start")
    print("This script will test your Snowflake setup and run a sample analysis")
    
    # Step 1: Check configuration
    if not check_config():
        sys.exit(1)
    
    # Step 2: Test connection
    if not test_connection():
        print("\n💡 Tip: Check your snowflake_config.json credentials")
        sys.exit(1)
    
    # Step 3: Check tables
    if not check_tables():
        print("\n💡 Tip: Run the setup script first:")
        print("   snowsql -f setup.sql")
        sys.exit(1)
    
    # Step 4: Upload sample logs
    if not upload_sample_logs():
        sys.exit(1)
    
    # Step 5: Run analysis
    if not run_analysis():
        sys.exit(1)
    
    # Step 6: Show results
    show_results()
    
    # Final instructions
    print_header("🎉 Quick Start Complete!")
    print("\n📍 Next Steps:")
    print("   1. View results in Snowflake:")
    print("      SELECT * FROM anomaly_results WHERE is_anomaly = TRUE;")
    print("\n   2. Launch Streamlit UI:")
    print("      streamlit run streamlit_app.py")
    print("\n   3. Upload your own logs:")
    print("      Use the Streamlit app or Python API")
    print("\n   4. Read the full guide:")
    print("      See SNOWFLAKE_DEPLOYMENT_GUIDE.md")
    print("\n✨ Happy anomaly hunting! 🔍")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

