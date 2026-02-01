import streamlit as st

# Set logo for entire app
st.logo("pages/additional_icons/Logo Steel-FY25.png")

def main():
    """Application entry point - redirects to Home page."""
    st.switch_page("pages/1_Home.py")

if __name__ == "__main__":
    main() 