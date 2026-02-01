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
    page_title="Event Monitoring",
    page_icon="📊",
    layout="wide"
)

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

st.title("📊 Event Monitoring")
st.markdown("Real-time security event tracking and analysis")

# Get connection
conn = get_active_connection()

if conn:
    try:
        with conn.cursor() as cur:
            # Get event overview with tenant and alert info
            cur.execute("""
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
                LIMIT 2000
            """)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                
                # Convert event_timestamp to datetime (timezone-naive)
                df['event_timestamp'] = pd.to_datetime(df['event_timestamp']).dt.tz_localize(None)
                df['age_hours'] = (pd.Timestamp.now() - df['event_timestamp']).dt.total_seconds() / 3600
                
                # KPI Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Events", len(df))
                
                with col2:
                    critical_count = len(df[df['severity'].isin(['CRITICAL', 'HIGH'])])
                    st.metric("Critical/High", critical_count)
                
                with col3:
                    linked_count = len(df[df['alert_id'].notna()])
                    st.metric("Linked to Alerts", linked_count)
                
                with col4:
                    unique_tenants = df['tenant_id'].nunique()
                    st.metric("Affected Tenants", unique_tenants)
                
                st.markdown("---")
                
                # Filters
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    severity_filter = st.multiselect(
                        "Severity",
                        options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'],
                        default=['CRITICAL', 'HIGH', 'MEDIUM']
                    )
                
                with col2:
                    event_type_filter = st.multiselect(
                        "Event Type",
                        options=df['event_type'].unique().tolist(),
                        default=df['event_type'].unique().tolist()
                    )
                
                with col3:
                    alert_link_filter = st.selectbox(
                        "Alert Linkage",
                        options=['All Events', 'Linked to Alerts', 'Standalone Events'],
                        index=0
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
                if event_type_filter:
                    filtered_df = filtered_df[filtered_df['event_type'].isin(event_type_filter)]
                
                # Alert linkage filter
                if alert_link_filter == 'Linked to Alerts':
                    filtered_df = filtered_df[filtered_df['alert_id'].notna()]
                elif alert_link_filter == 'Standalone Events':
                    filtered_df = filtered_df[filtered_df['alert_id'].isna()]
                
                # Time filter
                if time_filter == 'Last 7d':
                    cutoff = datetime.now() - timedelta(days=7)
                    filtered_df = filtered_df[filtered_df['event_timestamp'] >= cutoff]
                elif time_filter == 'Last 30d':
                    cutoff = datetime.now() - timedelta(days=30)
                    filtered_df = filtered_df[filtered_df['event_timestamp'] >= cutoff]
                elif time_filter == 'Last 90d':
                    cutoff = datetime.now() - timedelta(days=90)
                    filtered_df = filtered_df[filtered_df['event_timestamp'] >= cutoff]
                
                # Tabs for different views
                tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🔍 Event List", "📈 Trends"])
                
                with tab1:
                    # Analytics Charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Events by Severity")
                        severity_counts = filtered_df['severity'].value_counts()
                        fig = px.pie(
                            values=severity_counts.values,
                            names=severity_counts.index,
                            title="Event Distribution by Severity",
                            color=severity_counts.index,
                            color_discrete_map={
                                'CRITICAL': '#d62728',
                                'HIGH': '#ff7f0e',
                                'MEDIUM': '#ffbb78',
                                'LOW': '#2ca02c',
                                'INFO': '#17becf'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Events by Type")
                        type_counts = filtered_df['event_type'].value_counts().reset_index()
                        type_counts.columns = ['Event Type', 'Count']
                        fig = px.bar(
                            type_counts,
                            x='Event Type',
                            y='Count',
                            title="Event Type Distribution",
                            color='Event Type',
                            color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Events by Industry")
                        industry_counts = filtered_df['industry'].value_counts().head(10).reset_index()
                        industry_counts.columns = ['Industry', 'Count']
                        fig = px.bar(
                            industry_counts,
                            x='Count',
                            y='Industry',
                            orientation='h',
                            title="Top 10 Industries by Event Volume",
                            color_discrete_sequence=['#1f77b4']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Alert Linkage")
                        linkage_data = pd.DataFrame({
                            'Type': ['Linked to Alerts', 'Standalone Events'],
                            'Count': [
                                len(df[df['alert_id'].notna()]),
                                len(df[df['alert_id'].isna()])
                            ]
                        })
                        fig = px.pie(
                            linkage_data,
                            values='Count',
                            names='Type',
                            title="Event-Alert Relationship",
                            color_discrete_sequence=['#2ca02c', '#ff7f0e']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.subheader("Event Details")
                    
                    # Search functionality
                    search = st.text_input("🔍 Search by event ID, tenant, hostname, username, or log", "")
                    if search:
                        filtered_df = filtered_df[
                            filtered_df['event_id'].str.contains(search, case=False, na=False) |
                            filtered_df['tenant_name'].str.contains(search, case=False, na=False) |
                            filtered_df['hostname'].str.contains(search, case=False, na=False) |
                            filtered_df['username'].str.contains(search, case=False, na=False) |
                            filtered_df['raw_log'].str.contains(search, case=False, na=False)
                        ]
                    
                    # Display events as expandable cards
                    st.info(f"📋 Showing {len(filtered_df)} events")
                    
                    for idx, row in filtered_df.head(100).iterrows():
                        # Severity emoji
                        severity_emoji = {
                            'CRITICAL': '🔴',
                            'HIGH': '🟠',
                            'MEDIUM': '🟡',
                            'LOW': '🟢',
                            'INFO': '🔵'
                        }.get(row['severity'], '⚪')
                        
                        # Event type icon
                        type_icon = {
                            'LOGIN': '🔐',
                            'LOGOUT': '🚪',
                            'FILE_ACCESS': '📁',
                            'NETWORK_CONNECTION': '🌐',
                            'PROCESS_EXECUTION': '⚙️'
                        }.get(row['event_type'], '📊')
                        
                        alert_badge = " 🚨" if pd.notna(row['alert_id']) else ""
                        
                        with st.expander(
                            f"{severity_emoji} {type_icon} {row['event_id']} - {row['event_type']} | {row['tenant_name']}{alert_badge}",
                            expanded=False
                        ):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown(f"**Event Type:** `{row['event_type']}`")
                                st.markdown(f"**Severity:** `{row['severity']}`")
                                st.markdown(f"**Timestamp:** {row['event_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                                st.markdown(f"**Age:** {row['age_hours']:.1f} hours")
                                
                                if pd.notna(row['hostname']):
                                    st.markdown(f"**Hostname:** {row['hostname']}")
                                if pd.notna(row['username']):
                                    st.markdown(f"**Username:** {row['username']}")
                                if pd.notna(row['source_ip']):
                                    st.markdown(f"**Source IP:** {row['source_ip']}")
                                
                                if pd.notna(row['raw_log']):
                                    st.markdown("**Raw Log:**")
                                    st.code(row['raw_log'], language=None)
                            
                            with col2:
                                st.markdown(f"**Tenant:** {row['tenant_name']}")
                                st.markdown(f"**Industry:** {row['industry']}")
                                st.markdown(f"**Service Tier:** {row['service_tier']}")
                                st.markdown(f"**Risk Level:** {row['risk_level']}")
                                
                                if pd.notna(row['alert_id']):
                                    st.success(f"🚨 Linked to Alert: {row['alert_id']}")
                                else:
                                    st.info("No associated alert")
                    
                    if len(filtered_df) > 100:
                        st.warning(f"⚠️ Showing first 100 of {len(filtered_df)} events. Use filters to narrow down results.")
                
                with tab3:
                    st.subheader("Event Trends Over Time")
                    
                    # Time series of events
                    filtered_df['date'] = filtered_df['event_timestamp'].dt.date
                    daily_counts = filtered_df.groupby(['date', 'severity']).size().reset_index(name='count')
                    
                    fig = px.line(
                        daily_counts,
                        x='date',
                        y='count',
                        color='severity',
                        title='Daily Event Volume by Severity',
                        labels={'date': 'Date', 'count': 'Event Count'},
                        color_discrete_map={
                            'CRITICAL': '#d62728',
                            'HIGH': '#ff7f0e',
                            'MEDIUM': '#ffbb78',
                            'LOW': '#2ca02c',
                            'INFO': '#17becf'
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Event type trends
                    st.subheader("Event Type Trends")
                    
                    type_daily = filtered_df.groupby(['date', 'event_type']).size().reset_index(name='count')
                    fig = px.area(
                        type_daily,
                        x='date',
                        y='count',
                        color='event_type',
                        title='Daily Event Volume by Type',
                        labels={'date': 'Date', 'count': 'Event Count'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.warning("No event data found")
        
    except Exception as e:
        st.error(f"❌ Query error: {e}")
        st.exception(e)
else:
    st.error("Cannot connect to database. Check your credentials.")
