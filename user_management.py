import streamlit as st
from database import get_connection
from auth import create_user


def log_activity(user_id, action, details):

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT INTO activity_logs (user_id, action, details)
            VALUES (?, ?, ?)
            """,
            (user_id, action, details)
        )

        conn.commit()

    finally:

        conn.close()


def user_management_page(current_user=None):

    # =========================================
    # HEALTHCARE UI STYLING
    # =========================================

    st.markdown("""
    <style>
    .user-header {
        background: linear-gradient(120deg, #087f8c, #13a89e);
        padding: 26px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }

    .user-header h2 {
        color: white;
        font-size: 27px;
        margin: 0;
    }

    .user-header p {
        color: #e7ffff;
        margin-top: 8px;
        margin-bottom: 0;
    }

    div[data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px;
        padding: 15px;
    }

    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.2);
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
        min-height: 42px;
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================================
    # HEADER
    # =========================================

    st.markdown("""
    <div class="user-header">
        <h2>👥 User Management</h2>
        <p>Create accounts, assign hospital roles and manage
        system user access.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs([
        "➕ Add New User",
        "👥 View Users"
    ])

    # =========================================
    # ADD NEW USER
    # =========================================

    with tab1:

        st.subheader("Register New User")

        st.caption(
            "Create a user account and assign the appropriate role "
            "and hospital."
        )

        # Fetch hospitals
        conn = get_connection()

        try:

            hospitals = conn.execute(
                """
                SELECT hospital_id, hospital_name
                FROM hospitals
                ORDER BY hospital_name
                """
            ).fetchall()

        finally:

            conn.close()

        hospital_options = {
            hospital["hospital_name"]: hospital["hospital_id"]
            for hospital in hospitals
        }

        role_options = {
            "Doctor": "doctor",
            "Nurse": "staff",
            "Driver": "driver"
        }

        with st.form("register_user_form"):

            st.markdown("#### 👤 Personal Information")

            col1, col2 = st.columns(2)

            with col1:

                full_name = st.text_input(
                    "Full Name *",
                    placeholder="Enter full name"
                )

                username = st.text_input(
                    "Username *",
                    placeholder="Choose a username"
                )

            with col2:

                phone = st.text_input(
                    "Phone Number",
                    placeholder="Enter phone number"
                )

                location = st.text_input(
                    "Location *",
                    placeholder="Enter city or area"
                )

            st.divider()

            st.markdown("#### 🔐 Account Information")

            password = st.text_input(
                "Temporary Password *",
                type="password",
                placeholder="Minimum 8 characters"
            )

            st.divider()

            st.markdown("#### 🏥 Role and Hospital Assignment")

            col3, col4 = st.columns(2)

            with col3:

                selected_role = st.selectbox(
                    "Select Role",
                    list(role_options.keys())
                )

            with col4:

                if hospital_options:

                    hospital_name = st.selectbox(
                        "Select Hospital",
                        list(hospital_options.keys())
                    )

                    hospital_id = hospital_options[hospital_name]

                else:

                    hospital_id = None

                    st.warning(
                        "Please register a hospital first."
                    )

            st.caption("* Required fields")

            submitted = st.form_submit_button(
                "Create User Account",
                type="primary",
                use_container_width=True
            )

        # =====================================
        # VALIDATION AND USER CREATION
        # =====================================

        if submitted:

            if not all([
                full_name.strip(),
                username.strip(),
                password.strip(),
                location.strip()
            ]):

                st.error(
                    "Please fill all required fields."
                )

            elif len(password) < 8:

                st.error(
                    "Password must contain at least 8 characters."
                )

            elif hospital_id is None:

                st.error(
                    "A hospital must be registered first."
                )

            else:

                role = role_options[selected_role]

                success, message = create_user(
                    full_name=full_name.strip(),
                    username=username.strip(),
                    password=password,
                    role=role,
                    hospital_id=hospital_id,
                    phone=phone.strip(),
                    location=location.strip()
                )

                if success:

                    try:

                        if current_user:

                            log_activity(
                                current_user["user_id"],
                                "User Created",
                                (
                                    f"Created {role} account: "
                                    f"{username.strip()}"
                                )
                            )

                        st.success(message)

                        st.rerun()

                    except Exception as error:

                        st.warning(
                            "User created, but activity logging failed: "
                            + str(error)
                        )

                else:

                    st.error(message)

    # =========================================
    # VIEW USERS
    # =========================================

    with tab2:

        st.subheader("Registered System Users")

        st.caption(
            "View user information, hospital assignments "
            "and account status."
        )

        conn = get_connection()

        try:

            users = conn.execute(
                """
                SELECT
                    users.user_id,
                    users.full_name,
                    users.username,
                    users.role,
                    users.phone,
                    users.location,
                    users.is_active,
                    users.hospital_id,
                    hospitals.hospital_name
                FROM users
                LEFT JOIN hospitals
                    ON users.hospital_id = hospitals.hospital_id
                ORDER BY users.user_id DESC
                """
            ).fetchall()

        finally:

            conn.close()

        if users:

            # =================================
            # DASHBOARD METRICS
            # =================================

            total_users = len(users)

            active_users = sum(
                1 for u in users if u["is_active"]
            )

            inactive_users = sum(
                1 for u in users if not u["is_active"]
            )

            doctor_count = sum(
                1 for u in users if u["role"] == "doctor"
            )

            nurse_count = sum(
                1 for u in users if u["role"] == "staff"
            )

            driver_count = sum(
                1 for u in users if u["role"] == "driver"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Users", total_users)
            col2.metric("Active Users", active_users)
            col3.metric("Inactive Users", inactive_users)

            col4, col5, col6 = st.columns(3)

            col4.metric("Doctors", doctor_count)
            col5.metric("Nurses", nurse_count)
            col6.metric("Drivers", driver_count)

            st.divider()

            # =================================
            # SEARCH AND FILTER
            # =================================

            st.markdown("#### 🔎 Search and Filter")

            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:

                search_query = st.text_input(
                    "Search User",
                    placeholder="Search by name or username..."
                )

            with filter_col2:

                role_filter = st.selectbox(
                    "Filter by Role",
                    [
                        "All Roles",
                        "Admin",
                        "Doctor",
                        "Nurse",
                        "Driver"
                    ]
                )

            status_filter = st.selectbox(
                "Filter by Account Status",
                [
                    "All Users",
                    "Active",
                    "Inactive"
                ]
            )

            # =================================
            # APPLY FILTERS
            # =================================

            filtered_users = users

            if search_query.strip():

                search_value = search_query.strip().lower()

                filtered_users = [
                    u for u in filtered_users
                    if search_value in (
                        u["full_name"] or ""
                    ).lower()
                    or search_value in (
                        u["username"] or ""
                    ).lower()
                ]

            role_mapping = {
                "Admin": "admin",
                "Doctor": "doctor",
                "Nurse": "staff",
                "Driver": "driver"
            }

            if role_filter != "All Roles":

                selected_role = role_mapping[role_filter]

                filtered_users = [
                    u for u in filtered_users
                    if u["role"] == selected_role
                ]

            if status_filter == "Active":

                filtered_users = [
                    u for u in filtered_users
                    if u["is_active"]
                ]

            elif status_filter == "Inactive":

                filtered_users = [
                    u for u in filtered_users
                    if not u["is_active"]
                ]

            st.write(
                f"Showing {len(filtered_users)} user(s)"
            )

            st.divider()

            # =================================
            # DISPLAY USERS
            # =================================

            if filtered_users:

                for user in filtered_users:

                    with st.expander(
                        f"👤 {user['full_name']} "
                        f"— {user['role'].upper()}"
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown("**User ID**")
                            st.write(user["user_id"])

                            st.markdown("**Username**")
                            st.write(user["username"])

                            st.markdown("**Phone Number**")
                            st.write(
                                user["phone"] or "Not available"
                            )

                        with col2:

                            st.markdown("**Role**")
                            st.write(user["role"].upper())

                            st.markdown("**Location**")
                            st.write(
                                user["location"] or "Not available"
                            )

                            st.markdown("**Hospital**")
                            st.write(
                                user["hospital_name"] or "Not assigned"
                            )

                        st.divider()

                        if user["is_active"]:

                            st.success("Account Status: Active")

                        else:

                            st.warning("Account Status: Inactive")

                        # Admin protection
                        if user["role"] == "admin":

                            st.info(
                                "Admin accounts cannot be changed here."
                            )

                            continue

                        # Prevent self-deactivation
                        if (
                            current_user
                            and user["user_id"] == current_user["user_id"]
                        ):

                            st.info(
                                "You cannot deactivate your own account."
                            )

                            continue

                        # =================================
                        # DEACTIVATE USER
                        # =================================

                        if user["is_active"]:

                            if st.button(
                                "Deactivate User",
                                key=f"deactivate_{user['user_id']}",
                                type="secondary"
                            ):

                                conn = get_connection()

                                try:

                                    cursor = conn.execute(
                                        """
                                        UPDATE users
                                        SET is_active = 0
                                        WHERE user_id = ?
                                        AND role != 'admin'
                                        AND is_active = 1
                                        """,
                                        (user["user_id"],)
                                    )

                                    conn.commit()

                                    if cursor.rowcount == 0:

                                        st.warning(
                                            "User status was already changed."
                                        )

                                    else:

                                        if current_user:

                                            log_activity(
                                                current_user["user_id"],
                                                "User Deactivated",
                                                (
                                                    "Deactivated account: "
                                                    f"{user['username']}"
                                                )
                                            )

                                        st.success(
                                            "User deactivated successfully."
                                        )

                                except Exception as error:

                                    conn.rollback()

                                    st.error(
                                        f"Unable to deactivate user: {error}"
                                    )

                                finally:

                                    conn.close()

                                st.rerun()

                        # =================================
                        # ACTIVATE USER
                        # =================================

                        else:

                            if st.button(
                                "Activate User",
                                key=f"activate_{user['user_id']}",
                                type="primary"
                            ):

                                conn = get_connection()

                                try:

                                    cursor = conn.execute(
                                        """
                                        UPDATE users
                                        SET is_active = 1
                                        WHERE user_id = ?
                                        AND role != 'admin'
                                        AND is_active = 0
                                        """,
                                        (user["user_id"],)
                                    )

                                    conn.commit()

                                    if cursor.rowcount == 0:

                                        st.warning(
                                            "User status was already changed."
                                        )

                                    else:

                                        if current_user:

                                            log_activity(
                                                current_user["user_id"],
                                                "User Activated",
                                                (
                                                    "Activated account: "
                                                    f"{user['username']}"
                                                )
                                            )

                                        st.success(
                                            "User activated successfully."
                                        )

                                except Exception as error:

                                    conn.rollback()

                                    st.error(
                                        f"Unable to activate user: {error}"
                                    )

                                finally:

                                    conn.close()

                                st.rerun()

            else:

                st.info(
                    "No users match the selected search and filters."
                )

        else:

            st.info(
                "No users registered yet."
            )

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Smart Biomedical Waste Management System"
    )