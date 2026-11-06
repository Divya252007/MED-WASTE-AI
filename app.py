import streamlit as st

from auth import login_user, admin_exists, create_first_admin
from database import get_connection

from user_management import user_management_page
from hospital_management import hospital_management_page
from waste_management import waste_management_page
from qr_scanner import qr_scanner_page

from admin_portal import admin_portal_page
from doctor_portal import doctor_portal_page
from nurse_portal import nurse_portal_page
from driver_portal import driver_portal_page

from collection_management import collection_management_page
from reports_analystics import reports_analytics_page
from notification import notification_page
from location_tracking import location_tracking_page
from chatbot import chatbot_page


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="MED WASTE AI | Smart Healthcare",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# SESSION STATE
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "theme" not in st.session_state:
    st.session_state.theme = "Dark Green"

if "theme_selector" not in st.session_state:
    st.session_state.theme_selector = st.session_state.theme

if st.session_state.theme not in ["Dark Green", "Dark Blue"]:
    st.session_state.theme = "Dark Green"
    st.session_state.theme_selector = "Dark Green"

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Dashboard Overview"


# =====================================================
# THEME COLOUR PALETTES
# =====================================================

THEMES = {
    "Dark Green": {
        "background": "#102D23",
        "surface": "#183D30",
        "surface_alt": "#1D4837",
        "sidebar": "#0B241C",
        "primary": "#42B883",
        "primary_hover": "#319B6D",
        "text": "#EAF5EE",
        "muted": "#A8C7B4",
        "border": "#315B46",
        "input": "#143629",
        "accent": "#75D6A5",
        "soft": "#204B38",
        "button_text": "#08251A"
    },

    "Dark Blue": {
        "background": "#101F3D",
        "surface": "#192D50",
        "surface_alt": "#203A62",
        "sidebar": "#0A1730",
        "primary": "#60A5FA",
        "primary_hover": "#3B82F6",
        "text": "#EDF4FF",
        "muted": "#AFC5E8",
        "border": "#30496F",
        "input": "#142644",
        "accent": "#93C5FD",
        "soft": "#233F67",
        "button_text": "#0A1C36"
    }
}


# =====================================================
# GLOBAL THEME
# =====================================================

def apply_theme():

    colors = THEMES.get(
        st.session_state.theme,
        THEMES["Dark Green"]
    )

    st.markdown(
        f"""
        <style>

        :root {{
            --app-bg: {colors["background"]};
            --surface: {colors["surface"]};
            --surface-alt: {colors["surface_alt"]};
            --sidebar-bg: {colors["sidebar"]};
            --primary: {colors["primary"]};
            --primary-hover: {colors["primary_hover"]};
            --text: {colors["text"]};
            --muted: {colors["muted"]};
            --border: {colors["border"]};
            --input-bg: {colors["input"]};
            --accent: {colors["accent"]};
            --soft: {colors["soft"]};
            --button-text: {colors["button_text"]};
        }}

        /* GLOBAL BACKGROUND */

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: var(--app-bg) !important;
            color: var(--text);
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
            position: relative;
            z-index: 1;
        }}

        /* MEDICAL DECORATIONS */

        .medical-decoration-layer {{
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            pointer-events: none;
            z-index: 0;
        }}

        .medical-icon {{
            position: absolute;
            opacity: 0.075;
            filter: blur(3px);
            user-select: none;
            line-height: 1;
            pointer-events: none;
        }}

        .medical-icon.i1 {{
            top: 8%;
            left: 19%;
            font-size: 85px;
            transform: rotate(-18deg);
        }}

        .medical-icon.i2 {{
            top: 25%;
            right: 7%;
            font-size: 105px;
            transform: rotate(15deg);
        }}

        .medical-icon.i3 {{
            top: 58%;
            left: 8%;
            font-size: 95px;
            transform: rotate(12deg);
        }}

        .medical-icon.i4 {{
            bottom: 8%;
            right: 16%;
            font-size: 100px;
            transform: rotate(-15deg);
        }}

        .medical-icon.i5 {{
            top: 75%;
            left: 48%;
            font-size: 65px;
            filter: blur(4px);
        }}

        .medical-icon.i6 {{
            top: 12%;
            right: 38%;
            font-size: 60px;
        }}

        .medical-icon.i7 {{
            bottom: 25%;
            right: 43%;
            font-size: 75px;
        }}

        .medical-icon.i8 {{
            top: 43%;
            left: 36%;
            font-size: 55px;
            filter: blur(4px);
        }}

        /* SIDEBAR */

        [data-testid="stSidebar"] {{
            background: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border);
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background: var(--sidebar-bg);
            padding-top: 1.5rem;
        }}

        [data-testid="stSidebar"] * {{
            color: var(--text);
        }}

        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            padding: 10px 12px;
            border-radius: 9px;
            margin-bottom: 5px;
        }}

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background: var(--surface);
        }}

        /* HEADINGS AND TEXT */

        h1, h2, h3, h4, h5, h6 {{
            color: var(--text) !important;
            font-weight: 700 !important;
        }}

        p, label, li {{
            color: var(--text);
        }}

        [data-testid="stCaptionContainer"] {{
            color: var(--muted);
        }}

        /* METRIC CARDS */

        [data-testid="stMetric"] {{
            background: var(--surface) !important;
            border: 1px solid var(--border);
            border-radius: 15px;
            padding: 18px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.12);
        }}

        [data-testid="stMetricLabel"] {{
            color: var(--muted) !important;
        }}

        [data-testid="stMetricValue"] {{
            color: var(--accent) !important;
            font-weight: 750;
        }}

        [data-testid="stMetricDelta"] {{
            color: var(--muted) !important;
        }}

        /* BUTTONS */

        .stButton > button,
        .stDownloadButton > button {{
            background: var(--primary) !important;
            color: var(--button-text) !important;
            border: 1px solid var(--primary) !important;
            border-radius: 9px;
            min-height: 40px;
            font-weight: 700;
            transition: all 0.2s ease;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: var(--primary-hover) !important;
            color: white !important;
            border-color: var(--primary-hover) !important;
        }}

        .stButton > button:focus,
        .stDownloadButton > button:focus {{
            box-shadow: 0 0 0 2px var(--accent);
        }}

        /* INPUT FIELDS */

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input {{
            background: var(--input-bg) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 9px;
        }}

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: var(--muted) !important;
        }}

        .stSelectbox div[data-baseweb="select"] > div {{
            background: var(--input-bg);
            border-radius: 9px;
            border-color: var(--border);
            color: var(--text);
        }}

        [data-testid="stDateInput"] input {{
            background: var(--input-bg);
            color: var(--text);
        }}

        [data-testid="stFileUploader"] {{
            background: var(--surface);
            border: 1px dashed var(--primary);
            border-radius: 12px;
            padding: 10px;
        }}

        [data-testid="stFileUploader"] * {{
            color: var(--text);
        }}

        /* TABS */

        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            border-bottom: 1px solid var(--border);
        }}

        .stTabs [data-baseweb="tab"] {{
            padding: 12px 16px;
            font-weight: 600;
            color: var(--muted);
        }}

        .stTabs [aria-selected="true"] {{
            color: var(--accent) !important;
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: var(--primary);
        }}

        /* TABLES */

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: var(--surface);
        }}

        /* EXPANDERS */

        [data-testid="stExpander"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
        }}

        [data-testid="stExpander"] summary {{
            color: var(--text);
        }}

        [data-testid="stExpander"] summary:hover {{
            color: var(--accent);
        }}

        /* ALERTS AND CONTAINERS */

        [data-testid="stAlert"] {{
            border-radius: 10px;
        }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--border) !important;
            border-radius: 12px;
        }}

        /* BRAND */

        .brand-header {{
            padding: 15px 5px 20px 5px;
        }}

        .brand-name {{
            font-size: 24px;
            font-weight: 800;
            color: var(--accent);
            letter-spacing: -0.7px;
        }}

        .brand-subtitle {{
            color: var(--muted);
            font-size: 11px;
            letter-spacing: 1.3px;
            font-weight: 600;
            margin-top: 4px;
        }}

        /* MAIN PORTAL HEADER */

        .portal-header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 5px solid var(--primary);
            border-radius: 16px;
            padding: 22px 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 18px rgba(0,0,0,0.12);
        }}

        .portal-label {{
            color: var(--accent);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }}

        .portal-title {{
            color: var(--text);
            font-size: 27px;
            font-weight: 750;
            margin-top: 7px;
        }}

        .portal-description {{
            color: var(--muted);
            font-size: 14px;
            margin-top: 5px;
        }}

        .login-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.20);
            backdrop-filter: blur(12px);
        }}

        .login-brand {{
            color: var(--accent);
            font-size: 35px;
            font-weight: 800;
            text-align: center;
            letter-spacing: -1px;
        }}

        .login-description {{
            color: var(--muted);
            text-align: center;
            font-size: 14px;
            margin-bottom: 20px;
        }}

        .user-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 4px solid var(--primary);
            border-radius: 12px;
            padding: 13px;
            margin-top: 12px;
        }}

        /* CHECKBOX AND RADIO */

        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {{
            color: var(--text);
        }}

        /* DIVIDERS */

        hr {{
            border-color: var(--border) !important;
        }}

        ::selection {{
            background: var(--primary);
            color: var(--button-text);
        }}

        /* RESPONSIVE */

        @media(max-width: 768px) {{

            .block-container {{
                padding: 1rem 1rem 2rem 1rem;
            }}

            .portal-title {{
                font-size: 22px;
            }}

            .login-brand {{
                font-size: 27px;
            }}

            .portal-header {{
                padding: 18px;
            }}

            .medical-icon {{
                font-size: 45px !important;
                opacity: 0.045;
            }}
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

    # MEDICAL EMOJI DECORATIONS
    st.markdown(
        """
        <div class="medical-decoration-layer">
            <span class="medical-icon i1">🩺</span>
            <span class="medical-icon i2">💉</span>
            <span class="medical-icon i3">🧪</span>
            <span class="medical-icon i4">🏥</span>
            <span class="medical-icon i5">🧬</span>
            <span class="medical-icon i6">🧤</span>
            <span class="medical-icon i7">♻️</span>
            <span class="medical-icon i8">🩹</span>
        </div>
        """,
        unsafe_allow_html=True
    )


# APPLY THEME
apply_theme()


# =====================================================
# FIRST ADMIN SETUP
# =====================================================

def first_time_admin_setup():

    st.subheader("Create Your Administrator Account")

    st.caption(
        "Set up the first administrator to access MED WASTE AI."
    )

    with st.container(border=True):

        full_name = st.text_input(
            "Full Name",
            key="setup_full_name"
        )

        username = st.text_input(
            "Username",
            key="setup_username"
        )

        phone = st.text_input(
            "Phone Number (Optional)",
            key="setup_phone"
        )

        password = st.text_input(
            "Create Password",
            type="password",
            key="setup_password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="setup_confirm"
        )

        if st.button(
            "Create Admin Account",
            use_container_width=True
        ):

            if (
                not full_name.strip()
                or not username.strip()
                or not password
            ):
                st.error("Please fill in all required fields.")

            elif password != confirm:
                st.error("Passwords do not match.")

            else:

                success, message = create_first_admin(
                    full_name,
                    username,
                    password,
                    phone
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# =====================================================
# LOGIN PAGE
# =====================================================

def login_page():

    left, center, right = st.columns([1, 1.25, 1])

    with center:

        st.write("")

        st.markdown(
            """
            <div class="login-card">
                <div class="login-brand">✚ MED WASTE AI</div>
                <div class="login-description">
                    SMART BIOMEDICAL WASTE MANAGEMENT PLATFORM
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        if not admin_exists():

            with st.container(border=True):
                first_time_admin_setup()

            st.divider()

        with st.container(border=True):

            st.subheader("Welcome Back")

            st.caption(
                "Sign in to access your healthcare portal."
            )

            username = st.text_input(
                "Username",
                key="login_username"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button(
                "Sign In",
                use_container_width=True,
                type="primary"
            ):

                if not username.strip() or not password:
                    st.warning(
                        "Please enter username and password."
                    )

                else:

                    user = login_user(
                        username.strip(),
                        password
                    )

                    if user:

                        st.session_state.user = user
                        st.session_state.selected_page = (
                            "Dashboard Overview"
                        )

                        st.rerun()

                    else:
                        st.error(
                            "Invalid username or password."
                        )

        st.write("")

        st.markdown(
            """
            <p style="text-align:center;color:var(--muted);font-size:12px;">
                Secure Healthcare Waste Management
                <br>
                MED WASTE AI © 2026
            </p>
            """,
            unsafe_allow_html=True
        )


# =====================================================
# ROLE CONFIGURATION
# =====================================================

PORTAL_DETAILS = {

    "admin": {
        "title": "Administrator Portal",
        "description": "Manage hospitals, users and system operations.",
        "icon": "🛡️"
    },

    "doctor": {
        "title": "Doctor Portal",
        "description": "Review biomedical waste and verify AI suggestions.",
        "icon": "🩺"
    },

    "staff": {
        "title": "Nurse / Healthcare Staff Portal",
        "description": "Register waste records and manage collection requests.",
        "icon": "🧑‍⚕️"
    },

    "driver": {
        "title": "Driver Portal",
        "description": "Manage assigned collections and transportation.",
        "icon": "🚚"
    }
}


# =====================================================
# ROLE-BASED NAVIGATION
# =====================================================

def get_menu_items(role):

    if role == "admin":

        return [
            "Dashboard Overview",
            "User Management",
            "Hospital Management",
            "Waste Records",
            "QR Scanner",
            "Collection Management",
            "Notifications",
            "Activity Logs",
            "Reports & Analytics"
        ]

    elif role == "doctor":

        return [
            "Dashboard Overview",
            "Waste Records",
            "AI Waste Assistant",
            "QR Scanner",
            "Notifications"
        ]

    elif role == "staff":

        return [
            "Dashboard Overview",
            "Waste Records",
            "AI Waste Assistant",
            "Collection Management",
            "QR Scanner",
            "Notifications"
        ]

    elif role == "driver":

        return [
            "Dashboard Overview",
            "Transportation Tracking",
            "Location Tracking",
            "QR Scanner",
            "Notifications"
        ]

    return []


# =====================================================
# DASHBOARD PAGE
# =====================================================

def dashboard_page():

    user = st.session_state.user
    role = user["role"]

    current_portal = PORTAL_DETAILS.get(role)

    if current_portal is None:
        st.error("Your account has an invalid role.")
        return

    menu_items = get_menu_items(role)

    if not menu_items:
        st.error("No navigation options are available.")
        return

    if st.session_state.selected_page not in menu_items:
        st.session_state.selected_page = "Dashboard Overview"

    # =================================================
    # SIDEBAR
    # =================================================

    with st.sidebar:

        st.markdown(
            """
            <div class="brand-header">
                <div class="brand-name">✚ MED WASTE AI</div>
                <div class="brand-subtitle">
                    SMART HEALTHCARE PLATFORM
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()
        st.caption("MAIN MENU")

        selected_page = st.radio(
            "Navigation",
            menu_items,
            key="main_navigation",
            label_visibility="collapsed"
        )

        st.session_state.selected_page = selected_page

        st.divider()
        st.caption("APPEARANCE")

        selected_theme = st.selectbox(
            "Choose Theme",
            ["Dark Green", "Dark Blue"],
            key="theme_selector"
        )

        if selected_theme != st.session_state.theme:
            st.session_state.theme = selected_theme
            st.rerun()

        st.divider()
        st.caption("SIGNED IN AS")

        st.markdown(
            f"""
            <div class="user-card">
                <strong>
                    {current_portal["icon"]} {user["full_name"]}
                </strong>
                <br>
                <span style="color:var(--muted);font-size:12px;">
                    {role.upper()}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        if st.button(
            "↪ Logout",
            use_container_width=True
        ):

            st.session_state.user = None
            st.session_state.selected_page = "Dashboard Overview"

            st.rerun()

    # =================================================
    # MAIN HEADER
    # =================================================

    header_html = f"""
    <div class="portal-header">
        <div class="portal-label">MED WASTE AI / {role.upper()}</div>
        <div class="portal-title">{current_portal["icon"]} {current_portal["title"]}</div>
        <div class="portal-description">{current_portal["description"]}</div>
    </div>
    """

    st.markdown(
        header_html,
        unsafe_allow_html=True
    )

    # =================================================
    # PAGE ROUTING
    # =================================================

    if selected_page == "Dashboard Overview":

        if role == "admin":
            admin_portal_page(user)

        elif role == "doctor":
            doctor_portal_page(user)

        elif role == "staff":
            nurse_portal_page(user)

        elif role == "driver":
            driver_portal_page(user)

    elif selected_page == "User Management" and role == "admin":

        user_management_page()

    elif selected_page == "Hospital Management" and role == "admin":

        hospital_management_page()

    elif selected_page == "Waste Records" and role in [
        "admin", "doctor", "staff"
    ]:

        waste_management_page(user)

    elif selected_page == "AI Waste Assistant" and role in [
        "doctor", "staff"
    ]:

        chatbot_page(user)

    elif selected_page == "QR Scanner":

        qr_scanner_page(user)

    elif selected_page == "Collection Management" and role in [
        "admin", "staff"
    ]:

        collection_management_page(user)

    elif selected_page == "Transportation Tracking" and role == "driver":

        driver_portal_page(user)

    elif selected_page == "Location Tracking" and role == "driver":

        location_tracking_page()

    elif selected_page == "Activity Logs" and role == "admin":

        st.subheader("System Activity Logs")

        conn = get_connection()

        try:

            logs = conn.execute(
                """
                SELECT
                    a.log_id,
                    u.full_name,
                    a.action,
                    a.details,
                    a.created_at
                FROM activity_logs a
                LEFT JOIN users u
                    ON a.user_id = u.user_id
                ORDER BY a.log_id DESC
                LIMIT 100
                """
            ).fetchall()

        finally:
            conn.close()

        if logs:

            st.dataframe(
                [dict(row) for row in logs],
                width="stretch",
                hide_index=True
            )

        else:
            st.info("No activity logs available.")

    elif selected_page == "Reports & Analytics" and role == "admin":

        reports_analytics_page(user)

    elif selected_page == "Notifications":

        notification_page(user)


# =====================================================
# APPLICATION CONTROL
# =====================================================

if st.session_state.user is None:

    login_page()

else:

    dashboard_page()