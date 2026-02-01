import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path to import db_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_active_connection

st.set_page_config(page_title="Support Incident Tool", page_icon="🎫", layout="wide")

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

st.title("🎫 Support Incident Tool")
st.markdown("### Manage and update customer support tickets")

# Agent name input
if 'agent_name' not in st.session_state:
    st.session_state.agent_name = 'Ankit Jain'

col1, col2 = st.columns([3, 1])
with col1:
    # Display success message if it exists in session state
    if 'update_message' in st.session_state:
        st.success(st.session_state.update_message)
        del st.session_state.update_message

    # Display error message if it exists in session state
    if 'error_message' in st.session_state:
        st.error(st.session_state.error_message)
        del st.session_state.error_message

with col2:
    agent_name = st.text_input("👤 Your Name", value=st.session_state.agent_name, key="agent_name_input")
    if agent_name != st.session_state.agent_name:
        st.session_state.agent_name = agent_name

# Get connection
conn = get_active_connection()

if conn:
    try:
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📋 Existing Tickets", "🚨 Alerts Without Tickets"])
        
        with tab1:
            with conn.cursor() as cur:
                # Query support_tickets table with tenant and alert info
                cur.execute("""
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
                """)
                
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            
            conn.commit()  # Commit after successful read
            
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                
                # KPI Metrics
                st.markdown("---")
                
                # Calculate metrics
                total_tickets = len(df)
                open_tickets = len(df[df['activity_type'] == 'OPEN'])
                investigating_tickets = len(df[df['activity_type'] == 'INVESTIGATING'])
                acknowledged_tickets = len(df[df['activity_type'] == 'ACKNOWLEDGED'])
                closed_tickets = len(df[df['activity_type'] == 'CLOSED'])
                critical_tickets = len(df[df['alert_severity'] == 'CRITICAL'])
                high_tickets = len(df[df['alert_severity'] == 'HIGH'])
                medium_tickets = len(df[df['alert_severity'] == 'MEDIUM'])
                low_tickets = len(df[df['alert_severity'] == 'LOW'])
                
                # Two column layout for better organization
                left_col, right_col = st.columns(2)
                
                with left_col:
                    st.markdown("### 📋 Ticket Status")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Total", total_tickets)
                    with col2:
                        st.metric("Open", open_tickets)
                    with col3:
                        st.metric("Investigating", investigating_tickets)
                    with col4:
                        st.metric("Acknowledged", acknowledged_tickets)
                    with col5:
                        st.metric("Closed", closed_tickets)
                
                with right_col:
                    st.markdown("### 🎯 Alert Priority")
                    col6, col7, col8, col9 = st.columns(4)
                    with col6:
                        st.metric("🔴 Critical", critical_tickets)
                    with col7:
                        st.metric("🟠 High", high_tickets)
                    with col8:
                        st.metric("🟡 Medium", medium_tickets)
                    with col9:
                        st.metric("🟢 Low", low_tickets)
                
                # Filters
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    activity_types = ['All'] + sorted(df['activity_type'].unique().tolist())
                    selected_activity = st.selectbox("Incident Status", activity_types)
                
                with col2:
                    severities = ['All'] + sorted([s for s in df['alert_severity'].unique() if s is not None])
                    selected_severity = st.selectbox("Alert Priority", severities)
                
                with col3:
                    tenants = ['All'] + sorted(df['tenant_name'].dropna().unique().tolist())
                    selected_tenant = st.selectbox("Tenant", tenants)
                
                with col4:
                    search_term = st.text_input("Search (Ticket ID, User, Comment)")
                
                # Apply filters
                filtered_df = df.copy()
                if selected_activity != 'All':
                    filtered_df = filtered_df[filtered_df['activity_type'] == selected_activity]
                if selected_severity != 'All':
                    filtered_df = filtered_df[filtered_df['alert_severity'] == selected_severity]
                if selected_tenant != 'All':
                    filtered_df = filtered_df[filtered_df['tenant_name'] == selected_tenant]
                if search_term:
                    mask = (
                        filtered_df['ticket_id'].astype(str).str.contains(search_term, case=False, na=False) |
                        filtered_df['user_name'].astype(str).str.contains(search_term, case=False, na=False) |
                        filtered_df['comment'].astype(str).str.contains(search_term, case=False, na=False)
                    )
                    filtered_df = filtered_df[mask]
                
                st.markdown("---")
                st.subheader(f"📋 Tickets ({len(filtered_df)} found)")
                
                # Sort by priority: CRITICAL > HIGH > MEDIUM > LOW > None
                priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, None: 4}
                filtered_df['priority_rank'] = filtered_df['alert_severity'].map(priority_order)
                filtered_df = filtered_df.sort_values(['priority_rank', 'activity_timestamp'], ascending=[True, False])
                
                # Display tickets with update functionality
                for idx, row in filtered_df.iterrows():
                    # Priority indicator
                    priority_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠', 
                        'MEDIUM': '🟡',
                        'LOW': '🟢',
                        None: '⚪'
                    }.get(row['alert_severity'], '⚪')
                    
                    with st.expander(f"{priority_emoji} Ticket #{row['ticket_id']} - {row['activity_type']} - {row['alert_severity'] or 'No Priority'} - {row['tenant_name'] or 'Unknown Tenant'}"):
                        col_info, col_update = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"**Tenant:** {row['tenant_name'] or 'N/A'} (ID: {row['tenant_id']})")
                            st.markdown(f"**Alert ID:** {row['alert_id'] or 'N/A'}")
                            if row['alert_severity']:
                                st.markdown(f"**Alert Priority:** {row['alert_severity']} ({row['alert_type'] or 'N/A'})")
                            st.markdown(f"**User:** {row['user_name']}")
                            st.markdown(f"**Activity Type:** {row['activity_type']}")
                            st.markdown(f"**Timestamp:** {row['activity_timestamp']}")
                            st.markdown(f"**Comment:** {row['comment'] or 'N/A'}")
                        
                        with col_update:
                            st.markdown("#### Update Ticket")
                            
                            # Activity type selector
                            new_activity_type = st.selectbox(
                                "Status",
                            ['OPEN', 'INVESTIGATING', 'ACKNOWLEDGED', 'CLOSED'],
                            index=['OPEN', 'INVESTIGATING', 'ACKNOWLEDGED', 'CLOSED'].index(row['activity_type']) if row['activity_type'] in ['OPEN', 'INVESTIGATING', 'ACKNOWLEDGED', 'CLOSED'] else 0,
                            key=f"activity_{row['ticket_id']}"
                        )
                        
                        # Comment field
                        new_comment = st.text_area(
                            "Add Comment",
                            value="",
                            key=f"comment_{row['ticket_id']}",
                            height=100
                        )
                        
                        # Update button
                        if st.button("💾 Update Ticket", key=f"update_{row['ticket_id']}"):
                            if new_comment:
                                try:
                                    with conn.cursor() as update_cur:
                                        update_cur.execute("""
                                            UPDATE data_wolves.support_tickets 
                                            SET user_name = %s,
                                                activity_type = %s,
                                                activity_timestamp = %s,
                                                comment = %s
                                            WHERE ticket_id = %s
                                        """, (
                                            st.session_state.agent_name,
                                            new_activity_type,
                                            datetime.now(),
                                            new_comment,
                                            row['ticket_id']
                                        ))
                                        conn.commit()
                                        st.session_state.update_message = f"✅ Ticket #{row['ticket_id']} status has been updated to: {new_activity_type}"
                                        st.rerun()
                                except Exception as update_error:
                                    st.error(f"❌ Failed to update ticket: {update_error}")
                                    conn.rollback()
                            else:
                                st.warning("⚠️ Please add a comment to update the ticket")
                
                st.markdown("---")
                st.caption(f"Showing {len(filtered_df)} of {len(df)} total tickets")
            else:
                st.warning("No tickets found in the database")
        
        # Tab 2: Alerts without tickets
        with tab2:
            with conn.cursor() as cur:
                # Get alerts that don't have tickets yet
                cur.execute("""
                    SELECT 
                        a.alert_id,
                        a.tenant_id,
                        t.tenant_name,
                        a.severity,
                        a.alert_type,
                        a.alert_name,
                        a.affected_assets,
                        a.detection_time,
                        a.description,
                        a.status,
                        a.assigned_to
                    FROM data_wolves.lb_alerts a
                    LEFT JOIN data_wolves.support_tickets st ON a.alert_id = st.alert_id
                    LEFT JOIN data_wolves.lb_tenants1 t ON a.tenant_id = t.tenant_id
                    WHERE st.ticket_id IS NULL
                    ORDER BY 
                        CASE 
                            WHEN a.severity = 'CRITICAL' THEN 0
                            WHEN a.severity = 'HIGH' THEN 1
                            WHEN a.severity = 'MEDIUM' THEN 2
                            WHEN a.severity = 'LOW' THEN 3
                            ELSE 4
                        END,
                        a.detection_time DESC
                """)
                
                alert_columns = [desc[0] for desc in cur.description]
                alert_rows = cur.fetchall()
                
                # Get max ticket ID for next ticket generation
                cur.execute("""
                    SELECT ticket_id 
                    FROM data_wolves.support_tickets 
                    ORDER BY ticket_id DESC 
                    LIMIT 1
                """)
                max_ticket_row = cur.fetchone()
                
            conn.commit()
            
            if alert_rows:
                alerts_df = pd.DataFrame(alert_rows, columns=alert_columns)
                
                # Calculate next ticket ID
                if max_ticket_row and max_ticket_row[0]:
                    max_ticket_id = max_ticket_row[0]
                    # Extract number from ticket ID (e.g., "TKT200" -> 200)
                    import re
                    match = re.search(r'\d+', max_ticket_id)
                    if match:
                        next_ticket_num = int(match.group()) + 1
                    else:
                        next_ticket_num = 1
                else:
                    next_ticket_num = 1
                
                next_ticket_id = f"TKT{next_ticket_num}"
                
                # KPI Metrics for alerts without tickets
                st.markdown("### 🚨 Alerts Without Tickets")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Alerts", len(alerts_df))
                with col2:
                    critical_count = len(alerts_df[alerts_df['severity'] == 'CRITICAL'])
                    st.metric("🔴 Critical", critical_count)
                with col3:
                    high_count = len(alerts_df[alerts_df['severity'] == 'HIGH'])
                    st.metric("🟠 High", high_count)
                
                st.markdown("---")
                
                # Filters for alerts
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    alert_severities = ['All'] + sorted(alerts_df['severity'].unique().tolist())
                    selected_alert_severity = st.selectbox("Filter by Severity", alert_severities, key="alert_severity_filter")
                
                with col2:
                    alert_tenants = ['All'] + sorted(alerts_df['tenant_name'].dropna().unique().tolist())
                    selected_alert_tenant = st.selectbox("Filter by Tenant", alert_tenants, key="alert_tenant_filter")
                
                with col3:
                    alert_types = ['All'] + sorted(alerts_df['alert_type'].unique().tolist())
                    selected_alert_type = st.selectbox("Filter by Alert Type", alert_types, key="alert_type_filter")
                
                # Apply filters
                filtered_alerts_df = alerts_df.copy()
                if selected_alert_severity != 'All':
                    filtered_alerts_df = filtered_alerts_df[filtered_alerts_df['severity'] == selected_alert_severity]
                if selected_alert_tenant != 'All':
                    filtered_alerts_df = filtered_alerts_df[filtered_alerts_df['tenant_name'] == selected_alert_tenant]
                if selected_alert_type != 'All':
                    filtered_alerts_df = filtered_alerts_df[filtered_alerts_df['alert_type'] == selected_alert_type]
                
                st.markdown("---")
                st.subheader(f"🚨 Alerts Needing Tickets ({len(filtered_alerts_df)} found)")
                
                # Display alerts with create ticket functionality
                ticket_counter = next_ticket_num
                for idx, alert in filtered_alerts_df.iterrows():
                    # Priority indicator
                    priority_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠',
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }.get(alert['severity'], '⚪')
                    
                    with st.expander(f"{priority_emoji} Alert #{alert['alert_id']} - {alert['severity']} - {alert['alert_type']} - {alert['tenant_name'] or 'Unknown Tenant'}"):
                        col_info, col_create = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"**Alert ID:** {alert['alert_id']}")
                            st.markdown(f"**Tenant:** {alert['tenant_name'] or 'N/A'} (ID: {alert['tenant_id']})")
                            st.markdown(f"**Severity:** {alert['severity']}")
                            st.markdown(f"**Alert Type:** {alert['alert_type']}")
                            st.markdown(f"**Alert Name:** {alert['alert_name'] or 'N/A'}")
                            st.markdown(f"**Affected Assets:** {alert['affected_assets'] or 'N/A'}")
                            st.markdown(f"**Detection Time:** {alert['detection_time']}")
                            st.markdown(f"**Description:** {alert['description'] or 'N/A'}")
                            st.markdown(f"**Status:** {alert['status']}")
                            st.markdown(f"**Assigned To:** {alert['assigned_to'] or 'Unassigned'}")
                        
                        with col_create:
                            st.markdown("#### Create Ticket")
                            
                            current_ticket_id = f"TKT{ticket_counter}"
                            
                            # Initial status
                            initial_status = st.selectbox(
                                "Initial Status",
                                ['OPEN', 'INVESTIGATING', 'ACKNOWLEDGED'],
                                key=f"status_{alert['alert_id']}"
                            )
                            
                            # Initial comment
                            initial_comment = st.text_area(
                                "Initial Comment",
                                value=f"Ticket created for {alert['alert_type']} alert",
                                key=f"new_comment_{alert['alert_id']}",
                                height=100
                            )
                            
                            # Create ticket button
                            if st.button("✅ Create Ticket", key=f"create_{alert['alert_id']}", type="primary", use_container_width=True):
                                if initial_comment:
                                    st.info("🔄 Creating support ticket, please wait...")
                                    try:
                                        with conn.cursor() as create_cur:
                                            create_cur.execute("""
                                                INSERT INTO data_wolves.support_tickets 
                                                (ticket_id, tenant_id, alert_id, user_name, activity_type, 
                                                 activity_timestamp, comment, is_customer_facing, customer_message)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (
                                                current_ticket_id,
                                                alert['tenant_id'],
                                                alert['alert_id'],
                                                st.session_state.agent_name,
                                                initial_status,
                                                datetime.now(),
                                                initial_comment,
                                                False,
                                                None
                                            ))
                                            conn.commit()
                                        st.session_state.update_message = f"✅ Support ticket: {current_ticket_id} has been created for Alert ID: {alert['alert_id']}"
                                        st.rerun()
                                    except Exception as create_error:
                                        st.error(f"❌ Failed to create ticket: {create_error}")
                                        st.session_state.error_message = f"❌ Failed to create ticket: {create_error}"
                                        conn.rollback()
                                else:
                                    st.warning("⚠️ Please add an initial comment")
                        
                        ticket_counter += 1
                
                st.markdown("---")
                st.caption(f"Showing {len(filtered_alerts_df)} alerts without tickets")
            else:
                st.success("✅ All alerts have tickets assigned!")
        
    except Exception as e:
        st.error(f"❌ Query error: {e}")
        conn.rollback()
else:
    st.warning("Cannot connect to database. Check your credentials.")
