import streamlit as st
import re
from API.auth import auth_handler

def is_valid_email(email):
    """Check if the email is valid."""
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

def LogInUI():
    st.header("Login")
    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        if not login_email or not login_password:
            st.error("Email and Password are required.")
        elif not is_valid_email(login_email):
            st.error("Please enter a valid email address.")
        elif auth_handler.validate_user(login_email, login_password):
            st.session_state["logged_in"] = True
            st.session_state["email"] = login_email
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid credentials")

def SignUpUI():
    st.header("Register")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password (USE FAKE PASSWORD)", type="password", key="reg_password")
    reg_role = st.selectbox("Register as", ["Student"], key="reg_role") # Remove "Instructor" for user testing
    st.write("Your School ID is automatically set to 123456 for user testing and cannot be changed.")
    # reg_school_id = st.text_input("Join School ID (Default User Testing Group)", key="reg_school_id")
    reg_school_id = "123456"

    if st.button("Register"):
        if not reg_email or not reg_password or not reg_school_id:
            st.error("All fields are required.")
        elif not is_valid_email(reg_email):
            st.error("Please enter a valid email address.")
        elif not reg_school_id.isdigit():
            st.error("School ID must be a numeric value.")
        elif auth_handler.user_exists(reg_email):
            st.error("User already exists, please login.")
        else:
            try:
                auth_handler.register_user(
                    reg_email, reg_password, int(reg_school_id), reg_role
                )
                st.success("Registration successful! You can now log in.")
            except Exception as e:
                st.error(f"Registration failed: {e}")

def AuthUI():
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        LogInUI()
    with tab2:
        SignUpUI()