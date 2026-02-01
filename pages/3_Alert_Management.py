import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path to import db_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_active_connection

st.set_page_config(
    page_title="Alert Management",
    page_icon="🚨",
    layout="wide"
)

st.logo("pages/additional_icons/Logo Steel-FY25.png")

# Helper function to get related events
@st.cache_data(ttl=60)
def get_related_events(alert_id):
    """Get events related to this alert"""
    conn = get_active_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = f"""
            SELECT 
                event_id,
                event_type,
                severity,
                source_ip,
                username,
                event_timestamp
            FROM data_wolves.lb_events
            WHERE alert_id = '{alert_id}'
            ORDER BY event_timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()

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

st.title("🚨 Alert Management")
st.markdown("Real-time security alert monitoring and incident response")

# Get connection
conn = get_active_connection()

if conn:
    try:
        with conn.cursor() as cur:
            # Get alert overview with tenant info
            cur.execute("""
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
                    t.risk_level,
                    t.security_score
                FROM data_wolves.lb_alerts a
                LEFT JOIN data_wolves.lb_tenants1 t ON a.tenant_id = t.tenant_id
                ORDER BY a.detection_time DESC
                LIMIT 1000
            """)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                
                # Convert detection_time to datetime (timezone-naive)
                df['detection_time'] = pd.to_datetime(df['detection_time']).dt.tz_localize(None)
                df['age_hours'] = (pd.Timestamp.now() - df['detection_time']).dt.total_seconds() / 3600
                
                # Calculate simulated resolution time for resolved/closed alerts
                # Based on severity and some randomness
                import numpy as np
                def calculate_resolution_time(row):
                    if row['status'] in ['RESOLVED', 'CLOSED']:
                        # Base resolution times by severity (in hours)
                        base_times = {
                            'CRITICAL': 4,
                            'HIGH': 12,
                            'MEDIUM': 24,
                            'LOW': 48
                        }
                        base = base_times.get(row['severity'], 24)
                        # Add randomness (±50%)
                        variation = np.random.uniform(0.5, 1.5)
                        return base * variation
                    else:
                        return row['age_hours']
                
                df['resolution_hours'] = df.apply(calculate_resolution_time, axis=1)
                
                # KPI Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Alerts", len(df))
                
                with col2:
                    critical_count = len(df[df['severity'] == 'CRITICAL'])
                    st.metric("Critical Alerts", critical_count, delta=None, delta_color="inverse")
                
                with col3:
                    open_count = len(df[df['status'].isin(['OPEN', 'INVESTIGATING'])])
                    st.metric("Open/Active", open_count)
                
                with col4:
                    resolved_count = len(df[df['status'].isin(['RESOLVED', 'CLOSED'])])
                    st.metric("Resolved", resolved_count)
                
                st.markdown("---")
                
                # Filters
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    severity_filter = st.multiselect(
                        "Severity",
                        options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
                        default=['CRITICAL', 'HIGH']
                    )
                
                with col2:
                    status_filter = st.multiselect(
                        "Status",
                        options=df['status'].unique().tolist(),
                        default=['OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED']
                    )
                
                with col3:
                    alert_type_filter = st.multiselect(
                        "Alert Type",
                        options=df['alert_type'].unique().tolist(),
                        default=df['alert_type'].unique().tolist()
                    )
                
                with col4:
                    time_filter = st.selectbox(
                        "Time Range",
                        options=['Last 7d', 'Last 30d', 'Last 90d', 'All Time'],
                        index=1
                    )
                
                # Apply filters
                filtered_df = df.copy()
                
                if severity_filter:
                    filtered_df = filtered_df[filtered_df['severity'].isin(severity_filter)]
                if status_filter:
                    filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
                if alert_type_filter:
                    filtered_df = filtered_df[filtered_df['alert_type'].isin(alert_type_filter)]
                
                # Time filter
                if time_filter == 'Last 7d':
                    cutoff = datetime.now() - timedelta(days=7)
                    filtered_df = filtered_df[filtered_df['detection_time'] >= cutoff]
                elif time_filter == 'Last 30d':
                    cutoff = datetime.now() - timedelta(days=30)
                    filtered_df = filtered_df[filtered_df['detection_time'] >= cutoff]
                elif time_filter == 'Last 90d':
                    cutoff = datetime.now() - timedelta(days=90)
                    filtered_df = filtered_df[filtered_df['detection_time'] >= cutoff]
                
                # Tabs for different views
                tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🔍 Alert List", "📈 Trends"])
                
                with tab1:
                    # Analytics Charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Alerts by Severity")
                        severity_counts = filtered_df['severity'].value_counts()
                        fig = px.pie(
                            values=severity_counts.values,
                            names=severity_counts.index,
                            title="Alert Distribution by Severity",
                            color=severity_counts.index,
                            color_discrete_map={
                                'CRITICAL': '#d62728',
                                'HIGH': '#ff7f0e',
                                'MEDIUM': '#ffbb78',
                                'LOW': '#2ca02c'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Alerts by Status")
                        status_counts = filtered_df['status'].value_counts().reset_index()
                        status_counts.columns = ['Status', 'Count']
                        fig = px.bar(
                            status_counts,
                            x='Status',
                            y='Count',
                            title="Alert Status Distribution",
                            color='Status',
                            color_discrete_map={
                                'OPEN': '#ff6b6b',  # Light red
                                'INVESTIGATING': '#ffa500',  # Orange
                                'IN_PROGRESS': '#ffa500',  # Orange
                                'RESOLVED': '#2ca02c',  # Green
                                'CLOSED': '#20c997',  # Lighter green
                                'FALSE_POSITIVE': '#6c757d'  # Gray
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Alert Types")
                        type_counts = filtered_df['alert_type'].value_counts().head(10).reset_index()
                        type_counts.columns = ['Alert Type', 'Count']
                        fig = px.bar(
                            type_counts,
                            x='Count',
                            y='Alert Type',
                            orientation='h',
                            title="Top 10 Alert Types",
                            color_discrete_sequence=['#1f77b4']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Alerts by Industry")
                        industry_counts = filtered_df['industry'].value_counts().head(10).reset_index()
                        industry_counts.columns = ['Industry', 'Count']
                        fig = px.bar(
                            industry_counts,
                            x='Count',
                            y='Industry',
                            orientation='h',
                            title="Top 10 Industries by Alert Volume",
                            color_discrete_sequence=['#ff7f0e']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.subheader("Alert Details")
                    
                    # Search functionality
                    search = st.text_input("🔍 Search by alert name, tenant, or description", "")
                    if search:
                        filtered_df = filtered_df[
                            filtered_df['alert_name'].str.contains(search, case=False, na=False) |
                            filtered_df['tenant_name'].str.contains(search, case=False, na=False) |
                            filtered_df['description'].str.contains(search, case=False, na=False)
                        ]
                    
                    # Display alerts as expandable cards
                    st.info(f"📋 Showing {len(filtered_df)} alerts")
                    
                    for idx, row in filtered_df.head(50).iterrows():
                        # Severity emoji
                        severity_emoji = {
                            'CRITICAL': '🔴',
                            'HIGH': '🟠',
                            'MEDIUM': '🟡',
                            'LOW': '🟢'
                        }.get(row['severity'], '⚪')
                        
                        # Status emoji
                        status_emoji = {
                            'OPEN': '🆕',
                            'INVESTIGATING': '🔍',
                            'RESOLVED': '✅',
                            'CLOSED': '🔒',
                            'FALSE_POSITIVE': '❌'
                        }.get(row['status'], '❓')
                        
                        with st.expander(
                            f"{severity_emoji} {status_emoji} {row['alert_id']} - {row['alert_name']} | {row['tenant_name']}",
                            expanded=False
                        ):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown(f"**Alert Type:** `{row['alert_type']}`")
                                st.markdown(f"**Severity:** `{row['severity']}`")
                                st.markdown(f"**Status:** `{row['status']}`")
                                st.markdown(f"**Detected:** {row['detection_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                                st.markdown(f"**Age:** {row['age_hours']:.1f} hours")
                                st.markdown(f"**Affected Assets:** {row['affected_assets']}")
                                
                                if row['description']:
                                    st.markdown("**Description:**")
                                    st.info(row['description'])
                                
                                # Related Events Summary
                                st.markdown("---")
                                st.markdown("**📊 Related Events Summary**")
                                
                                events_df = get_related_events(row['alert_id'])
                                
                                if not events_df.empty:
                                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                                    
                                    with metric_col1:
                                        st.metric("📝 Total Events", len(events_df))
                                    
                                    with metric_col2:
                                        critical_events = len(events_df[events_df['severity'].isin(['CRITICAL', 'HIGH'])])
                                        st.metric("🔴 Critical/High", critical_events)
                                    
                                    with metric_col3:
                                        unique_ips = events_df['source_ip'].nunique()
                                        st.metric("🌐 Unique IPs", unique_ips)
                                    
                                    # Top event types
                                    st.markdown("**Top Event Types:**")
                                    event_counts = events_df['event_type'].value_counts().head(3)
                                    for event_type, count in event_counts.items():
                                        st.caption(f"• {event_type}: {count}")
                                else:
                                    st.caption("ℹ️ No related events found")
                            
                            with col2:
                                st.markdown(f"**Tenant:** {row['tenant_name']}")
                                st.markdown(f"**Industry:** {row['industry']}")
                                st.markdown(f"**Service Tier:** {row['service_tier']}")
                                st.markdown(f"**Risk Level:** {row['risk_level']}")
                                
                                if row['assigned_to']:
                                    st.markdown(f"**Assigned To:** {row['assigned_to']}")
                                else:
                                    st.warning("⚠️ Unassigned")
                                
                                # Security Score Gauge
                                st.markdown("---")
                                fig = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=row['security_score'],
                                    title={'text': "Security Score", 'font': {'size': 18, 'color': '#333'}},
                                    number={'font': {'size': 32, 'color': '#333'}},
                                    gauge={
                                        'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "#444"},
                                        'bar': {'color': "#1f77b4", 'thickness': 0.8},
                                        'bgcolor': 'rgba(0,0,0,0)',
                                        'borderwidth': 2,
                                        'bordercolor': "#ddd",
                                        'steps': [
                                            {'range': [0, 50], 'color': "#ff4444"},
                                            {'range': [50, 70], 'color': "#ff8c42"},
                                            {'range': [70, 85], 'color': "#ffd93d"},
                                            {'range': [85, 100], 'color': "#6bcf7f"}
                                        ],
                                        'threshold': {
                                            'line': {'color': "#d62728", 'width': 3},
                                            'thickness': 0.8,
                                            'value': 70
                                        }
                                    }
                                ))
                                fig.update_layout(
                                    height=280,
                                    margin=dict(l=20, r=20, t=50, b=20),
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='#333')
                                )
                                st.plotly_chart(fig, use_container_width=True)
                    
                    if len(filtered_df) > 50:
                        st.warning(f"⚠️ Showing first 50 of {len(filtered_df)} alerts. Use filters to narrow down results.")
                
                with tab3:
                    st.subheader("Alert Trends Over Time")
                    
                    # Time series of alerts
                    filtered_df['date'] = filtered_df['detection_time'].dt.date
                    daily_counts = filtered_df.groupby(['date', 'severity']).size().reset_index(name='count')
                    
                    fig = px.line(
                        daily_counts,
                        x='date',
                        y='count',
                        color='severity',
                        title='Daily Alert Volume by Severity',
                        labels={'date': 'Date', 'count': 'Alert Count'},
                        color_discrete_map={
                            'CRITICAL': '#d62728',
                            'HIGH': '#ff7f0e',
                            'MEDIUM': '#ffbb78',
                            'LOW': '#2ca02c'
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Alert resolution time
                    st.subheader("Alert Resolution Metrics")
                    
                    resolved_df = df[df['status'].isin(['RESOLVED', 'CLOSED'])]
                    if not resolved_df.empty:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            resolution_by_severity = resolved_df.groupby('severity')['resolution_hours'].mean().reset_index()
                            resolution_by_severity.columns = ['Severity', 'Avg Hours']
                            fig = px.bar(
                                resolution_by_severity,
                                x='Severity',
                                y='Avg Hours',
                                title='Average Resolution Time by Severity (hours)',
                                color_discrete_sequence=['#2ca02c']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            resolution_by_type = resolved_df.groupby('alert_type')['resolution_hours'].mean().head(10).reset_index()
                            resolution_by_type.columns = ['Alert Type', 'Avg Hours']
                            fig = px.bar(
                                resolution_by_type,
                                x='Avg Hours',
                                y='Alert Type',
                                orientation='h',
                                title='Average Resolution Time by Alert Type (Top 10)',
                                color_discrete_sequence=['#ff7f0e']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No resolved alerts in the selected time range")
                
            else:
                st.warning("No alert data found")
        
    except Exception as e:
        st.error(f"❌ Query error: {e}")
        st.exception(e)
else:
    st.error("Cannot connect to database. Check your credentials.")
