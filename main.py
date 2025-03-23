import streamlit as st

from dotenv import load_dotenv

from UI.Auth import AuthUI
from DB.index import database_manager
from UI.Instructor import InstructorUI
from UI.StudentUI.Student import StudentUI

# Load environment variables
load_dotenv()

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "email" not in st.session_state:
    st.session_state["email"] = None

# Setup DB connection and cursor

st.title("My Learning Companion")

if not st.session_state["logged_in"]:
    AuthUI()
else:
    # User is logged in
    st.subheader(f"Welcome, {st.session_state['email']}!")

    # Determine user role
    database_manager.cursor.execute(
        "SELECT role FROM users WHERE email = %s", (st.session_state["email"],)
    )
    user_role = database_manager.cursor.fetchone()[0]

    if user_role == "Instructor":
        InstructorUI()
    else:
        StudentUI()
