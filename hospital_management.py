import streamlit as st
from database import get_connection


def hospital_management_page():

    # =========================================
    # HEALTHCARE UI STYLING
    # =========================================

    st.markdown("""
    <style>
    .hospital-header {
        background: linear-gradient(120deg, #087f8c, #13a89e);
        padding: 26px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }

    .hospital-header h2 {
        color: white;
        font-size: 27px;
        margin: 0;
    }

    .hospital-header p {
        color: #e7ffff;
        margin-top: 8px;
        margin-bottom: 0;
    }

    .hospital-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-left: 4px solid #0d9488;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
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
    <div class="hospital-header">
        <h2>🏥 Hospital Management</h2>
        <p>Register, organize and manage hospitals
        in the MED WASTE AI system.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs([
        "➕ Add Hospital",
        "🏥 View Hospitals"
    ])

    # =========================================
    # ADD HOSPITAL
    # =========================================

    with tab1:

        st.subheader("Register New Hospital")

        st.caption(
            "Enter the hospital details to register it in the system."
        )

        with st.form("add_hospital_form"):

            col1, col2 = st.columns(2)

            with col1:

                name = st.text_input(
                    "Hospital Name *",
                    placeholder="Enter hospital name"
                )

                city = st.text_input(
                    "City",
                    placeholder="Enter city"
                )

            with col2:

                phone = st.text_input(
                    "Contact Number",
                    placeholder="Enter contact number"
                )

            address = st.text_area(
                "Hospital Address",
                placeholder="Enter complete hospital address"
            )

            st.caption("* Required field")

            submitted = st.form_submit_button(
                "Register Hospital",
                use_container_width=True
            )

        if submitted:

            if not name.strip():

                st.error("Hospital name is required.")

            else:

                conn = get_connection()

                try:

                    conn.execute(
                        """
                        INSERT INTO hospitals
                        (hospital_name, address, city, phone)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            name.strip(),
                            address.strip(),
                            city.strip(),
                            phone.strip()
                        )
                    )

                    conn.commit()

                    st.success(
                        "Hospital registered successfully!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Unable to register hospital: {e}"
                    )

                finally:

                    conn.close()

    # =========================================
    # VIEW HOSPITALS
    # =========================================

    with tab2:

        st.subheader("Registered Hospitals")

        st.caption(
            "View and search hospitals registered in the system."
        )

        conn = get_connection()

        try:

            hospitals = conn.execute(
                """
                SELECT *
                FROM hospitals
                ORDER BY hospital_id DESC
                """
            ).fetchall()

        finally:

            conn.close()

        if hospitals:

            # =================================
            # SUMMARY METRICS
            # =================================

            total_hospitals = len(hospitals)

            cities = {
                hospital["city"].strip().lower()
                for hospital in hospitals
                if hospital["city"] and hospital["city"].strip()
            }

            col1, col2 = st.columns(2)

            col1.metric(
                "Total Hospitals",
                total_hospitals
            )

            col2.metric(
                "Cities Covered",
                len(cities)
            )

            st.divider()

            # =================================
            # SEARCH
            # =================================

            search_query = st.text_input(
                "🔎 Search Hospital",
                placeholder="Search by hospital name or city..."
            )

            filtered_hospitals = hospitals

            if search_query.strip():

                search_value = search_query.strip().lower()

                filtered_hospitals = [
                    hospital for hospital in hospitals
                    if search_value in (
                        hospital["hospital_name"] or ""
                    ).lower()
                    or search_value in (
                        hospital["city"] or ""
                    ).lower()
                ]

            st.write(
                f"Showing {len(filtered_hospitals)} hospital(s)"
            )

            # =================================
            # HOSPITAL DETAILS
            # =================================

            if filtered_hospitals:

                for hospital in filtered_hospitals:

                    hospital_name = (
                        hospital["hospital_name"]
                        or "Unnamed Hospital"
                    )

                    with st.expander(
                        f"🏥 {hospital_name} "
                        f"— ID: {hospital['hospital_id']}"
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown("**Hospital ID**")

                            st.write(
                                hospital["hospital_id"]
                            )

                            st.markdown("**City**")

                            st.write(
                                hospital["city"] or "Not provided"
                            )

                        with col2:

                            st.markdown("**Contact Number**")

                            st.write(
                                hospital["phone"] or "Not provided"
                            )

                        st.markdown("**Hospital Address**")

                        st.write(
                            hospital["address"] or "Not provided"
                        )

            else:

                st.info(
                    "No hospitals match your search."
                )

        else:

            st.info(
                "No hospitals registered yet. "
                "Use the Add Hospital tab to register one."
            )

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Smart Biomedical Waste Management System"
    )