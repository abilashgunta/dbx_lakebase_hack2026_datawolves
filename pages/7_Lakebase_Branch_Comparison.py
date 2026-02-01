import streamlit as st
import psycopg
import pandas as pd
import base64
import time
from datetime import datetime, timezone, timedelta
from databricks.sdk import WorkspaceClient
from db_utils import get_active_connection, get_postgres_branch_connection, get_postgres_connection

st.set_page_config(page_title="Lakebase Branch Comparison", page_icon="⛁", layout="wide")

st.logo("pages/additional_icons/Logo Steel-FY25.png")

# Background Image CSS
st.markdown("""
<style>
.stApp {
    background-image: url('https://hougumlaw.com/wp-content/uploads/2016/05/light-website-backgrounds-light-color-background-images-light-color-background-images-for-website-1024x640.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: scroll;
}
</style>
""", unsafe_allow_html=True)

st.title("⛁ Lakebase Branch Comparison")
st.markdown("Checking branch statuses and performing test to ascertain data cleanliness")

# Initialize session state for branches
if "branches_list" not in st.session_state:
    st.session_state.branches_list = []

if "branch_oauth" not in st.session_state:
    st.session_state.branch_oauth = ""
    st.session_state.oauth_expires_at = None

w = WorkspaceClient()

with open("pages/additional_icons/git-branch-svgrepo-com.png", "rb") as f:
        img_bytes = f.read()
icon_base64 = base64.b64encode(img_bytes).decode()

# Available Branches Section
st.markdown(f"""## <img src="data:image/png;base64,{icon_base64}" style="height:1.5em; vertical-align:middle;"> Available Lakebase Branches""",
            unsafe_allow_html=True)
#st.subheader("![git branch](/additional_icons/git-branch-svgrepo-com.svg) Available Lakebase Branches")
col1, col2 = st.columns(2)

def get_branch_details():
    # Get branch details
    info_box = st.info("Loading branch details...")
    try:
        branches = list(w.postgres.list_branches(parent="projects/ea925ef7-65f0-4a9e-8a83-3d4a42ef62d5"))
        # Get branch names excluding 'default' (data quality comparisons will be done against 'default')
        st.session_state.branches_list = [branch.name for branch in branches if branch.status.default != True]

        # Convert to DataFrame
        branch_data = []
        for branch in branches:
            branch_data.append({
                "Branch Name": branch.name,
                "Default": branch.status.default,
                "Protected": branch.status.is_protected,
                "Created At": branch.status.source_branch_time,
                "State": branch.status.current_state,
                "Expires At": branch.status.expire_time
            })
    
        df = pd.DataFrame(branch_data)
        time.sleep(1.5)
        info_box.empty()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        time.sleep(1.5)
        info_box.empty()
        st.error(f"❌ Error fetching branches: {e}")

def get_oauth_token(endpoint):
    # Check if token exists and is not expired
    if st.session_state.branch_oauth != "" and st.session_state.oauth_expires_at is not None:
        try:
            # Parse the expiration time (format: "2026-01-29T22:52:51Z")
            current_time = datetime.now(timezone.utc)
            
            # If token is still valid (not expired), return without creating new one
            if current_time < st.session_state.oauth_expires_at:
                oauth_msg = st.info(f"OAuth token is still valid. Expires at: {st.session_state.oauth_expires_at}, Current time: {current_time}")
                time.sleep(1.5)
                oauth_msg.empty()
                return
            info_msg.empty()
        except Exception as e:
            st.info(e)
            pass
    
    # Create new token if it doesn't exist or is expired
    try:
        credential = w.postgres.generate_database_credential(endpoint=endpoint)

        st.session_state.branch_oauth = f"{credential.token}"
        st.session_state.oauth_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        success_msg = st.success(f"✓ OAuth token created. Expires at: {st.session_state.oauth_expires_at}")
        time.sleep(1.5)
        success_msg.empty()
    except Exception as e:
        st.error(f"❌ Error creating OAuth token: {e}")

selected_branch = None
with col1:
    if st.button("Refresh Branches"):
        get_branch_details()

with col2:
    if st.session_state.branches_list == []:
        st.write(f"Status: Waiting on branch refresh...")
    else:
        st.write(f"Status: Ready")
    
    # Branch selection dropdown
    if st.session_state.branches_list:
        selected_branch = st.selectbox(
            "Select a branch to work with:",
            st.session_state.branches_list,
            key="selected_branch"
        )
        st.success(f"✓ Selected: {selected_branch}")

# Data Cleanliness Check Section
st.subheader("🔍 Data Cleanliness Check")

# Create tabs for different checks
tab1, tab2, tab3 = st.tabs(["Table Validation", "Data Quality", "Performance Metrics"])

with tab1:
    st.write("### Table Validation")
    if st.button("Run Table Check"):
        info_msg = st.empty()
        info_msg.info("Validating database tables in main schema...")
        if selected_branch:
            # get branch endpoint
            endpoints = list(w.postgres.list_endpoints(parent=selected_branch))
            host_name = endpoints[0].status.hosts.host
            endpoint_name = endpoints[0].name
            get_oauth_token(endpoint_name)
            branch_conn = get_active_connection(host_name, st.session_state.branch_oauth)
            if branch_conn:
                success_msg = st.success(f"✓ Connected to selected branch database")
                time.sleep(1.5)
                success_msg.empty()
                
                # Check for required tables
                st.subheader("Table Validation")
                required_tables = ["lb_alerts", "lb_events", "lb_tenants", "support_tickets"]
                
                try:
                    cursor = branch_conn.cursor()
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'data_wolves'
                    """)
                    existing_tables = [row[0] for row in cursor.fetchall()]
                    cursor.close()
                    
                    # Display results
                    table_status = []
                    for table in required_tables:
                        status = "✓ Present" if table in existing_tables else "✗ Missing"
                        table_status.append({
                            "Table Name": table,
                            "Status": status
                        })
                    
                    status_df = pd.DataFrame(table_status)
                    st.dataframe(status_df, use_container_width=True)
                    
                    missing_tables = [t for t in required_tables if t not in existing_tables]
                    info_msg.empty()
                    if missing_tables:
                        st.error(f"❌ Missing tables: {', '.join(missing_tables)}. Please use PITR to revert to a previous branch version or re-sync any missing tables!")
                    else:
                        st.success("✓ All required tables are present")
                        
                except Exception as e:
                    st.error(f"❌ Error checking tables: {e}")
                finally:
                    if branch_conn:
                        branch_conn.close()
            else:
                info_msg.empty()
                st.warning("Cannot connect to branch database.")

        else:
            info_msg.empty()
            st.warning("Please select a branch first.")

with tab2:
    st.write("### Data Quality")
    if st.button("Run Data Quality Check"):
        info_msg = st.empty()
        info_msg.info("Checking data quality metrics...")
        if selected_branch:
            # get branch endpoint
            endpoints = list(w.postgres.list_endpoints(parent=selected_branch))
            host_name = endpoints[0].status.hosts.host
            endpoint_name = endpoints[0].name
            get_oauth_token(endpoint_name)
            branch_conn = get_active_connection(host_name, st.session_state.branch_oauth)
            
            if branch_conn:
                success_msg = st.success(f"✓ Connected to selected branch database")
                time.sleep(1.5)
                success_msg.empty()
                
                null_threshold = 25  # 25% threshold
                
                try:
                    cursor = branch_conn.cursor()
                    
                    # Dynamically fetch all tables from data_wolves schema
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'data_wolves'
                    """)
                    required_tables = [row[0] for row in cursor.fetchall()]
                    
                    all_quality_issues = []
                    
                    for table in required_tables:
                        # Get all columns for the table
                        cursor.execute(f"""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'data_wolves' AND table_name = '{table}'
                            ORDER BY ordinal_position
                        """)
                        columns = [row[0] for row in cursor.fetchall()]
                        
                        if not columns:
                            continue
                        
                        # Check NULL percentage for each column
                        for column in columns:
                            cursor.execute(f"""
                                SELECT COUNT(*), COUNT("{column}") 
                                FROM data_wolves.{table}
                            """)
                            total_rows, non_null_rows = cursor.fetchone()
                            
                            if total_rows > 0:
                                null_percentage = ((total_rows - non_null_rows) / total_rows) * 100
                                
                                if null_percentage > null_threshold:
                                    all_quality_issues.append({
                                        "Table": table,
                                        "Column": column,
                                        "NULL %": f"{null_percentage:.2f}%",
                                        "Status": "⚠️ High NULL"
                                    })
                    
                    cursor.close()
                    info_msg.empty()
                    # Display results
                    if all_quality_issues:
                        st.subheader("Data Quality Issues Found")
                        issues_df = pd.DataFrame(all_quality_issues)
                        st.dataframe(issues_df, use_container_width=True)
                        st.error(f"❌ Found {len(all_quality_issues)} column(s) with > {null_threshold}% NULL values.")
                    else:
                        st.success(f"✓ All columns have ≤ {null_threshold}% NULL values - Data quality check passed!")
                        
                except Exception as e:
                    info_msg.empty()
                    st.error(f"❌ Error checking data quality: {e}")
                finally:
                    if branch_conn:
                        branch_conn.close()
            else:
                info_msg.empty()
                st.warning("Cannot connect to branch database.")
        else:
            info_msg.empty()
            st.warning("Please select a branch first.")

with tab3:
    st.write("### Performance Metrics")
    if st.button("Run Performance Analysis"):
        info_msg = st.empty()
        info_msg.info("Analyzing database performance...")
        if selected_branch:
            try:
                # Get endpoints for both branches
                endpoints = list(w.postgres.list_endpoints(parent=selected_branch))
                branch_host = endpoints[0].status.hosts.host
                endpoint_name = endpoints[0].name
                get_oauth_token(endpoint_name)
                
                # Connect to selected branch
                branch_conn = get_active_connection(branch_host, st.session_state.branch_oauth)
                
                # Connect to default branch
                default_conn = get_active_connection()
                
                if branch_conn and default_conn:
                    success_msg = st.success("✓ Connected to both branches")
                    time.sleep(1.5)
                    success_msg.empty()
                    
                    import time
                    
                    # Define multiple test queries
                    test_queries = {
                        "Support Ticket Data Gather": """
                            SELECT 
                                st.ticket_id,
                                st.tenant_id,
                                t.tenant_name as tenant_name,
                                st.alert_id,
                                a.severity as alert_severity,
                                a.alert_type,
                                st.user_name,
                                st.activity_type,
                                st.activity_timestamp,
                                st.comment,
                                st.is_customer_facing,
                                st.customer_message
                            FROM data_wolves.support_tickets st
                            LEFT JOIN data_wolves.lb_tenants1 t ON st.tenant_id = t.tenant_id
                            LEFT JOIN data_wolves.lb_alerts a ON st.alert_id = a.alert_id
                            ORDER BY st.activity_timestamp DESC
                        """,
                        "Event Data Gathering": """
                            SELECT 
                                e.event_id,
                                e.tenant_id,
                                t.tenant_name,
                                t.industry,
                                e.alert_id,
                                e.event_type,
                                e.severity,
                                e.source_ip,
                                e.username,
                                e.hostname,
                                e.event_timestamp,
                                e.raw_log,
                                t.service_tier,
                                t.risk_level
                            FROM data_wolves.lb_events e
                            LEFT JOIN data_wolves.lb_tenants1 t ON e.tenant_id = t.tenant_id
                            ORDER BY e.event_timestamp DESC
                        """,
                        "Alert Data Gathering": """
                            SELECT 
                                a.alert_id,
                                a.tenant_id,
                                t.tenant_name,
                                t.industry,
                                a.alert_name,
                                a.alert_type,
                                a.severity,
                                a.status,
                                a.detection_time,
                                a.assigned_to,
                                a.affected_assets,
                                a.description,
                                t.service_tier,
                                t.risk_level
                            FROM data_wolves.lb_alerts a
                            LEFT JOIN data_wolves.lb_tenants1 t ON a.tenant_id = t.tenant_id
                            ORDER BY a.detection_time DESC
                        """,
                        "Tenant Data Gathering": """
                            SELECT 
                                t.tenant_id,
                                t.tenant_name,
                                t.industry,
                                t.company_size,
                                t.service_tier,
                                t.security_score,
                                t.risk_level,
                                t.status,
                                COUNT(DISTINCT st.ticket_id) as total_tickets
                            FROM data_wolves.lb_tenants1 t
                            LEFT JOIN data_wolves.support_tickets st ON t.tenant_id = st.tenant_id
                            GROUP BY 
                                t.tenant_id, t.tenant_name, t.industry, t.company_size,
                                t.service_tier, t.security_score, t.risk_level, t.status
                            ORDER BY t.security_score DESC
                        """
                    }
                    
                    performance_results = []
                    
                    # Run each query on both branches
                    for query_name, query in test_queries.items():
                        # Run on default branch
                        try:
                            cursor_default = default_conn.cursor()
                            start_time = time.time()
                            cursor_default.execute(query)
                            cursor_default.fetchall()
                            default_duration = time.time() - start_time
                            cursor_default.close()
                            
                            default_status = "✓"
                        except Exception as e:
                            default_duration = None
                            default_status = "✗"
                        
                        # Run on selected branch
                        try:
                            cursor_branch = branch_conn.cursor()
                            start_time = time.time()
                            cursor_branch.execute(query)
                            cursor_branch.fetchall()
                            branch_duration = time.time() - start_time
                            cursor_branch.close()
                            
                            branch_status = "✓"
                        except Exception as e:
                            branch_duration = None
                            branch_status = "✗"
                        
                        # Calculate difference if both queries succeeded
                        if default_duration and branch_duration:
                            difference = abs(default_duration - branch_duration)
                            percentage_diff = (difference / max(default_duration, branch_duration)) * 100
                            
                            performance_results.append({
                                "Query": query_name,
                                "Default (s)": f"{default_duration:.4f}",
                                "Branch (s)": f"{branch_duration:.4f}",
                                "Diff (s)": f"{difference:.4f}",
                                "Diff %": f"{percentage_diff:.2f}%",
                                "Pass": "❌" if percentage_diff > 50 else "✓",
                                "Status": default_status if default_status == branch_status else "⚠️"
                            })
                        else:
                            performance_results.append({
                                "Query": query_name,
                                "Default (s)": f"{default_duration:.4f}" if default_duration else "Error",
                                "Branch (s)": f"{branch_duration:.4f}" if branch_duration else "Error",
                                "Diff (s)": "N/A",
                                "Diff %": "N/A",
                                "Pass": "❌",
                                "Status": "⚠️ Error"
                            })

                    info_msg.empty()
                    # Display results
                    if performance_results:
                        st.subheader("Query Performance Comparison")
                        perf_df = pd.DataFrame(performance_results)
                        st.dataframe(perf_df, use_container_width=True)
                        
                        # Summary statistics
                        st.subheader("Performance Summary")
                        col1, col2, col3 = st.columns(3)
                        
                        # Count successful queries
                        successful = len([r for r in performance_results if r["Status"] != "⚠️ Error"])
                        
                        with col1:
                            st.metric("Successful Queries", successful)
                        with col2:
                            avg_default = pd.to_numeric(
                                pd.Series([float(r["Default (s)"]) for r in performance_results if r["Default (s)"] != "Error"]),
                                errors='coerce'
                            ).mean()
                            st.metric("Avg Default Time (s)", f"{avg_default:.4f}")
                        with col3:
                            avg_branch = pd.to_numeric(
                                pd.Series([float(r["Branch (s)"]) for r in performance_results if r["Branch (s)"] != "Error"]),
                                errors='coerce'
                            ).mean()
                            st.metric("Avg Branch Time (s)", f"{avg_branch:.4f}")
                    
                else:
                    info_msg.empty()
                    st.warning("Could not connect to one or both branches")
                    
            except Exception as e:
                info_msg.empty()
                st.error(f"❌ Error during performance analysis: {e}")
        else:
            info_msg.empty()
            st.warning("Please select a branch first.")