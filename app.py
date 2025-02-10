import sqlite3
import os
import re
import pandas as pd
import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Initialize SQLite database
DB_FILE = "user_credentials.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True, "Registration successful! You can now log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose a different one."
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return True, "Login successful!"
    else:
        return False, "Invalid username or password. Please try again."

# Function to validate email addresses using regex
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

# Function to send emails
def send_bulk_emails(sender_email, sender_password, smtp_server, smtp_port, email_subject, email_body, recipient_emails):
    failed_recipients = []
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            
            for recipient in recipient_emails:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient
                msg['Subject'] = email_subject
                msg.attach(MIMEText(email_body, 'plain'))
                
                try:
                    server.send_message(msg)
                except Exception:
                    failed_recipients.append(recipient)
        
        return failed_recipients
    except Exception as e:
        st.error(f"An error occurred while connecting to the SMTP server: {str(e)}")
        return recipient_emails

# Main app function
def main():
    st.set_page_config(page_title="Bulk Email Sender", layout="wide")

    # Initialize the database
    init_db()

    # Handle session state for login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None

    if not st.session_state.logged_in:
        st.title("Welcome to Bulk Email Sender")
        st.subheader("Please log in or register to continue.")

        login_tab, register_tab = st.tabs(["Log In", "Register"])
        
        # Login tab
        with login_tab:
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_button = st.button("Log In")

            if login_button:
                success, message = login_user(login_username, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    st.success(message)
                    st.rerun()  # Refresh the page
                else:
                    st.error(message)
        
        # Register tab
        with register_tab:
            register_username = st.text_input("New Username", key="register_username")
            register_password = st.text_input("New Password", type="password", key="register_password")
            register_button = st.button("Register")

            if register_button:
                if not register_username or not register_password:
                    st.error("Both username and password are required.")
                else:
                    success, message = register_user(register_username, register_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    else:
        # Logged-in user interface
        st.sidebar.markdown(f"**Logged in as: {st.session_state.username}**")
        if st.sidebar.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

        # Bulk Email Sender functionality
        st.title("Bulk Email Sender")

        # Display logo and tagline
        logo_path = r"C:\Users\Admin\Desktop\bulk email\logo.png"  # Update with your logo file path
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)  # Adjust width to make the logo smaller
            st.markdown("<h3 style='text-align: left; font-size: 28px;'>Achievements Assured</h3>", unsafe_allow_html=True)
        else:
            st.warning("Logo not found. Please check the file path.")
        
        # File uploader for CSV and Excel files
        uploaded_file = st.file_uploader("Upload your CSV or Excel file containing emails", type=["csv", "xlsx", "xls"])

        if uploaded_file:
            try:
                # Determine file type and load data accordingly
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                else:
                    st.error("Unsupported file type. Please upload a CSV or Excel file.")
                    return
                
                # Case-insensitive check for 'email' column
                email_column = [col for col in df.columns if col.strip().lower() == "email"]
                
                if not email_column:
                    st.error("The uploaded file must contain a column named 'email'.")
                    return
                
                email_column = email_column[0]
                
                # Remove duplicates and validate emails
                df['email_valid'] = df[email_column].apply(lambda x: is_valid_email(str(x).strip()))
                valid_emails = df[df['email_valid']][email_column].drop_duplicates().tolist()
                
                if not valid_emails:
                    st.error("No valid email addresses found in the uploaded file.")
                    return

                st.success(f"Found {len(valid_emails)} valid email addresses.")
                st.write("Preview of valid emails:")
                st.write(valid_emails)

                # Email configuration form
                with st.form(key="email_form"):
                    sender_email = st.text_input("Sender Email")
                    sender_password = st.text_input("Sender Password", type="password")
                    smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
                    smtp_port = st.number_input("SMTP Port", value=587, step=1)
                    email_subject = st.text_input("Email Subject")
                    email_body = st.text_area("Email Body")
                    
                    # Submit button
                    submit_button = st.form_submit_button("Send Emails")
                    
                    if submit_button:
                        if not sender_email or not sender_password or not email_subject or not email_body:
                            st.error("Please fill in all the required fields.")
                        else:
                            st.info("Sending emails... please wait.")
                            failed_emails = send_bulk_emails(
                                sender_email, sender_password, smtp_server, smtp_port, 
                                email_subject, email_body, valid_emails
                            )
                            
                            if failed_emails:
                                st.warning(f"Failed to send emails to {len(failed_emails)} recipients.")
                                st.write("Failed recipients:")
                                st.write(failed_emails)
                            else:
                                st.success("All emails were sent successfully!")

            except Exception as e:
                st.error(f"An error occurred while processing the file: {str(e)}")

if __name__ == "__main__":
    main()
