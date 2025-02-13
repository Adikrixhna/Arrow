import sqlite3
import os
import re
import pandas as pd
import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.comments import Comment

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
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zAZ0-9.-]+\.[a-zA-Z]{2,}$'
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

# Function to create a sample Excel template with Name and Email columns and a comment in the first row
def generate_sample_excel_template():
    # Sample data with Name and Email columns
    data = {
        "Name": ["John Doe", "Jane Smith", "Alice Brown"],
        "Email": ["johndoe@example.com", "janesmith@example.com", "alicebrown@example.com"]
    }
    
    # Create a DataFrame from the sample data
    df = pd.DataFrame(data)
    
    # Create an Excel Workbook
    wb = Workbook()
    ws = wb.active

    # Add the dataframe to the worksheet
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    # Add a comment to the first row (header row)
    comment = Comment("This is supposed to be in the first row only", "Arrow App")
    ws["A1"].comment = comment  # Add the comment to cell A1

    # Save the workbook to an in-memory buffer
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)  # Go to the beginning of the buffer to read from it
    
    return excel_buffer

# Main app function
def main():
    st.set_page_config(page_title="Arrow", layout="wide", initial_sidebar_state="expanded")

    # Initialize the database
    init_db()

    # Handle session state for login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None

    # Create a more welcoming page title
    if not st.session_state.logged_in:
        st.title("Welcome to Arrow 🚀")

        # Move the login or register message below the title
        st.markdown("""
            <div style="text-align:left; font-size: 18px; color: #1d3557; margin-top: 20px;">
                Please log in or register to continue.
            </div>
        """, unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["Log In", "Register"])

        # Login tab with modernized layout
        with login_tab:
            col1, col2 = st.columns([3, 1])
            with col1:
                login_username = st.text_input("Username", key="login_username")
                login_password = st.text_input("Password", type="password", key="login_password")
            with col2:
                login_button = st.button("Log In", use_container_width=True)

            if login_button:
                success, message = login_user(login_username, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    st.success(message)
                    st.rerun()  # Refresh the page
                else:
                    st.error(message)

        # Register tab with better spacing
        with register_tab:
            col1, col2 = st.columns([3, 1])
            with col1:
                register_username = st.text_input("New Username", key="register_username")
                register_password = st.text_input("New Password", type="password", key="register_password")
            with col2:
                register_button = st.button("Register", use_container_width=True)

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
        st.sidebar.markdown(f"**Logged in as: {st.session_state.username}**", unsafe_allow_html=True)
        if st.sidebar.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

        # Arrow functionality
        st.title("Arrow - Your Email Assistant")

        # Display logo and tagline with better alignment
        logo_path = r"logo.png"  # Update with your logo file path
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)  # Adjust width to make the logo smaller
            st.markdown("<h3 style='text-align: center;'>Achievements Assured 🚀</h3>", unsafe_allow_html=True)
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
                valid_emails_df = df[df['email_valid']][['Name', email_column]].drop_duplicates()
                
                if valid_emails_df.empty:
                    st.error("No valid email addresses found in the uploaded file.")
                    return

                st.success(f"Found {len(valid_emails_df)} valid email addresses.")
                # Removed the table preview
                valid_emails_df['selected'] = valid_emails_df[email_column].apply(lambda x: st.checkbox(f"Send to {x}", key=x))
                selected_emails = valid_emails_df[valid_emails_df['selected']][email_column].tolist()
                
                if selected_emails:
                    st.write("Selected Emails: ")
                    st.write(selected_emails)

            except Exception as e:
                st.error(f"An error occurred while processing the file: {str(e)}")

        # Show the sample template download button
        st.subheader("Download Sample Excel Template")
        st.write("Download the Excel template that contains the required `email` column to upload your contacts.")

        # Provide a button to allow the user to download the template
        excel_template = generate_sample_excel_template()
        st.download_button(
            label="Download Sample Excel Template",
            data=excel_template,
            file_name="email_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Email configuration form with a more intuitive form layout
        with st.form(key="email_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                sender_email = st.text_input("Sender Email")
                sender_password = st.text_input("Sender Password", type="password")
                smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
                smtp_port = st.number_input("SMTP Port", value=587, step=1)
            with col2:
                email_subject = st.text_input("Email Subject")
                email_body = st.text_area("Email Body")

            submit_button = st.form_submit_button("Send Emails 🚀", use_container_width=True)

            # Create a placeholder for the "Sending emails... please wait" message
            status_placeholder = st.empty()

            if submit_button:
                if not sender_email or not sender_password or not email_subject or not email_body:
                    st.error("Please fill in all the required fields.")
                else:
                    status_placeholder.info("Sending emails... please wait.")
                    failed_emails = send_bulk_emails(
                        sender_email, sender_password, smtp_server, smtp_port, 
                        email_subject, email_body, selected_emails
                    )
                    
                    if failed_emails:
                        st.warning(f"Failed to send emails to {len(failed_emails)} recipients.")
                        st.write("Failed recipients:")
                        st.write(failed_emails)
                    else:
                        status_placeholder.empty()  # Remove the "Sending emails..." message
                        st.success("All emails were sent successfully! 🚀")

if __name__ == "__main__":
    main()

