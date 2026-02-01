"""
Database utility functions for PostgreSQL connection
"""
import streamlit as st
import psycopg

@st.cache_resource
def get_postgres_connection():
    """
    Get a connection to the PostgreSQL (Databricks Lakebase) database.
    Connection parameters are retrieved from Streamlit secrets.
    
    Returns:
        psycopg.Connection: Database connection object or None if connection fails
    """
    try:
        token = st.secrets.get("db_token", "")
        
        conn_string = (
            f"host=ep-tiny-tooth-d1sdotnq.database.us-west-2.cloud.databricks.com "
            f"user=ankit.jain@arcticwolf.com "
            f"password={token} "
            f"dbname=databricks_postgres "
            f"port=5432 "
            f"sslmode=require "
            f"keepalives=1 "
            f"keepalives_idle=30 "
            f"keepalives_interval=10 "
            f"keepalives_count=5"
        )
        
        conn = psycopg.connect(conn_string)
        return conn
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        return None
    
def get_postgres_branch_connection(endpoint, token):
    """
    Get a connection to the PostgreSQL (Databricks Lakebase) database.
    Connection parameters are retrieved from Streamlit secrets.
    
    Returns:
        psycopg.Connection: Database connection object or None if connection fails
    """
    try:        
        conn_string = (
            f"host={endpoint} "
            f"user=83583b3e-5502-4d5a-a68d-7c741e06489c "
            f"password={token} "
            f"dbname=databricks_postgres "
            f"port=5432 "
            f"sslmode=require"
        )
        
        conn = psycopg.connect(conn_string)
        return conn
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        return None

def get_active_connection(endpoint=None, token=None):
    """
    Get an active database connection, reconnecting if necessary.
    
    Returns:
        psycopg.Connection: Active database connection or None if connection fails
    """
    if endpoint and token:
        conn = get_postgres_branch_connection(endpoint, token)
    else:
        conn = get_postgres_connection()
    
    if conn:
        try:
            # Test if connection is still alive
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except Exception:
            # Connection is dead, clear cache and reconnect
            st.cache_resource.clear()
            if endpoint and token:
                return get_postgres_branch_connection(endpoint, token)
            else:
                return get_postgres_connection()
    
    return None

def test_connection():
    """Test the database connection and display status"""
    conn = get_active_connection()
    if conn:
        st.success("✅ Connected to database successfully!")
        return conn
    else:
        st.error("❌ Failed to connect to database")
        return None
