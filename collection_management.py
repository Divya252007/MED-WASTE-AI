import streamlit as st
from database import get_connection


def collection_management_page(user):

    # -----------------------------------------
    # HEALTHCARE DASHBOARD STYLING
    # -----------------------------------------

    st.markdown("""
    <style>
    .collection-header {
        background: linear-gradient(120deg, #087f8c, #13a89e);
        padding: 25px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }

    .collection-header h2 {
        color: white;
        margin: 0;
        font-size: 27px;
    }

    .collection-header p {
        color: #e7ffff;
        margin-top: 7px;
    }

    .section-heading {
        font-size: 20px;
        font-weight: 700;
        margin-top: 12px;
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

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    st.markdown("""
    <div class="collection-header">
        <h2>🚛 Collection Management</h2>
        <p>Manage biomedical waste collection requests,
        driver assignments and transportation coordination.</p>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------
    # FETCH REQUESTS AND DRIVERS
    # -----------------------------------------

    conn = get_connection()

    try:
        if user["role"] == "admin":

            requests = conn.execute(
                """
                SELECT
                    cr.request_id,
                    cr.waste_id,
                    cr.status,
                    cr.requested_at,
                    cr.assigned_driver,
                    cr.driver_response,
                    cr.driver_response_at,
                    w.hospital_id,
                    w.colour_category,
                    w.waste_weight,
                    h.hospital_name,
                    u.full_name AS driver_name
                FROM collection_requests cr
                JOIN waste_records w ON cr.waste_id = w.waste_id
                LEFT JOIN hospitals h ON w.hospital_id = h.hospital_id
                LEFT JOIN users u ON cr.assigned_driver = u.user_id
                ORDER BY cr.request_id DESC
                """
            ).fetchall()

            drivers = conn.execute(
                """
                SELECT user_id, full_name, hospital_id
                FROM users
                WHERE role = 'driver' AND is_active = 1
                ORDER BY full_name
                """
            ).fetchall()

        else:

            requests = conn.execute(
                """
                SELECT
                    cr.request_id,
                    cr.waste_id,
                    cr.status,
                    cr.requested_at,
                    cr.assigned_driver,
                    cr.driver_response,
                    cr.driver_response_at,
                    w.hospital_id,
                    w.colour_category,
                    w.waste_weight,
                    h.hospital_name,
                    u.full_name AS driver_name
                FROM collection_requests cr
                JOIN waste_records w ON cr.waste_id = w.waste_id
                LEFT JOIN hospitals h ON w.hospital_id = h.hospital_id
                LEFT JOIN users u ON cr.assigned_driver = u.user_id
                WHERE cr.requested_by = ?
                ORDER BY cr.request_id DESC
                """,
                (user["user_id"],)
            ).fetchall()

            drivers = []

    finally:
        conn.close()

    # -----------------------------------------
    # EMPTY STATE
    # -----------------------------------------

    if not requests:
        st.info("No collection requests found.")
        st.caption("MED WASTE AI | Collection Management")
        return

    # -----------------------------------------
    # COLLECTION METRICS
    # -----------------------------------------

    st.markdown(
        '<div class="section-heading">📊 Collection Overview</div>',
        unsafe_allow_html=True
    )

    total_requests = len(requests)

    completed = sum(
        1 for row in requests
        if row["status"] == "Completed"
    )

    pending = sum(
        1 for row in requests
        if row["status"] not in ["Completed", "Cancelled"]
        and (row["driver_response"] or "Pending") == "Pending"
    )

    assigned = sum(
        1 for row in requests
        if row["assigned_driver"] is not None
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Requests", total_requests)
    c2.metric("Assigned Requests", assigned)
    c3.metric("Pending Responses", pending)
    c4.metric("Completed", completed)

    st.divider()

    # -----------------------------------------
    # COLLECTION REQUEST TABLE
    # -----------------------------------------

    st.markdown(
        '<div class="section-heading">📋 Collection Requests</div>',
        unsafe_allow_html=True
    )

    st.caption("View collection details and driver response information.")

    request_data = [
        {
            "Request ID": row["request_id"],
            "Waste ID": row["waste_id"],
            "Hospital": row["hospital_name"] or "Not available",
            "Category": row["colour_category"],
            "Weight (kg)": row["waste_weight"],
            "Collection Status": row["status"],
            "Assigned Driver": row["driver_name"] or "Not assigned",
            "Driver Response": row["driver_response"] or "Pending",
            "Response Time": row["driver_response_at"] or "Not responded"
        }
        for row in requests
    ]

    st.dataframe(
        request_data,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------
    # REQUEST DETAILS
    # -----------------------------------------

    with st.expander("🔎 View Collection Request Details"):

        for row in requests:

            st.markdown(f"**Request #{row['request_id']}**")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Waste ID:**", row["waste_id"])
                st.write("**Hospital:**", row["hospital_name"] or "Not available")
                st.write("**Category:**", row["colour_category"])

            with col2:
                st.write("**Weight:**", f"{row['waste_weight']} kg")
                st.write("**Status:**", row["status"])
                st.write("**Driver:**", row["driver_name"] or "Not assigned")

            st.divider()

    # -----------------------------------------
    # NON-ADMIN VIEW
    # -----------------------------------------

    if user["role"] != "admin":
        st.caption("MED WASTE AI | Collection Management")
        return

    # -----------------------------------------
    # ASSIGN / REASSIGN DRIVER
    # -----------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-heading">👨‍⚕️ Driver Assignment Management</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Assign an active driver to a new collection request "
        "or reassign a rejected request."
    )

    assignable = [
        row for row in requests
        if (
            row["status"] not in ["Completed", "Cancelled"]
            and (
                row["assigned_driver"] is None
                or row["driver_response"] == "Rejected"
            )
        )
    ]

    if not assignable:

        st.success(
            "All available collection requests have been assigned. "
            "There are no requests waiting for assignment."
        )

        st.caption("MED WASTE AI | Collection Management")
        return

    if not drivers:

        st.warning("Create an active Driver account first.")
        return

    # -----------------------------------------
    # REQUEST SELECTION
    # -----------------------------------------

    request_options = {
        (
            f"Request #{row['request_id']} - "
            f"{'Reassignment Required' if row['driver_response'] == 'Rejected' else 'New Request'}"
        ): row["request_id"]
        for row in assignable
    }

    selected_label = st.selectbox(
        "Select Collection Request",
        list(request_options.keys()),
        key="collection_request_selection"
    )

    request_id = request_options[selected_label]

    selected_request = next(
        row for row in assignable
        if row["request_id"] == request_id
    )

    # -----------------------------------------
    # SELECTED REQUEST INFORMATION
    # -----------------------------------------

    st.markdown("#### Selected Request Information")

    col1, col2, col3 = st.columns(3)

    col1.metric("Request ID", f"#{request_id}")
    col2.metric("Waste ID", selected_request["waste_id"])
    col3.metric(
        "Weight",
        f"{selected_request['waste_weight']} kg"
    )

    st.write("**Hospital:**", selected_request["hospital_name"])
    st.write("**Waste Category:**", selected_request["colour_category"])
    st.write("**Collection Status:**", selected_request["status"])

    if selected_request["driver_response"] == "Rejected":

        st.warning(
            f"Previous driver ({selected_request['driver_name']}) "
            "rejected this assignment. Please select another driver."
        )

    # -----------------------------------------
    # ELIGIBLE DRIVERS
    # -----------------------------------------

    st.markdown("#### Select Eligible Driver")

    eligible_drivers = [
        driver for driver in drivers
        if (
            driver["hospital_id"] == selected_request["hospital_id"]
            and driver["user_id"] != selected_request["assigned_driver"]
        )
    ]

    if not eligible_drivers:

        st.warning(
            "No other active driver is available for this hospital. "
            "Create or activate another driver account."
        )

        return

    driver_ids = [
        driver["user_id"]
        for driver in eligible_drivers
    ]

    driver_id = st.selectbox(
        "Choose Driver",
        driver_ids,
        format_func=lambda value: next(
            driver["full_name"]
            for driver in eligible_drivers
            if driver["user_id"] == value
        ),
        key=f"eligible_driver_{request_id}"
    )

    selected_driver = next(
        driver for driver in eligible_drivers
        if driver["user_id"] == driver_id
    )

    st.info(
        f"Selected Driver: {selected_driver['full_name']}"
    )

    # -----------------------------------------
    # ASSIGNMENT BUTTON
    # -----------------------------------------

    button_label = (
        "🔄 Reassign Driver"
        if selected_request["driver_response"] == "Rejected"
        else "✓ Assign Driver"
    )

    if st.button(
        button_label,
        use_container_width=True,
        key=f"assign_driver_{request_id}"
    ):

        conn = get_connection()

        try:

            cursor = conn.execute(
                """
                UPDATE collection_requests
                SET assigned_driver = ?,
                    status = 'Assigned',
                    driver_response = 'Pending',
                    driver_response_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE request_id = ?
                AND status NOT IN ('Completed', 'Cancelled')
                AND (
                    assigned_driver IS NULL
                    OR driver_response = 'Rejected'
                )
                """,
                (driver_id, request_id)
            )

            if cursor.rowcount == 0:

                conn.rollback()

                st.warning(
                    "This request is no longer available. Please refresh."
                )

                st.rerun()

            conn.execute(
                """
                UPDATE waste_records
                SET collection_status = 'Assigned'
                WHERE waste_id = ?
                """,
                (selected_request["waste_id"],)
            )

            # Notify newly assigned driver.
            conn.execute(
                """
                INSERT INTO notifications
                (user_id, message, related_waste_id)
                VALUES (?, ?, ?)
                """,
                (
                    driver_id,
                    (
                        f"New Collection Assigned! "
                        f"Request ID: #{request_id}, "
                        f"Waste ID: {selected_request['waste_id']}, "
                        f"Hospital: {selected_request['hospital_name']}, "
                        f"Category: {selected_request['colour_category']}, "
                        f"Weight: {selected_request['waste_weight']} kg. "
                        f"Please accept or reject this assignment."
                    ),
                    selected_request["waste_id"]
                )
            )

            # Activity log.
            conn.execute(
                """
                INSERT INTO activity_logs
                (user_id, action, details)
                VALUES (?, ?, ?)
                """,
                (
                    user["user_id"],
                    "Driver Assigned",
                    f"Request {request_id} assigned to driver {driver_id}"
                )
            )

            conn.commit()

            st.success(
                "Driver assigned successfully! "
                "The driver response is now Pending."
            )

            st.rerun()

        except Exception as error:

            conn.rollback()

            st.error(f"Unable to assign driver: {error}")

        finally:
            conn.close()

    st.divider()

    st.caption("MED WASTE AI | Smart Biomedical Waste Management System")