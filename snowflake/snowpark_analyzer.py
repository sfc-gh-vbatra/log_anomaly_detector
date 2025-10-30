"""
Snowpark-based Log Analyzer with Text Vectorization and Isolation Forest
Vectorizes log messages using TF-IDF and detects anomalies using Isolation Forest
"""

import pandas as pd
import numpy as np
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, udf, sproc
from snowflake.snowpark.types import (
    StructType, StructField, StringType, IntegerType, 
    FloatType, BooleanType, TimestampType
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import re
import joblib
import os


class SnowparkLogAnalyzer:
    """
    Log Analyzer that works with Snowflake using Snowpark.
    Vectorizes logs using TF-IDF and detects anomalies using Isolation Forest.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.vectorizer = None
        self.model = None
        self.scaler = StandardScaler()
        
    def parse_logs_from_stage(self, stage_name: str, file_pattern: str, target_table: str = "raw_logs"):
        """
        Load logs from Snowflake stage into raw_logs table.
        
        Args:
            stage_name: Name of the stage containing log files
            file_pattern: Pattern to match files (e.g., '*.log' or '*.txt')
            target_table: Target table name (default: raw_logs)
        """
        copy_sql = f"""
        COPY INTO {target_table} (file_name, raw_line)
        FROM (
            SELECT 
                METADATA$FILENAME as file_name,
                $1 as raw_line
            FROM @{stage_name}/{file_pattern}
        )
        FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = 'NONE' RECORD_DELIMITER = '\\n')
        ON_ERROR = 'CONTINUE'
        """
        
        self.session.sql(copy_sql).collect()
        print(f"✅ Loaded logs from stage {stage_name} into {target_table}")
        
    def parse_log_structure(self, raw_logs_df):
        """
        Parse raw log lines into structured format.
        Extracts timestamp, log level, and message.
        
        Args:
            raw_logs_df: Snowpark DataFrame with raw log lines
            
        Returns:
            Snowpark DataFrame with parsed structure
        """
        # Define UDF to parse log lines
        @udf(return_type=StructType([
            StructField("log_level", StringType()),
            StructField("message", StringType()),
            StructField("timestamp_str", StringType())
        ]))
        def parse_log_line(line: str) -> dict:
            if not line:
                return {"log_level": "INFO", "message": "", "timestamp_str": None}
            
            # Extract timestamp (e.g., 2025-03-27 10:00:36)
            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*', line)
            timestamp_str = timestamp_match.group(1) if timestamp_match else None
            
            # Remove timestamp from line
            cleaned_line = re.sub(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*', '', line)
            
            # Extract log level
            log_level = "INFO"  # default
            if "ERROR" in cleaned_line:
                log_level = "ERROR"
            elif "WARNING" in cleaned_line or "WARN" in cleaned_line:
                log_level = "WARNING"
            elif "CRITICAL" in cleaned_line or "FATAL" in cleaned_line:
                log_level = "CRITICAL"
            elif "DEBUG" in cleaned_line:
                log_level = "DEBUG"
            elif "SUMMARY" in cleaned_line:
                log_level = "SUMMARY"
            
            # Extract message (typically after log level)
            message_parts = cleaned_line.split(None, 2)
            message = message_parts[2] if len(message_parts) > 2 else cleaned_line
            
            return {
                "log_level": log_level,
                "message": message,
                "timestamp_str": timestamp_str
            }
        
        # Apply parsing
        parsed_df = raw_logs_df.select(
            col("LOG_ID"),
            col("FILE_NAME"),
            parse_log_line(col("RAW_LINE")).alias("parsed")
        ).select(
            col("LOG_ID"),
            col("FILE_NAME"),
            col("parsed")["log_level"].alias("LOG_LEVEL"),
            col("parsed")["message"].alias("MESSAGE"),
            col("parsed")["timestamp_str"].alias("TIMESTAMP_EXTRACTED")
        )
        
        return parsed_df
    
    def extract_features_and_vectorize(self, parsed_logs_df, max_features=100, contamination=0.1):
        """
        Extract features from parsed logs and vectorize using TF-IDF.
        Then detect anomalies using Isolation Forest.
        
        Args:
            parsed_logs_df: Snowpark DataFrame with parsed logs
            max_features: Maximum number of TF-IDF features (default: 100)
            contamination: Expected proportion of anomalies (default: 0.1)
            
        Returns:
            Pandas DataFrame with features, vectors, and anomaly scores
        """
        # Convert to Pandas for ML processing
        df = parsed_logs_df.to_pandas()
        
        if df.empty:
            print("⚠️ No logs to process")
            return pd.DataFrame()
        
        print(f"📊 Processing {len(df)} log entries...")
        
        # 1. Extract structured features
        df['msg_len'] = df['MESSAGE'].fillna('').str.len()
        df['has_error'] = df['LOG_LEVEL'].apply(lambda x: 1 if x == 'ERROR' else 0)
        df['has_warning'] = df['LOG_LEVEL'].apply(lambda x: 1 if x == 'WARNING' else 0)
        df['has_critical'] = df['LOG_LEVEL'].apply(lambda x: 1 if x == 'CRITICAL' else 0)
        
        # Pattern-based features
        df['has_failure'] = df['MESSAGE'].fillna('').str.contains(r'fail(ed|ure)?', case=False, regex=True).astype(int)
        df['has_exception'] = df['MESSAGE'].fillna('').str.contains('exception', case=False).astype(int)
        df['is_unauthorized'] = df['MESSAGE'].fillna('').str.contains('unauthorized', case=False).astype(int)
        df['is_connection_issue'] = df['MESSAGE'].fillna('').str.contains(
            'connection|network|latency|timeout', case=False, regex=True
        ).astype(int)
        df['has_number'] = df['MESSAGE'].fillna('').str.contains(r'\d+', regex=True).astype(int)
        df['has_special_chars'] = df['MESSAGE'].fillna('').str.count(r'[^\w\s]')
        
        # Message frequency (rare messages are more likely anomalies)
        message_counts = df['MESSAGE'].value_counts()
        df['message_frequency'] = df['MESSAGE'].map(message_counts)
        df['is_rare_message'] = (df['message_frequency'] <= 2).astype(int)
        
        # 2. Vectorize log messages using TF-IDF
        print("🔤 Vectorizing log messages with TF-IDF...")
        messages = df['MESSAGE'].fillna('').tolist()
        
        # Initialize TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=2,  # Ignore terms that appear in fewer than 2 documents
            max_df=0.8,  # Ignore terms that appear in more than 80% of documents
            ngram_range=(1, 2),  # Use unigrams and bigrams
            strip_accents='unicode',
            lowercase=True,
            token_pattern=r'\b[a-zA-Z]{2,}\b',  # Only alphabetic tokens with 2+ chars
            stop_words='english'
        )
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(messages)
            tfidf_features = tfidf_matrix.toarray()
            
            # Create feature names for TF-IDF columns
            tfidf_feature_names = [f'tfidf_{i}' for i in range(tfidf_features.shape[1])]
            tfidf_df = pd.DataFrame(tfidf_features, columns=tfidf_feature_names, index=df.index)
            
            print(f"✅ Created {tfidf_features.shape[1]} TF-IDF features")
        except Exception as e:
            print(f"⚠️ TF-IDF vectorization failed: {e}. Using zero features.")
            tfidf_df = pd.DataFrame()
        
        # 3. Combine structured features with TF-IDF vectors
        structured_features = [
            'msg_len', 'has_error', 'has_warning', 'has_critical',
            'has_failure', 'has_exception', 'is_unauthorized', 
            'is_connection_issue', 'has_number', 'has_special_chars',
            'message_frequency', 'is_rare_message'
        ]
        
        # Combine all features
        if not tfidf_df.empty:
            feature_matrix = pd.concat([df[structured_features], tfidf_df], axis=1)
        else:
            feature_matrix = df[structured_features]
        
        # Fill any NaN values
        feature_matrix = feature_matrix.fillna(0)
        
        print(f"📈 Total feature dimensions: {feature_matrix.shape[1]}")
        
        # 4. Standardize features for better anomaly detection
        print("⚖️ Standardizing features...")
        scaled_features = self.scaler.fit_transform(feature_matrix)
        
        # 5. Detect anomalies using Isolation Forest
        print(f"🤖 Training Isolation Forest (contamination={contamination})...")
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
            max_samples='auto',
            n_jobs=-1  # Use all available cores
        )
        
        # Predict anomalies
        anomaly_scores = self.model.fit_predict(scaled_features)
        anomaly_probabilities = -self.model.score_samples(scaled_features)
        
        # Add results back to dataframe
        df['anomaly_score'] = anomaly_scores
        df['anomaly_probability'] = anomaly_probabilities
        df['is_anomaly'] = (anomaly_scores == -1)
        
        # Calculate statistics
        anomaly_count = (anomaly_scores == -1).sum()
        total_count = len(df)
        print(f"✅ Detected {anomaly_count} anomalies out of {total_count} logs ({100*anomaly_count/total_count:.1f}%)")
        
        return df
    
    def save_results_to_snowflake(self, results_df, target_table="anomaly_results"):
        """
        Save anomaly detection results back to Snowflake.
        
        Args:
            results_df: Pandas DataFrame with detection results
            target_table: Target table name
        """
        if results_df.empty:
            print("⚠️ No results to save")
            return
        
        # Select relevant columns
        columns_to_save = [
            'LOG_ID', 'FILE_NAME', 'LOG_LEVEL', 'MESSAGE',
            'anomaly_score', 'anomaly_probability', 'is_anomaly'
        ]
        
        # Ensure columns exist
        available_cols = [col for col in columns_to_save if col in results_df.columns]
        save_df = results_df[available_cols].copy()
        
        # Rename columns to uppercase for Snowflake
        save_df.columns = [c.upper() for c in save_df.columns]
        
        # Use temp table approach to avoid column mismatch issues
        temp_table = "TEMP_ANOMALY_RESULTS"
        
        # Convert to Snowpark DataFrame
        sp_df = self.session.create_dataframe(save_df)
        sp_df.write.mode("overwrite").save_as_table(temp_table)
        
        # Insert from temp table (this respects default values and auto-generated columns)
        self.session.sql(f"""
            INSERT INTO {target_table} (log_id, file_name, log_level, message, anomaly_score, anomaly_probability, is_anomaly)
            SELECT LOG_ID, FILE_NAME, LOG_LEVEL, MESSAGE, ANOMALY_SCORE, ANOMALY_PROBABILITY, IS_ANOMALY
            FROM {temp_table}
        """).collect()
        
        # Drop temp table
        self.session.sql(f"DROP TABLE IF EXISTS {temp_table}").collect()
        
        anomaly_count = int(results_df['is_anomaly'].sum())
        print(f"💾 Saved {len(save_df)} records ({anomaly_count} anomalies) to {target_table}")
        
    def run_full_pipeline(self, file_name: str = None, contamination: float = 0.1, max_features: int = 100):
        """
        Run the complete anomaly detection pipeline.
        
        Args:
            file_name: Specific file to process (None = process all)
            contamination: Expected anomaly proportion
            max_features: Number of TF-IDF features
            
        Returns:
            Pandas DataFrame with results
        """
        print("=" * 60)
        print("🚀 Starting Log Anomaly Detection Pipeline")
        print("=" * 60)
        
        # Step 1: Load raw logs
        print("\n📥 Step 1: Loading raw logs...")
        query = "SELECT * FROM raw_logs"
        if file_name:
            query += f" WHERE file_name = '{file_name}'"
        
        raw_logs_df = self.session.sql(query)
        
        # Step 2: Parse logs
        print("\n🔍 Step 2: Parsing log structure...")
        parsed_df = self.parse_log_structure(raw_logs_df)
        
        # Save parsed logs
        parsed_df.write.mode("overwrite").save_as_table("parsed_logs")
        print("✅ Saved parsed logs to parsed_logs table")
        
        # Step 3: Extract features, vectorize, and detect anomalies
        print(f"\n🧬 Step 3: Extracting features and vectorizing (max_features={max_features})...")
        results_df = self.extract_features_and_vectorize(parsed_df, max_features, contamination)
        
        if results_df.empty:
            print("⚠️ No results generated")
            return results_df
        
        # Step 4: Save results
        print("\n💾 Step 4: Saving results to Snowflake...")
        self.save_results_to_snowflake(results_df, "anomaly_results")
        
        # Step 5: Update run history
        anomaly_count = int(results_df['is_anomaly'].sum())
        total_logs = len(results_df)
        
        # Use direct SQL INSERT to respect auto-increment
        file_name_escaped = (file_name if file_name else 'ALL').replace("'", "''")
        self.session.sql(f"""
            INSERT INTO anomaly_runs (file_name, total_logs, anomalies_detected, contamination_factor)
            VALUES ('{file_name_escaped}', {total_logs}, {anomaly_count}, {contamination})
        """).collect()
        
        print("\n" + "=" * 60)
        print("✨ Pipeline Complete!")
        print(f"   Total Logs: {total_logs}")
        print(f"   Anomalies: {anomaly_count} ({100*anomaly_count/total_logs:.1f}%)")
        print(f"   TF-IDF Features: {max_features}")
        print("=" * 60)
        
        return results_df
    
    def save_model(self, model_path="./models"):
        """
        Save the trained vectorizer and model to disk.
        
        Args:
            model_path: Directory to save models
        """
        os.makedirs(model_path, exist_ok=True)
        
        if self.vectorizer:
            joblib.dump(self.vectorizer, f"{model_path}/tfidf_vectorizer.pkl")
            print(f"💾 Saved TF-IDF vectorizer to {model_path}/tfidf_vectorizer.pkl")
        
        if self.model:
            joblib.dump(self.model, f"{model_path}/isolation_forest.pkl")
            print(f"💾 Saved Isolation Forest model to {model_path}/isolation_forest.pkl")
            
        if self.scaler:
            joblib.dump(self.scaler, f"{model_path}/scaler.pkl")
            print(f"💾 Saved scaler to {model_path}/scaler.pkl")
    
    def load_model(self, model_path="./models"):
        """
        Load a previously trained vectorizer and model.
        
        Args:
            model_path: Directory containing saved models
        """
        try:
            self.vectorizer = joblib.load(f"{model_path}/tfidf_vectorizer.pkl")
            self.model = joblib.load(f"{model_path}/isolation_forest.pkl")
            self.scaler = joblib.load(f"{model_path}/scaler.pkl")
            print("✅ Loaded models successfully")
        except Exception as e:
            print(f"⚠️ Error loading models: {e}")


def load_snowflake_config(config_path='snowflake_config.json'):
    """
    Load Snowflake configuration and handle key-pair authentication.
    
    Args:
        config_path: Path to the configuration JSON file
        
    Returns:
        dict: Configuration ready for Snowpark Session
    """
    import json
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Handle key-pair authentication
    if config.get('authenticator') == 'SNOWFLAKE_JWT':
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        
        private_key_path = config.get('private_key_path')
        if not private_key_path:
            raise ValueError("private_key_path required for SNOWFLAKE_JWT authentication")
        
        if not os.path.exists(private_key_path):
            raise FileNotFoundError(f"Private key file not found: {private_key_path}")
        
        # Load private key
        passphrase = config.get('private_key_passphrase')
        if passphrase in ['your_passphrase_if_encrypted', '', None]:
            passphrase = None
        
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=passphrase.encode() if passphrase else None,
                backend=default_backend()
            )
        
        # Convert to bytes format for Snowpark
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Build config for Snowpark
        connection_config = {
            'account': config['account'],
            'user': config['user'],
            'private_key': private_key_bytes,
            'role': config.get('role'),
            'warehouse': config.get('warehouse'),
            'database': config.get('database'),
            'schema': config.get('schema')
        }
        
        return connection_config
    
    # Return as-is for password authentication
    return config


# Standalone execution
if __name__ == "__main__":
    import json
    
    # Load Snowflake connection parameters
    print("📡 Loading Snowflake configuration...")
    config = load_snowflake_config('snowflake_config.json')
    
    # Create Snowpark session
    print("🔌 Connecting to Snowflake...")
    session = Session.builder.configs(config).create()
    
    print(f"✅ Connected to Snowflake: {session.get_current_database()}.{session.get_current_schema()}")
    
    # Create analyzer
    analyzer = SnowparkLogAnalyzer(session)
    
    # Run full pipeline
    results = analyzer.run_full_pipeline(contamination=0.1, max_features=100)
    
    # Optionally save models
    analyzer.save_model()
    
    # Close session
    session.close()

