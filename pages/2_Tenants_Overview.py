import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add parent directory to path to import db_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_active_connection

st.set_page_config(
    page_title="Tenant Overview",
    page_icon="🏢",
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

st.title("🏢 Tenant Overview")
st.markdown("Security posture and statistics for all customer organizations")

# Get connection
conn = get_active_connection()

if conn:
    try:
        with conn.cursor() as cur:
            # Get tenant overview
            cur.execute("""
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
            """)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                
                # KPI Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Tenants", len(df))
                
                with col2:
                    active_count = len(df[df['status'] == 'ACTIVE'])
                    st.metric("Active Tenants", active_count)
                
                with col3:
                    avg_security_score = df['security_score'].mean()
                    st.metric("Avg Security Score", f"{avg_security_score:.1f}")
                
                with col4:
                    total_tickets = df['total_tickets'].sum()
                    st.metric("Total Tickets", int(total_tickets))
                
                st.markdown("---")
                
                # Filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    industries = ['All'] + sorted(df['industry'].unique().tolist())
                    selected_industry = st.selectbox("Industry", industries)
                
                with col2:
                    risk_levels = ['All'] + sorted(df['risk_level'].unique().tolist())
                    selected_risk = st.selectbox("Risk Level", risk_levels)
                
                with col3:
                    service_tiers = ['All'] + sorted(df['service_tier'].unique().tolist())
                    selected_tier = st.selectbox("Service Tier", service_tiers)
                
                # Apply filters
                filtered_df = df.copy()
                if selected_industry != 'All':
                    filtered_df = filtered_df[filtered_df['industry'] == selected_industry]
                if selected_risk != 'All':
                    filtered_df = filtered_df[filtered_df['risk_level'] == selected_risk]
                if selected_tier != 'All':
                    filtered_df = filtered_df[filtered_df['service_tier'] == selected_tier]
                
                # Charts
                tab1, tab2 = st.tabs(["📊 Overview", "📋 Details"])
                
                with tab1:
                    # Pie Charts Row
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Risk Level Distribution")
                        risk_counts = filtered_df['risk_level'].value_counts()
                        fig = px.pie(
                            values=risk_counts.values,
                            names=risk_counts.index,
                            title="Tenants by Risk Level",
                            color_discrete_sequence=px.colors.sequential.RdBu_r
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Customer Status: Trial vs Active")
                        status_counts = filtered_df['status'].value_counts()
                        fig = px.pie(
                            values=status_counts.values,
                            names=status_counts.index,
                            title="Customer Status Distribution",
                            color_discrete_map={
                                'ACTIVE': '#2ca02c',
                                'TRIAL': '#ff7f0e',
                                'SUSPENDED': '#d62728'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Bar Charts Row
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Service Tier Distribution")
                        tier_counts = filtered_df['service_tier'].value_counts()
                        fig = px.bar(
                            x=tier_counts.index,
                            y=tier_counts.values,
                            title="Tenants by Service Tier",
                            labels={'x': 'Service Tier', 'y': 'Number of Tenants'},
                            color_discrete_sequence=['#2ca02c']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Industry Distribution")
                        industry_counts = filtered_df['industry'].value_counts().head(10)
                        fig = px.bar(
                            x=industry_counts.values,
                            y=industry_counts.index,
                            orientation='h',
                            title="Top 10 Industries",
                            labels={'x': 'Number of Tenants', 'y': 'Industry'},
                            color_discrete_sequence=['#ff7f0e']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.subheader("Tenant Details")
                    
                    # Add search functionality
                    search = st.text_input("🔍 Search by tenant name", "")
                    if search:
                        filtered_df = filtered_df[filtered_df['tenant_name'].str.contains(search, case=False)]
                    
                    # Display dataframe with formatting
                    display_df = filtered_df[[
                        'tenant_name', 'industry', 'company_size', 'service_tier',
                        'security_score', 'risk_level', 'total_tickets', 'status'
                    ]].copy()
                    
                    # Style the dataframe
                    def color_risk(val):
                        if val == 'CRITICAL':
                            return 'background-color: #d32f2f; color: white; font-weight: bold'
                        elif val == 'HIGH':
                            return 'background-color: #f57c00; color: white; font-weight: bold'
                        elif val == 'MEDIUM':
                            return 'background-color: #fbc02d; color: black; font-weight: bold'
                        elif val == 'LOW':
                            return 'background-color: #388e3c; color: white; font-weight: bold'
                        return ''
                    
                    def color_score(val):
                        if val >= 90:
                            return 'background-color: #388e3c; color: white; font-weight: bold'
                        elif val >= 70:
                            return 'background-color: #fbc02d; color: black; font-weight: bold'
                        elif val >= 50:
                            return 'background-color: #f57c00; color: white; font-weight: bold'
                        else:
                            return 'background-color: #d32f2f; color: white; font-weight: bold'
                    
                    styled_df = display_df.style.applymap(
                        color_risk, subset=['risk_level']
                    ).applymap(
                        color_score, subset=['security_score']
                    )
                    
                    st.dataframe(styled_df, use_container_width=True, height=600)
                    st.success(f"✅ Showing {len(filtered_df)} tenants")
                
            else:
                st.warning("No tenant data found")
        
    except Exception as e:
        st.error(f"❌ Query error: {e}")
else:
    st.error("Cannot connect to database. Check your credentials.")
