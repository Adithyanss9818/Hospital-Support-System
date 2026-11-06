import streamlit as st
import sqlite3
import pandas as pd
import uuid
import hashlib
import hmac
import secrets
from datetime import datetime
from pathlib import Path

# ==================================================
# HOSPITAL ADMINISTRATION DIGITAL SUPPORT SYSTEM
# ==================================================

st.set_page_config(
    page_title="Hospital Administration",
    page_icon="🏥",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hospital_support.db"

DATASETS = [
    "appointments.csv",
    "billing.csv",
    "doctors.csv",
    "patients.csv",
    "treatments.csv"
]

STATUSES = [
    "Pending",
    "Under Review",
    "Resolved",
    "Rejected"
]

CATEGORIES = [
    "Appointment",
    "Billing",
    "Doctor Information",
    "Treatment Information",
    "General Enquiry"
]

# ==================================================
# DATABASE CONNECTION
# ==================================================

conn = sqlite3.connect(
    str(DB_PATH),
    check_same_thread=False
)

conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ENQUIRIES TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS enquiries (
    enquiry_id TEXT PRIMARY KEY,
    patient_name TEXT,
    email TEXT,
    phone TEXT,
    category TEXT,
    message TEXT,
    status TEXT,
    remarks TEXT,
    created_at TEXT
)
""")

# ENQUIRY HISTORY TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS enquiry_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enquiry_id TEXT,
    old_status TEXT,
    new_status TEXT,
    remarks TEXT,
    updated_at TEXT
)
""")

# STAFF USERS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS staff_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    salt TEXT,
    role TEXT,
    created_at TEXT
)
""")

# AI RESPONSE LOG TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS response_log (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enquiry_id TEXT,
    draft_text TEXT,
    approved_by TEXT,
    dispatched_at TEXT,
    dispatch_status TEXT
)
""")

conn.commit()


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_dataset(filename):

    file_path = BASE_DIR / filename

    if not file_path.exists():
        return None

    try:
        return pd.read_csv(file_path)

    except Exception:
        return None


def get_enquiries():

    cursor.execute("""
        SELECT * FROM enquiries
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    columns = [
        "enquiry_id",
        "patient_name",
        "email",
        "phone",
        "category",
        "message",
        "status",
        "remarks",
        "created_at"
    ]

    return pd.DataFrame(
        [dict(row) for row in rows],
        columns=columns
    )


def password_hash(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


def create_staff(username, password, role):

    salt = secrets.token_hex(16)

    hashed = password_hash(password, salt)

    try:

        cursor.execute("""
            INSERT INTO staff_users
            (username, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            hashed,
            salt,
            role,
            current_time()
        ))

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        return False


def check_login(username, password):

    cursor.execute("""
        SELECT * FROM staff_users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()

    if user is None:
        return None

    entered_hash = password_hash(
        password,
        user["salt"]
    )

    if hmac.compare_digest(
        entered_hash,
        user["password_hash"]
    ):

        return {
            "username": user["username"],
            "role": user["role"]
        }

    return None


def show_history(enquiry_id):

    cursor.execute("""
        SELECT old_status, new_status, remarks, updated_at
        FROM enquiry_history
        WHERE enquiry_id = ?
        ORDER BY history_id DESC
    """, (enquiry_id,))

    rows = cursor.fetchall()

    if rows:

        history_df = pd.DataFrame(
            [dict(row) for row in rows]
        )

        history_df.columns = [
            "Previous Status",
            "New Status",
            "Remarks",
            "Updated At"
        ]

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No history available.")


def search_reference(reference):

    results = []

    for filename in DATASETS:

        df = load_dataset(filename)

        if df is None:
            continue

        mask = df.astype(str).apply(
            lambda column: column.str.contains(
                reference,
                case=False,
                na=False
            )
        ).any(axis=1)

        matches = df[mask]

        if not matches.empty:
            results.append((filename, matches))

    return results


def staff_required():

    if not st.session_state.get("staff_user"):

        st.warning(
            "Please login using your staff account."
        )

        return False

    return True


# ==================================================
# SIDEBAR MENU
# ==================================================

st.sidebar.title("🏥 Main Menu")

menu = st.sidebar.selectbox(
    "Select Module",
    [
        "Home",
        "Public Enquiry Portal",
        "Track Enquiry",
        "Staff Login",
        "Admin Dashboard",
        "Dashboard & Reports",
        "Dataset Explorer",
        "AI Assistant Studio"
    ]
)

if st.session_state.get("staff_user"):

    user = st.session_state["staff_user"]

    st.sidebar.success(
        f"Logged in: {user['username']} ({user['role']})"
    )

    if st.sidebar.button("Logout"):

        st.session_state.pop("staff_user", None)

        st.rerun()


# ==================================================
# HOME
# ==================================================

if menu == "Home":

    st.title("🏥 Hospital Administration")

    st.subheader("Digital Support System")

    st.write("""
    This application helps patients submit enquiries
    and hospital staff manage and track those enquiries.
    """)

    st.success("Hospital Support System is running!")

    col1, col2, col3 = st.columns(3)

    col1.info("Patient Enquiry Management")

    col2.info("Enquiry Tracking System")

    col3.info("Hospital Reports and Datasets")

    st.subheader("Available Modules")

    st.write("""
    1. Public Enquiry Portal
    2. Enquiry Tracking
    3. Staff Login
    4. Admin Dashboard
    5. Dashboard and Reports
    6. Dataset Explorer
    7. AI Assistant Studio
    """)


# ==================================================
# PUBLIC ENQUIRY PORTAL
# ==================================================

elif menu == "Public Enquiry Portal":

    st.header("📝 Public Enquiry Portal")

    with st.form("enquiry_form"):

        name = st.text_input("Patient Name")

        email = st.text_input("Email Address")

        phone = st.text_input("Phone Number")

        category = st.selectbox(
            "Enquiry Category",
            CATEGORIES
        )

        reference_id = st.text_input(
            "Hospital Reference ID (Optional)"
        )

        message = st.text_area(
            "Enter Your Enquiry"
        )

        submit = st.form_submit_button(
            "Submit Enquiry"
        )

    if submit:

        name = name.strip()
        email = email.strip()
        phone = phone.strip()
        message = message.strip()

        valid_email = (
            "@" in email
            and "." in email.split("@")[-1]
            and " " not in email
        )

        valid_phone = (
            phone.isdigit()
            and len(phone) == 10
        )

        if not all([name, email, phone, message]):

            st.error("Please fill in all required fields.")

        elif not valid_email:

            st.error("Please enter a valid email address.")

        elif not valid_phone:

            st.error(
                "Phone number must contain exactly 10 digits."
            )

        else:

            enquiry_id = (
                "ENQ-" + uuid.uuid4().hex[:8].upper()
            )

            created_at = current_time()

            cursor.execute("""
                INSERT INTO enquiries
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enquiry_id,
                name,
                email,
                phone,
                category,
                message,
                "Pending",
                "Not reviewed yet",
                created_at
            ))

            cursor.execute("""
                INSERT INTO enquiry_history
                (enquiry_id, old_status, new_status,
                 remarks, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                enquiry_id,
                "New",
                "Pending",
                "Enquiry submitted",
                created_at
            ))

            conn.commit()

            st.success(
                "Enquiry submitted successfully!"
            )

            st.write("Your Enquiry ID:")

            st.code(enquiry_id)

            st.info(
                "Please save this ID to track your enquiry."
            )

            if reference_id.strip():

                matches = search_reference(
                    reference_id.strip()
                )

                if matches:

                    st.success(
                        "Reference ID found in dataset."
                    )

                    for filename, result in matches:

                        st.write(filename)

                        st.dataframe(
                            result,
                            use_container_width=True
                        )

                else:

                    st.warning(
                        "Reference ID was not found "
                        "in the available datasets. "
                        "Your enquiry was still saved."
                    )


# ==================================================
# TRACK ENQUIRY
# ==================================================

elif menu == "Track Enquiry":

    st.header("🔍 Track Your Enquiry")

    enquiry_id = st.text_input(
        "Enter Your Enquiry ID"
    )

    if st.button("Track Enquiry"):

        search_id = enquiry_id.strip().upper()

        if not search_id:

            st.warning("Please enter your Enquiry ID.")

        else:

            cursor.execute("""
                SELECT * FROM enquiries
                WHERE enquiry_id = ?
            """, (search_id,))

            result = cursor.fetchone()

            if result:

                st.success("Enquiry Found!")

                st.write(
                    "Patient Name:",
                    result["patient_name"]
                )

                st.write(
                    "Category:",
                    result["category"]
                )

                st.write(
                    "Enquiry:",
                    result["message"]
                )

                st.write(
                    "Status:",
                    result["status"]
                )

                st.write(
                    "Remarks:",
                    result["remarks"]
                )

                st.write(
                    "Submitted Date:",
                    result["created_at"]
                )

                st.subheader("Enquiry History")

                show_history(search_id)

            else:

                st.error(
                    "Invalid Enquiry ID. Please check again."
                )


# ==================================================
# STAFF LOGIN
# ==================================================

elif menu == "Staff Login":

    st.header("🔐 Staff Login")

    cursor.execute(
        "SELECT COUNT(*) FROM staff_users"
    )

    staff_count = cursor.fetchone()[0]

    if staff_count == 0:

        st.info(
            "First-time setup: Create your Admin account."
        )

        with st.form("first_admin_form"):

            username = st.text_input("Admin Username")

            password = st.text_input(
                "Admin Password",
                type="password"
            )

            confirm = st.text_input(
                "Confirm Password",
                type="password"
            )

            create = st.form_submit_button(
                "Create Admin Account"
            )

        if create:

            if not username.strip() or not password:

                st.error("Enter username and password.")

            elif len(password) < 8:

                st.error(
                    "Password must contain at least 8 characters."
                )

            elif password != confirm:

                st.error("Passwords do not match.")

            else:

                if create_staff(
                    username.strip(),
                    password,
                    "Admin"
                ):

                    st.success(
                        "Admin account created successfully."
                    )

                    st.info(
                        "Now login using your new account."
                    )

                else:

                    st.error("Username already exists.")

    else:

        with st.form("login_form"):

            username = st.text_input("Username")

            password = st.text_input(
                "Password",
                type="password"
            )

            login = st.form_submit_button("Login")

        if login:

            user = check_login(
                username.strip(),
                password
            )

            if user:

                st.session_state["staff_user"] = user

                st.success("Login successful!")

                st.rerun()

            else:

                st.error(
                    "Incorrect username or password."
                )


# ==================================================
# ADMIN DASHBOARD
# ==================================================

elif menu == "Admin Dashboard":

    st.header("👨‍💼 Admin Dashboard")

    if staff_required():

        df = get_enquiries()

        if df.empty:

            st.info("No enquiries available.")

        else:

            st.subheader("Search and Filter Enquiries")

            search_text = st.text_input(
                "Search Enquiry"
            )

            status_filter = st.selectbox(
                "Filter by Status",
                ["All"] + STATUSES
            )

            category_filter = st.selectbox(
                "Filter by Category",
                ["All"] + CATEGORIES
            )

            filtered_df = df.copy()

            if search_text.strip():

                mask = filtered_df.astype(str).apply(
                    lambda column: column.str.contains(
                        search_text.strip(),
                        case=False,
                        na=False
                    )
                ).any(axis=1)

                filtered_df = filtered_df[mask]

            if status_filter != "All":

                filtered_df = filtered_df[
                    filtered_df["status"] == status_filter
                ]

            if category_filter != "All":

                filtered_df = filtered_df[
                    filtered_df["category"] == category_filter
                ]

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Showing {len(filtered_df)} enquiries."
            )

            st.divider()

            st.subheader("Update Enquiry")

            selected_id = st.selectbox(
                "Select Enquiry ID",
                df["enquiry_id"].tolist()
            )

            cursor.execute("""
                SELECT * FROM enquiries
                WHERE enquiry_id = ?
            """, (selected_id,))

            selected = cursor.fetchone()

            if selected:

                st.write(
                    "Patient:",
                    selected["patient_name"]
                )

                st.write(
                    "Current Status:",
                    selected["status"]
                )

                st.write(
                    "Enquiry:",
                    selected["message"]
                )

                status_index = (
                    STATUSES.index(selected["status"])
                    if selected["status"] in STATUSES
                    else 0
                )

                new_status = st.selectbox(
                    "Update Status",
                    STATUSES,
                    index=status_index
                )

                new_remarks = st.text_area(
                    "Admin Remarks",
                    value=selected["remarks"] or ""
                )

                if st.button("Save Enquiry Update"):

                    old_status = selected["status"]

                    cursor.execute("""
                        UPDATE enquiries
                        SET status = ?, remarks = ?
                        WHERE enquiry_id = ?
                    """, (
                        new_status,
                        new_remarks.strip(),
                        selected_id
                    ))

                    if (
                        old_status != new_status
                        or (selected["remarks"] or "")
                        != new_remarks.strip()
                    ):

                        cursor.execute("""
                            INSERT INTO enquiry_history
                            (enquiry_id, old_status,
                             new_status, remarks, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            selected_id,
                            old_status,
                            new_status,
                            new_remarks.strip(),
                            current_time()
                        ))

                    conn.commit()

                    st.success(
                        "Enquiry updated successfully!"
                    )

                    st.rerun()

                st.subheader("Enquiry History")

                show_history(selected_id)

        # ADMIN CAN CREATE STAFF ACCOUNTS

        if st.session_state["staff_user"]["role"] == "Admin":

            st.divider()

            st.subheader("Create Staff Account")

            with st.form("create_staff_form"):

                staff_username = st.text_input(
                    "New Staff Username"
                )

                staff_password = st.text_input(
                    "New Staff Password",
                    type="password"
                )

                staff_role = st.selectbox(
                    "Staff Role",
                    ["Staff", "Admin"]
                )

                create_staff_button = st.form_submit_button(
                    "Create Staff Account"
                )

            if create_staff_button:

                if not staff_username.strip() or not staff_password:

                    st.error("Enter username and password.")

                elif len(staff_password) < 8:

                    st.error(
                        "Password must contain at least 8 characters."
                    )

                elif create_staff(
                    staff_username.strip(),
                    staff_password,
                    staff_role
                ):

                    st.success(
                        "Staff account created successfully."
                    )

                else:

                    st.error("Username already exists.")


# ==================================================
# DASHBOARD AND REPORTS
# ==================================================

elif menu == "Dashboard & Reports":

    st.header("📊 Dashboard & Reports")

    if staff_required():

        df = get_enquiries()

        total = len(df)

        pending = (
            int((df["status"] == "Pending").sum())
            if total else 0
        )

        under_review = (
            int((df["status"] == "Under Review").sum())
            if total else 0
        )

        resolved = (
            int((df["status"] == "Resolved").sum())
            if total else 0
        )

        rejected = (
            int((df["status"] == "Rejected").sum())
            if total else 0
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Enquiries", total)

        col2.metric("Pending", pending)

        col3.metric("Under Review", under_review)

        col4.metric("Resolved", resolved)

        col5.metric("Rejected", rejected)

        if total:

            st.subheader("Enquiries by Status")

            status_report = (
                df.groupby("status")
                .size()
                .reset_index(name="Count")
            )

            st.bar_chart(
                status_report.set_index("status")
            )

            st.subheader("Enquiries by Category")

            category_report = (
                df.groupby("category")
                .size()
                .reset_index(name="Count")
            )

            st.bar_chart(
                category_report.set_index("category")
            )

            st.subheader("Enquiry Records")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No enquiry data available for reports."
            )


# ==================================================
# DATASET EXPLORER
# ==================================================

elif menu == "Dataset Explorer":

    st.header("📂 Hospital Dataset Explorer")

    dataset = st.selectbox(
        "Select Dataset",
        DATASETS
    )

    df = load_dataset(dataset)

    if df is None:

        st.error(
            f"{dataset} not found or unable to load."
        )

        st.info(
            "Keep the CSV files in the same folder as app.py."
        )

    else:

        st.success("Dataset loaded successfully!")

        col1, col2 = st.columns(2)

        col1.metric("Number of Rows", len(df))

        col2.metric("Number of Columns", len(df.columns))

        st.subheader("Search Within Dataset")

        search_text = st.text_input(
            "Enter search value"
        )

        filtered_df = df.copy()

        if search_text.strip():

            mask = filtered_df.astype(str).apply(
                lambda column: column.str.contains(
                    search_text.strip(),
                    case=False,
                    na=False
                )
            ).any(axis=1)

            filtered_df = filtered_df[mask]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("Search Across All Datasets")

    global_search = st.text_input(
        "Search all hospital CSV files"
    )

    if st.button("Search All Datasets"):

        if not global_search.strip():

            st.warning("Please enter a search value.")

        else:

            found = False

            for filename in DATASETS:

                search_df = load_dataset(filename)

                if search_df is None:
                    continue

                mask = search_df.astype(str).apply(
                    lambda column: column.str.contains(
                        global_search.strip(),
                        case=False,
                        na=False
                    )
                ).any(axis=1)

                matches = search_df[mask]

                if not matches.empty:

                    found = True

                    st.write(f"Matches in {filename}")

                    st.dataframe(
                        matches,
                        use_container_width=True
                    )

            if not found:

                st.info("No matching records found.")


# ==================================================
# AI ASSISTANT STUDIO
# ==================================================

elif menu == "AI Assistant Studio":

    st.header("🤖 AI Assistant Studio")

    if staff_required():

        df = get_enquiries()

        if df.empty:

            st.info(
                "No enquiries available. Submit an enquiry first."
            )

        else:

            selected_id = st.selectbox(
                "Select Enquiry",
                df["enquiry_id"].tolist()
            )

            cursor.execute("""
                SELECT * FROM enquiries
                WHERE enquiry_id = ?
            """, (selected_id,))

            record = cursor.fetchone()

            st.write(
                "Patient Name:",
                record["patient_name"]
            )

            st.write(
                "Enquiry Category:",
                record["category"]
            )

            st.write(
                "Current Status:",
                record["status"]
            )

            st.write(
                "Enquiry Message:",
                record["message"]
            )

            draft_type = st.selectbox(
                "Select Draft Type",
                ["Acknowledgement", "Status Update"]
            )

            if st.button("Generate Reply"):

                if draft_type == "Acknowledgement":

                    draft = (
                        f"Dear {record['patient_name']},\n\n"
                        "Thank you for contacting our hospital. "
                        "Your enquiry has been received successfully. "
                        "Our staff will review it and update you soon.\n\n"
                        "Regards,\nHospital Support Team"
                    )

                else:

                    draft = (
                        f"Dear {record['patient_name']},\n\n"
                        f"This is an update regarding your enquiry "
                        f"{record['enquiry_id']}. "
                        f"Current status: {record['status']}. "
                        f"Remarks: {record['remarks']}.\n\n"
                        "Regards,\nHospital Support Team"
                    )

                st.session_state["draft"] = draft

                st.session_state["draft_enquiry"] = selected_id

            if (
                st.session_state.get("draft_enquiry")
                == selected_id
                and st.session_state.get("draft")
            ):

                st.subheader("Review Suggested Reply")

                edited_draft = st.text_area(
                    "Edit Draft Before Approval",
                    value=st.session_state["draft"],
                    height=200,
                    key=f"draft_{selected_id}"
                )

                approved = st.checkbox(
                    "I have reviewed and approved this draft."
                )

                if st.button("Record Approved Draft"):

                    if not approved:

                        st.warning(
                            "Please approve the draft after reviewing."
                        )

                    elif not edited_draft.strip():

                        st.warning("Draft cannot be empty.")

                    else:

                        cursor.execute("""
                            INSERT INTO response_log
                            (enquiry_id, draft_text, approved_by,
                             dispatched_at, dispatch_status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            selected_id,
                            edited_draft.strip(),
                            st.session_state["staff_user"]["username"],
                            current_time(),
                            "Approved - Simulated Dispatch Only"
                        ))

                        conn.commit()

                        st.success(
                            "Approved draft recorded successfully. "
                            "No email was actually sent."
                        )

        st.info(
            "This prototype uses prepared message templates. "
            "It does not connect to a live Generative AI API or send "
            "real emails. Hospital staff must review every draft."
        )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Hospital Administration Digital Support System | "
    "Academic Prototype | Sample data only"
)

st.caption(
    "This system is not intended for diagnosis, treatment "
    "or emergency medical decisions."
)