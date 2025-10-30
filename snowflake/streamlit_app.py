"""
Streamlit App for Log Anomaly Detection in Snowflake
Uses TF-IDF vectorization and Isolation Forest for anomaly detection
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark import Session
from snowpark_analyzer import SnowparkLogAnalyzer
import json
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Log Anomaly Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


def load_snowflake_config_for_streamlit():
    """Load Snowflake config handling key-pair authentication."""
    # Try to load from config file
    if os.path.exists('snowflake_config.json'):
        with open('snowflake_config.json', 'r') as f:
            config = json.load(f)
        
        # Handle key-pair authentication
        if config.get('authenticator') == 'SNOWFLAKE_JWT':
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            
            private_key_path = config.get('private_key_path')
            if not private_key_path or not os.path.exists(private_key_path):
                raise FileNotFoundError(f"Private key not found: {private_key_path}")
            
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
            
            # Convert to bytes for Snowpark
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return {
                'account': config['account'],
                'user': config['user'],
                'private_key': private_key_bytes,
                'role': config.get('role'),
                'warehouse': config.get('warehouse'),
                'database': config.get('database'),
                'schema': config.get('schema')
            }
        
        return config
    else:
        # Use Streamlit secrets
        return {
            "account": st.secrets["snowflake"]["account"],
            "user": st.secrets["snowflake"]["user"],
            "password": st.secrets["snowflake"]["password"],
            "role": st.secrets["snowflake"]["role"],
            "warehouse": st.secrets["snowflake"]["warehouse"],
            "database": st.secrets["snowflake"]["database"],
            "schema": st.secrets["snowflake"]["schema"]
        }


@st.cache_resource
def get_snowflake_session():
    """Create and cache Snowflake session."""
    try:
        config = load_snowflake_config_for_streamlit()
        session = Session.builder.configs(config).create()
        return session
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        return None


def main():
    st.title("🔍 Log Anomaly Detection System")
    st.markdown("### Powered by TF-IDF Vectorization & Isolation Forest")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Connect to Snowflake
        session = get_snowflake_session()
        if session is None:
            st.error("Unable to connect to Snowflake. Please check your configuration.")
            st.stop()
        
        st.success(f"✅ Connected to Snowflake")
        st.info(f"**Database:** {session.get_current_database()}\n\n**Schema:** {session.get_current_schema()}")
        
        st.divider()
        
        # Analysis parameters
        st.subheader("Analysis Parameters")
        contamination = st.slider(
            "Contamination Factor",
            min_value=0.01,
            max_value=0.5,
            value=0.1,
            step=0.01,
            help="Expected proportion of anomalies (0.1 = 10%)"
        )
        
        max_features = st.slider(
            "TF-IDF Features",
            min_value=50,
            max_value=500,
            value=100,
            step=50,
            help="Maximum number of TF-IDF features to extract"
        )
        
        # File selection
        st.divider()
        st.subheader("Log File Selection")
        
        # Get available files
        try:
            files_df = session.sql("SELECT DISTINCT file_name FROM raw_logs ORDER BY file_name").to_pandas()
            if not files_df.empty:
                file_options = ['ALL'] + files_df['FILE_NAME'].tolist()
                selected_file = st.selectbox("Select Log File", file_options)
            else:
                st.warning("No log files found in raw_logs table")
                selected_file = None
        except Exception as e:
            st.error(f"Error loading files: {e}")
            selected_file = None
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🔮 Cluster View", "🚀 Run Analysis", "📁 Upload Logs", "📈 History"])
    
    # Tab 1: Dashboard
    with tab1:
        st.header("Anomaly Detection Dashboard")
        
        try:
            # Load summary data
            summary_df = session.sql("SELECT * FROM anomaly_summary ORDER BY last_analysis DESC").to_pandas()
            
            if not summary_df.empty:
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                total_logs = summary_df['TOTAL_LOGS'].sum()
                total_anomalies = summary_df['ANOMALY_COUNT'].sum()
                avg_anomaly_pct = summary_df['ANOMALY_PERCENTAGE'].mean()
                files_analyzed = len(summary_df)
                
                col1.metric("Total Logs", f"{total_logs:,}")
                col2.metric("Total Anomalies", f"{total_anomalies:,}")
                col3.metric("Avg Anomaly %", f"{avg_anomaly_pct:.2f}%")
                col4.metric("Files Analyzed", files_analyzed)
                
                st.divider()
                
                # Summary table
                st.subheader("📋 Analysis Summary by File")
                st.dataframe(
                    summary_df,
                    use_container_width=True,
                    column_config={
                        "ANOMALY_PERCENTAGE": st.column_config.ProgressColumn(
                            "Anomaly %",
                            format="%.2f%%",
                            min_value=0,
                            max_value=100,
                        ),
                    }
                )
                
                # Visualization
                st.subheader("📊 Anomaly Distribution")
                fig = px.bar(
                    summary_df,
                    x='FILE_NAME',
                    y=['TOTAL_LOGS', 'ANOMALY_COUNT'],
                    barmode='group',
                    title='Logs vs Anomalies by File',
                    labels={'value': 'Count', 'variable': 'Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.info("No analysis results found. Run an analysis from the 'Run Analysis' tab.")
        
        except Exception as e:
            st.error(f"Error loading dashboard: {e}")
    
    # Tab 2: Run Analysis
    with tab2:
        st.header("🚀 Run Anomaly Detection")
        
        st.info(f"""
        **Configuration:**
        - Contamination Factor: {contamination} ({contamination*100:.0f}% expected anomalies)
        - TF-IDF Features: {max_features}
        - Selected File: {selected_file if selected_file else 'None'}
        """)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🔍 Run Anomaly Detection", type="primary", use_container_width=True):
                if selected_file:
                    with st.spinner("Analyzing logs... This may take a few moments."):
                        try:
                            # Create analyzer
                            analyzer = SnowparkLogAnalyzer(session)
                            
                            # Progress tracking
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            status_text.text("Loading logs...")
                            progress_bar.progress(20)
                            
                            # Run pipeline
                            file_filter = None if selected_file == 'ALL' else selected_file
                            
                            status_text.text("Vectorizing with TF-IDF...")
                            progress_bar.progress(50)
                            
                            results = analyzer.run_full_pipeline(
                                file_name=file_filter,
                                contamination=contamination,
                                max_features=max_features
                            )
                            
                            status_text.text("Saving results...")
                            progress_bar.progress(90)
                            
                            if not results.empty:
                                anomaly_count = results['is_anomaly'].sum()
                                total_count = len(results)
                                
                                progress_bar.progress(100)
                                status_text.empty()
                                
                                st.success(f"""
                                ✅ Analysis Complete!
                                - Total Logs: {total_count}
                                - Anomalies Detected: {anomaly_count} ({100*anomaly_count/total_count:.1f}%)
                                - TF-IDF Features Used: {max_features}
                                """)
                                
                                # Show top anomalies
                                st.subheader("🚨 Top Anomalies Detected")
                                anomalies = results[results['is_anomaly'] == True].sort_values(
                                    'anomaly_probability', ascending=False
                                ).head(20)
                                
                                st.dataframe(
                                    anomalies[['LOG_LEVEL', 'MESSAGE', 'anomaly_probability']],
                                    use_container_width=True
                                )
                            else:
                                st.warning("No logs processed")
                        
                        except Exception as e:
                            st.error(f"Error during analysis: {e}")
                            st.exception(e)
                else:
                    st.warning("Please select a log file from the sidebar")
        
        with col2:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
    
    # Tab 2: Cluster Visualization
    with tab2:
        st.header("🔮 Cluster Visualization")
        
        st.markdown("""
        This visualization shows how logs are distributed in feature space.
        **112 features** are reduced to **2D** using PCA for visualization.
        
        - 🟢 **Green dots**: Normal logs (clustered together)
        - 🔴 **Red dots**: Anomalous logs (isolated, far from cluster)
        """)
        
        try:
            # Load anomaly results
            results_df = session.sql("""
                SELECT * FROM anomaly_results 
                ORDER BY log_id 
                LIMIT 5000
            """).to_pandas()
            
            if not results_df.empty and len(results_df) > 10:
                with st.spinner("Generating cluster visualization... This may take a moment."):
                    # Get the data
                    from snowpark_analyzer import SnowparkLogAnalyzer
                    
                    # Load parsed logs to recreate features
                    parsed_df = session.sql("SELECT * FROM parsed_logs LIMIT 5000").to_pandas()
                    
                    if not parsed_df.empty:
                        # Create analyzer to extract features
                        analyzer = SnowparkLogAnalyzer(session)
                        
                        # Extract features (without running full pipeline)
                        import pandas as pd
                        import numpy as np
                        from sklearn.feature_extraction.text import TfidfVectorizer
                        from sklearn.preprocessing import StandardScaler
                        from sklearn.decomposition import PCA
                        
                        df = parsed_df.copy()
                        
                        # Extract structured features
                        df['msg_len'] = df['MESSAGE'].fillna('').str.len()
                        df['has_error'] = (df['LOG_LEVEL'] == 'ERROR').astype(int)
                        df['has_warning'] = (df['LOG_LEVEL'] == 'WARNING').astype(int)
                        df['has_critical'] = (df['LOG_LEVEL'] == 'CRITICAL').astype(int)
                        df['has_failure'] = df['MESSAGE'].fillna('').str.contains(r'fail', case=False, regex=True).astype(int)
                        df['has_exception'] = df['MESSAGE'].fillna('').str.contains('exception', case=False).astype(int)
                        df['is_unauthorized'] = df['MESSAGE'].fillna('').str.contains('unauthorized', case=False).astype(int)
                        df['is_connection_issue'] = df['MESSAGE'].fillna('').str.contains('connection|network|timeout', case=False, regex=True).astype(int)
                        df['has_number'] = df['MESSAGE'].fillna('').str.contains(r'\d+', regex=True).astype(int)
                        df['has_special_chars'] = df['MESSAGE'].fillna('').str.count(r'[^\w\s]')
                        
                        message_counts = df['MESSAGE'].value_counts()
                        df['message_frequency'] = df['MESSAGE'].map(message_counts)
                        df['is_rare_message'] = (df['message_frequency'] <= 2).astype(int)
                        
                        # Vectorize with TF-IDF
                        messages = df['MESSAGE'].fillna('').tolist()
                        
                        vectorizer = TfidfVectorizer(
                            max_features=100,
                            min_df=2,
                            max_df=0.8,
                            ngram_range=(1, 2),
                            lowercase=True,
                            stop_words='english'
                        )
                        
                        try:
                            tfidf_matrix = vectorizer.fit_transform(messages)
                            tfidf_features = tfidf_matrix.toarray()
                            # Create TF-IDF dataframe with string column names
                            tfidf_columns = [f'tfidf_{i}' for i in range(tfidf_features.shape[1])]
                            tfidf_df = pd.DataFrame(tfidf_features, columns=tfidf_columns, index=df.index)
                        except:
                            tfidf_df = pd.DataFrame()
                        
                        # Combine features
                        structured_features = ['msg_len', 'has_error', 'has_warning', 'has_critical',
                                              'has_failure', 'has_exception', 'is_unauthorized',
                                              'is_connection_issue', 'has_number', 'has_special_chars',
                                              'message_frequency', 'is_rare_message']
                        
                        if not tfidf_df.empty:
                            feature_matrix = pd.concat([df[structured_features], tfidf_df], axis=1)
                        else:
                            feature_matrix = df[structured_features]
                        
                        feature_matrix = feature_matrix.fillna(0)
                        
                        # Ensure all column names are strings
                        feature_matrix.columns = feature_matrix.columns.astype(str)
                        
                        # Standardize
                        scaler = StandardScaler()
                        scaled_features = scaler.fit_transform(feature_matrix)
                        
                        # Reduce to 2D using PCA
                        pca = PCA(n_components=2)
                        coords_2d = pca.fit_transform(scaled_features)
                        
                        # Create visualization dataframe
                        viz_df = pd.DataFrame({
                            'PC1': coords_2d[:, 0],
                            'PC2': coords_2d[:, 1],
                            'LOG_ID': df['LOG_ID'].values,
                            'LOG_LEVEL': df['LOG_LEVEL'].values,
                            'MESSAGE': df['MESSAGE'].values
                        })
                        
                        # Merge with anomaly results
                        results_subset = results_df[['LOG_ID', 'IS_ANOMALY', 'ANOMALY_PROBABILITY']].copy()
                        viz_df = viz_df.merge(results_subset, on='LOG_ID', how='left')
                        viz_df['IS_ANOMALY'] = viz_df['IS_ANOMALY'].fillna(False)
                        viz_df['ANOMALY_PROBABILITY'] = viz_df['ANOMALY_PROBABILITY'].fillna(0)
                        
                        # Separate normal and anomalous
                        normal_df = viz_df[viz_df['IS_ANOMALY'] == False]
                        anomaly_df = viz_df[viz_df['IS_ANOMALY'] == True]
                        
                        # Display statistics
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total Logs", len(viz_df))
                        col2.metric("Normal (Green)", len(normal_df))
                        col3.metric("Anomalies (Red)", len(anomaly_df))
                        
                        st.divider()
                        
                        # Create interactive plot
                        import plotly.graph_objects as go
                        
                        fig = go.Figure()
                        
                        # Plot normal logs
                        fig.add_trace(go.Scatter(
                            x=normal_df['PC1'],
                            y=normal_df['PC2'],
                            mode='markers',
                            name='Normal Logs',
                            marker=dict(
                                size=6,
                                color='green',
                                opacity=0.5,
                                line=dict(width=0)
                            ),
                            text=normal_df['MESSAGE'].str[:60] + '...',
                            hovertemplate='<b>Normal Log</b><br>' +
                                        'Level: %{customdata[0]}<br>' +
                                        'Message: %{text}<br>' +
                                        '<extra></extra>',
                            customdata=normal_df[['LOG_LEVEL']].values
                        ))
                        
                        # Plot anomalous logs
                        fig.add_trace(go.Scatter(
                            x=anomaly_df['PC1'],
                            y=anomaly_df['PC2'],
                            mode='markers',
                            name='Anomalous Logs',
                            marker=dict(
                                size=10,
                                color=anomaly_df['ANOMALY_PROBABILITY'],
                                colorscale='Reds',
                                opacity=0.8,
                                line=dict(width=1, color='darkred'),
                                colorbar=dict(title="Anomaly<br>Probability"),
                                cmin=anomaly_df['ANOMALY_PROBABILITY'].min() if not anomaly_df.empty else 0,
                                cmax=anomaly_df['ANOMALY_PROBABILITY'].max() if not anomaly_df.empty else 1
                            ),
                            text=anomaly_df['MESSAGE'].str[:60] + '...',
                            hovertemplate='<b>ANOMALY</b><br>' +
                                        'Level: %{customdata[0]}<br>' +
                                        'Probability: %{customdata[1]:.4f}<br>' +
                                        'Message: %{text}<br>' +
                                        '<extra></extra>',
                            customdata=anomaly_df[['LOG_LEVEL', 'ANOMALY_PROBABILITY']].values
                        ))
                        
                        fig.update_layout(
                            title={
                                'text': '🔮 Log Clusters in Feature Space (PCA Projection)',
                                'x': 0.5,
                                'xanchor': 'center'
                            },
                            xaxis_title=f'Principal Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)',
                            yaxis_title=f'Principal Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)',
                            hovermode='closest',
                            height=600,
                            showlegend=True,
                            legend=dict(
                                yanchor="top",
                                y=0.99,
                                xanchor="left",
                                x=0.01,
                                bgcolor="rgba(255,255,255,0.8)"
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Explanation
                        st.info(f"""
                        **How to Read This Chart:**
                        
                        - **X & Y axes**: The two principal components that explain {pca.explained_variance_ratio_[0]*100:.1f}% and {pca.explained_variance_ratio_[1]*100:.1f}% of the variance
                        - **Green dots**: Normal logs clustered together (similar patterns)
                        - **Red dots**: Anomalous logs isolated from the main cluster (unusual patterns)
                        - **Darker red**: Higher anomaly probability
                        - **Hover**: See log details
                        
                        The algorithm detects logs that are **easy to isolate** from the cluster!
                        """)
                        
                        # Top anomalies in the view
                        st.subheader("🚨 Top Anomalies in This View")
                        top_anomalies = anomaly_df.nlargest(5, 'ANOMALY_PROBABILITY')
                        
                        for idx, row in top_anomalies.iterrows():
                            with st.expander(f"[{row['LOG_LEVEL']}] {row['MESSAGE'][:70]}..."):
                                st.write(f"**Anomaly Probability:** {row['ANOMALY_PROBABILITY']:.4f}")
                                st.write(f"**Position:** PC1={row['PC1']:.2f}, PC2={row['PC2']:.2f}")
                                st.write(f"**Full Message:** {row['MESSAGE']}")
                        
                    else:
                        st.warning("No parsed logs found. Run an analysis first!")
                        
            else:
                st.info("📊 No anomaly data available yet. Run an analysis from the 'Run Analysis' tab!")
                
        except Exception as e:
            st.error(f"Error generating visualization: {e}")
            st.exception(e)
    
    # Tab 3: Upload Logs
    with tab3:
        st.header("📁 Upload Log Files")
        
        st.markdown("""
        Upload log files to Snowflake for analysis. Supported formats:
        - `.log` files
        - `.txt` files
        """)
        
        uploaded_file = st.file_uploader("Choose a log file", type=['log', 'txt'])
        
        if uploaded_file is not None:
            st.info(f"**File:** {uploaded_file.name}\n\n**Size:** {uploaded_file.size:,} bytes")
            
            if st.button("📤 Upload to Snowflake", type="primary"):
                with st.spinner("Uploading..."):
                    try:
                        # Read file content
                        content = uploaded_file.read().decode('utf-8')
                        lines = content.strip().split('\n')
                        
                        # Create DataFrame
                        df = pd.DataFrame({
                            'file_name': [uploaded_file.name] * len(lines),
                            'raw_line': lines
                        })
                        
                        # Upload to Snowflake
                        sp_df = session.create_dataframe(df)
                        sp_df.write.mode("append").save_as_table("raw_logs")
                        
                        st.success(f"✅ Uploaded {len(lines)} log lines from {uploaded_file.name}")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Upload failed: {e}")
    
    # Tab 5: History
    with tab5:
        st.header("📈 Analysis History")
        
        try:
            history_df = session.sql("""
                SELECT * FROM anomaly_runs 
                ORDER BY run_timestamp DESC 
                LIMIT 50
            """).to_pandas()
            
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True)
                
                # Trend chart
                st.subheader("📊 Anomaly Trend Over Time")
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=history_df['RUN_TIMESTAMP'],
                    y=history_df['ANOMALIES_DETECTED'],
                    mode='lines+markers',
                    name='Anomalies',
                    line=dict(color='red', width=2)
                ))
                
                fig.add_trace(go.Scatter(
                    x=history_df['RUN_TIMESTAMP'],
                    y=history_df['TOTAL_LOGS'],
                    mode='lines+markers',
                    name='Total Logs',
                    line=dict(color='blue', width=2)
                ))
                
                fig.update_layout(
                    title='Log Analysis Trend',
                    xaxis_title='Timestamp',
                    yaxis_title='Count',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.info("No analysis history found")
        
        except Exception as e:
            st.error(f"Error loading history: {e}")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Log Anomaly Detection System | Powered by Snowflake, TF-IDF & Isolation Forest</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

