import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
from databricks.sdk import WorkspaceClient

# Add parent directory to path to import db_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_postgres_connection

# Try to import GenieFeedbackRating from possible locations
try:
    from databricks.sdk.service.dashboards import GenieFeedbackRating
except ImportError:
    try:
        from databricks.sdk.service.sql import GenieFeedbackRating
    except ImportError:
        # Fallback: create a simple enum-like class
        class GenieFeedbackRating:
            POSITIVE = "POSITIVE"
            NEGATIVE = "NEGATIVE"

st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize Databricks Workspace Client
w = WorkspaceClient()

# AI Space ID - Update this with your actual AI Space ID
# You can get this from your Databricks workspace: AI/BI → AI spaces
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f0fd04cca91439ba25b90614a26e00")

CATALOG = "dnb_hackathon_west_2"
SCHEMA = "data_wolves"

# Helper functions for AI Assistant API
def get_query_result(statement_id: str) -> pd.DataFrame:
    """Fetch query results from Databricks statement execution."""
    try:
        result = w.statement_execution.get_statement(statement_id)
        if result.result and result.result.data_array:
            return pd.DataFrame(
                result.result.data_array,
                columns=[col.name for col in result.manifest.schema.columns]
            )
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching query results: {str(e)}")
        return pd.DataFrame()

def display_message(message: dict, display_content: bool = True):
    """Display a chat message with content, data, and code."""
    if display_content and "content" in message and message["content"]:
        st.markdown(message["content"])
    
    if "data" in message and message["data"] is not None and not message["data"].empty:
        st.dataframe(message["data"], use_container_width=True, hide_index=True)
    
    if "code" in message and message["code"]:
        with st.expander("🔍 View Generated SQL"):
            st.code(message["code"], language="sql", wrap_lines=True)

def collect_feedback(message_id: str, conversation_id: str, key_suffix: str):
    """Collect user feedback on AI Assistant response."""
    if not message_id or not conversation_id:
        return
    
    rating = st.feedback("thumbs", key=f"feedback_{key_suffix}")
    
    if rating is not None:
        mapping = {1: GenieFeedbackRating.POSITIVE, 0: GenieFeedbackRating.NEGATIVE}
        try:
            w.genie.send_message_feedback(
                GENIE_SPACE_ID,
                conversation_id,
                message_id,
                mapping[rating]
            )
            st.toast(f"Thanks for your feedback! ({'👍' if rating == 1 else '👎'})")
        except Exception as e:
            st.warning(f"Could not send feedback: {str(e)}")

def process_ai_response(response, display_content: bool = True) -> dict:
    """Process and display AI Assistant API response."""
    messages = []
    
    # Try to extract message_id from various possible locations
    message_id = getattr(response, 'message_id', None) or getattr(response, 'id', None)
    
    # Debug: show response structure
    if display_content:
        with st.expander("🔍 Debug: Response Structure", expanded=False):
            st.write("Response attributes:", dir(response))
            if hasattr(response, 'attachments'):
                st.write(f"Number of attachments: {len(response.attachments) if response.attachments else 0}")
                for i, att in enumerate(response.attachments or []):
                    st.write(f"Attachment {i} attributes:", dir(att))
    
    if not hasattr(response, 'attachments') or not response.attachments:
        return {
            "role": "assistant",
            "content": "🤔 No response from AI Assistant. Please try again.",
            "message_id": message_id
        }
    
    # Collect all data from attachments
    text_content = []
    query_data = None
    query_code = None
    
    for attachment in response.attachments:
        # Handle text attachments
        if hasattr(attachment, 'text') and attachment.text and hasattr(attachment.text, 'content'):
            text_content.append(attachment.text.content)
            if display_content:
                st.markdown(attachment.text.content)
        
        # Handle query attachments (don't use elif - there might be multiple attachments)
        if hasattr(attachment, 'query') and attachment.query:
            # Get query code
            if hasattr(attachment.query, 'query'):
                query_code = attachment.query.query
            
            # Get query results
            if hasattr(response, 'query_result') and response.query_result:
                if hasattr(response.query_result, 'statement_id') and response.query_result.statement_id:
                    query_data = get_query_result(response.query_result.statement_id)
            
            # Display if requested
            if display_content:
                if query_data is not None and not query_data.empty:
                    st.dataframe(query_data, use_container_width=True, hide_index=True)
                if query_code:
                    with st.expander("🔍 View Generated SQL"):
                        st.code(query_code, language="sql", wrap_lines=True)
    
    # Return consolidated message for history
    return {
        "role": "assistant",
        "content": "\n\n".join(text_content) if text_content else "Query results:",
        "data": query_data,
        "code": query_code,
        "message_id": message_id
    }

def get_suggested_questions() -> list[str]:
    """Return a list of suggested questions."""
    return [
        "Show me critical security alerts from the last 7 days",
        "Which tenants have the highest risk level?",
        "List all open support tickets for critical alerts",
        "What are the top 5 security event types by count?",
        "Show me tenants with security score below 60",
        "Which alerts are still unresolved?",
        "Show security events linked to critical alerts",
        "List all tenants in trial status with high risk",
        "What's the average resolution time for critical alerts?",
        "Show recent login events from suspicious IPs"
    ]

# Initialize session state
if "genie_messages" not in st.session_state:
    st.session_state.genie_messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# Page Header
st.title("🤖 AI Assistant")
st.markdown("Powered by **Databricks AI/BI** — Ask questions about your data in natural language")

# Check PostgreSQL connection
conn = get_postgres_connection()
if conn:
    st.success("✅ Connected to Lakebase PostgreSQL - `data_wolves` schema")
else:
    st.error("❌ Unable to connect to Lakebase PostgreSQL")
    st.stop()

st.divider()

# Suggested questions row
st.subheader("💡 Try asking...")
suggestion_cols = st.columns(5)
for i, q in enumerate(get_suggested_questions()[:5]):
    with suggestion_cols[i]:
        if st.button(q, key=f"suggest_{q}", use_container_width=True):
            st.session_state.genie_input = q
            st.rerun()

col_clear, col_info, _ = st.columns([1, 2, 3])
with col_clear:
    if st.button("🗑️ New Conversation", use_container_width=True):
        st.session_state.genie_messages = []
        st.session_state.conversation_id = None
        st.rerun()
with col_info:
    if st.session_state.conversation_id:
        st.caption(f"📍 Active conversation: `{st.session_state.conversation_id[:8]}...`")
    else:
        st.caption("💬 No active conversation")

st.divider()

# Main chat interface
chat_container = st.container(height=500)

with chat_container:
    # Welcome message if no history
    if not st.session_state.genie_messages:
        st.info("""
        👋 **Welcome to the AI Assistant!** 
        
        I'm your **AI Assistant** powered by Databricks. I can help you explore and analyze security operations data using natural language.
        
        **What I can do:**
        - Answer complex security questions in plain English
        - Generate optimized SQL queries automatically
        - Provide threat intelligence and insights
        - Analyze security patterns and trends
        
        **Available data:**
        - `{}.{}.lb_tenants1` — Customer organizations, security scores, risk levels
        - `{}.{}.lb_alerts` — Security alerts, detection times, severity levels
        - `{}.{}.lb_events` — Security events, IPs, usernames, event types
        - `{}.{}.support_tickets` — Support incidents, ticket status, activities
        
        Try clicking a suggested question above or ask your own!
        """.format(CATALOG, SCHEMA, CATALOG, SCHEMA, CATALOG, SCHEMA, CATALOG, SCHEMA))
    
    # Display chat history
    for idx, msg in enumerate(st.session_state.genie_messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                display_message(msg, display_content=True)
                
                # Add feedback for assistant messages
                if msg.get("message_id") and st.session_state.conversation_id:
                    collect_feedback(
                        msg["message_id"],
                        st.session_state.conversation_id,
                        f"{idx}_{msg['message_id']}"
                    )

# Chat input
default_input = st.session_state.get("genie_input", "")
if default_input:
    del st.session_state.genie_input

user_input = st.chat_input("Ask a question about your data...", key="genie_chat_input")

# Process input (either from chat or from suggestion button)
query_to_process = user_input or default_input

if query_to_process:
    # Add user message to history
    st.session_state.genie_messages.append({
        "role": "user",
        "content": query_to_process
    })
    
    # Process query with Genie API
    with st.spinner("🤖 AI Assistant is thinking..."):
        try:
            if st.session_state.conversation_id:
                # Continue existing conversation
                response = w.genie.create_message_and_wait(
                    GENIE_SPACE_ID,
                    st.session_state.conversation_id,
                    query_to_process
                )
            else:
                # Start new conversation
                response = w.genie.start_conversation_and_wait(
                    GENIE_SPACE_ID,
                    query_to_process
                )
                # Extract conversation_id from response
                st.session_state.conversation_id = getattr(response, 'conversation_id', None) or getattr(response, 'id', None)
            
            # Process response and add to history
            assistant_message = process_ai_response(response, display_content=False)
            st.session_state.genie_messages.append(assistant_message)
            
        except Exception as e:
            error_message = str(e)
            st.session_state.genie_messages.append({
                "role": "assistant",
                "content": f"❌ **Error communicating with AI Assistant:**\n\n{error_message}\n\n**Troubleshooting:**\n- Verify `GENIE_SPACE_ID` is correct\n- Ensure you have access to the AI space\n- Check workspace permissions\n- Try creating a new conversation",
                "message_id": None
            })
    
    st.rerun()

st.divider()

# Footer
st.caption(f"**Data Source:** {CATALOG}.{SCHEMA} | **AI Space:** {GENIE_SPACE_ID[:16]}...")
st.caption("🤖 Powered by Databricks AI/BI — Give feedback with 👍/👎 to improve responses")
