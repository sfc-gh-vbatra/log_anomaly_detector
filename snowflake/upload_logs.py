#!/usr/bin/env python3
"""
Efficiently upload log files to Snowflake
"""

import sys
from pathlib import Path
from snowflake.snowpark import Session
from snowpark_analyzer import load_snowflake_config

def upload_log_file(log_file_path, session):
    """Upload a log file to Snowflake raw_logs table."""
    
    log_file = Path(log_file_path)
    if not log_file.exists():
        print(f"❌ File not found: {log_file_path}")
        return False
    
    print(f"\n📄 Reading file: {log_file.name}")
    with open(log_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    print(f"📊 Found {len(lines)} log lines")
    
    # Create a temporary table to load data
    print("📤 Uploading to Snowflake...")
    
    # Use Snowpark's efficient bulk upload
    import pandas as pd
    df = pd.DataFrame({
        'FILE_NAME': [log_file.name] * len(lines),
        'RAW_LINE': lines
    })
    
    # Create temp table
    temp_table = "TEMP_LOGS_UPLOAD"
    sp_df = session.create_dataframe(df)
    sp_df.write.mode("overwrite").save_as_table(temp_table)
    
    print("💾 Inserting into raw_logs...")
    # Insert from temp table to raw_logs (auto-increment will work)
    result = session.sql(f"""
        INSERT INTO raw_logs (file_name, raw_line)
        SELECT FILE_NAME, RAW_LINE FROM {temp_table}
    """).collect()
    
    # Drop temp table
    session.sql(f"DROP TABLE IF EXISTS {temp_table}").collect()
    
    print(f"✅ Successfully uploaded {len(lines)} log lines!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_logs.py <log_file_path>")
        print("\nExample:")
        print("  python upload_logs.py ../logs/test.txt")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    print("🔌 Connecting to Snowflake...")
    config = load_snowflake_config('snowflake_config.json')
    session = Session.builder.configs(config).create()
    print("✅ Connected!")
    
    success = upload_log_file(log_file, session)
    
    if success:
        # Show what was uploaded
        count = session.sql("SELECT COUNT(*) FROM raw_logs").collect()[0][0]
        print(f"\n📊 Total logs in database: {count}")
    
    session.close()
    sys.exit(0 if success else 1)

