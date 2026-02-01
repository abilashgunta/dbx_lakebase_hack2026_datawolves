import streamlit as st
import base64
from datetime import datetime
import time

st.set_page_config(
    page_title="Home - DataWolves Analytics",
    page_icon="🏠",
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

/* Sidebar background */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f0f0f0 0%, #e0e0e0 100%);
}

/* Make logo bigger */
[data-testid="stLogo"] img {
    width: 100% !important;
    max-width: none !important;
    height: auto !important;
}
[data-testid="stSidebarNav"] + div img {
    width: 100% !important;
    max-width: none !important;
    height: auto !important;
}

/* Make links more visible and clickable */
a {
    text-decoration: underline !important;
    cursor: pointer;
    transition: all 0.3s ease;
}

a:hover {
    color: #667eea !important;
    text-decoration: underline !important;
    opacity: 0.8;
}
</style>
""", unsafe_allow_html=True)

# Hero Section with Logo
# Read and encode the icon
with open("pages/additional_icons/AW_MARK_LOGO_STEEL.png", "rb") as img_file:
    img_data = base64.b64encode(img_file.read()).decode()

st.markdown(f"""
<div style='text-align: center;'>
    <img src='data:image/png;base64,{img_data}' style='width: 50px; height: auto; vertical-align: middle; margin-right: 10px; display: inline-block;'>
    <h1 style='display: inline-block; vertical-align: middle; margin: 0;'>Data Wolves Security Operations Center</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Real-time threat detection and incident response for 150+ organizations</p>", unsafe_allow_html=True)

st.divider()

# Key Metrics
st.markdown("### 📈 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 10px;'><a href='Tenants_Overview' target='_self' style='text-decoration: none; color: inherit;'><strong>Tenants Health</strong></a></h3>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-top: 0;'>150</h1></div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 10px;'><a href='Event_Monitoring' target='_self' style='text-decoration: none; color: inherit;'><strong>Events Posture</strong></a></h3>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-top: 0;'>800+</h1></div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 10px;'><a href='Alert_Management' target='_self' style='text-decoration: none; color: inherit;'><strong>Alert Management</strong></a></h3>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-top: 0;'>600</h1></div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 10px;'><a href='Support_Incident_Tool' target='_self' style='text-decoration: none; color: inherit;'><strong>Incident Response</strong></a></h3>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-top: 0;'>200</h1></div>", unsafe_allow_html=True)

st.divider()

# Security Status Dashboard
st.markdown("### 🛡️ Security Status Overview")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;'>
        <h4 style='margin: 0; color: white;'>🟢 System Status</h4>
        <p style='font-size: 1.5rem; margin: 10px 0 0 0; font-weight: bold;'>All Systems Operational</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style='padding: 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 10px; color: white;'>
        <h4 style='margin: 0; color: white;'>⚠️ Active Threats</h4>
        <p style='font-size: 1.5rem; margin: 10px 0 0 0; font-weight: bold;'>3 Critical | 12 High</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    current_time = datetime.now().strftime("%H:%M:%S %Z")
    st.markdown(f"""
    <div style='padding: 20px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border-radius: 10px; color: white;'>
        <h4 style='margin: 0; color: white;'>🕒 Current Time</h4>
        <p style='font-size: 1.5rem; margin: 10px 0 0 0; font-weight: bold;'>{current_time}</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Recent Activity Feed
st.markdown("### 📊 Recent Security Activity")

st.markdown("""
<div style='background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; border-left: 4px solid #f5576c;'>
    <p style='margin: 0; font-weight: bold; color: #f5576c;'>🚨 Critical Alert - Unusual Login Activity</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #666;'>2 minutes ago • Tenant: Enterprise Corp</p>
</div>
""", unsafe_allow_html=True)
st.write("")
st.markdown("""
<div style='background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; border-left: 4px solid #ffa502;'>
    <p style='margin: 0; font-weight: bold; color: #ffa502;'>⚠️ High Priority - Multiple Failed Logins</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #666;'>15 minutes ago • Tenant: TechStart Inc</p>
</div>
""", unsafe_allow_html=True)
st.write("")
st.markdown("""
<div style='background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; border-left: 4px solid #4facfe;'>
    <p style='margin: 0; font-weight: bold; color: #4facfe;'>ℹ️ Info - System Update Completed</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #666;'>1 hour ago • All Systems</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Call to Action

# Footer
st.caption("**Catalog:** dnb_hackathon_west_2 | **Schema:** data_wolves | Built with Databricks & Streamlit")
