import streamlit as st
from database import get_connection
from streamlit_geolocation import streamlit_geolocation
from notification import create_notification


def driver_portal_page(user):

    # -----------------------------------------
    # HEALTHCARE DASHBOARD STYLING
    # -----------------------------------------

    st.markdown("""
    <style>
    .driver-header {
        background: linear-gradient(120deg, #087f8c, #13a89e);
        padding: 25px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }

    .driver-header h2 {
        color: white;
        margin: 0;
        font-size: 27px;
    }

    .driver-header p {
        color: #e7ffff;
        margin: 7px 0 0 0;
    }

    .section-heading {
        font-size: 20px;
        font-weight: 700;
        margin-top: 12px;
        margin-bottom: 10px;
    }

    .driver-info-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-left: 4px solid #0d9488;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
    }

    .driver-info-card p {
        margin: 5px 0;
    }

    div[data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px;
        padding: 15px;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--text-color);
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
    # SUCCESS MESSAGE
    # -----------------------------------------

    if st.session_state.get("location_saved"):
        st.success("Your location has been saved successfully!")
        st.session_state["location_saved"] = False

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    st.markdown(f"""
    <div class="driver-header">
        <h2>🚚 Driver Dashboard</h2>
        <p>Welcome, {user['full_name']}!</p>
        <p>Manage collection assignments, share your location
        and update transportation status.</p>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------
    # FETCH ASSIGNMENTS
    # -----------------------------------------

    conn = get_connection()

    try:
        assignments = conn.execute(
            """
            SELECT
                cr.request_id,
                cr.waste_id,
                cr.status,
                cr.requested_at,
                cr.driver_response,
                cr.driver_response_at,
                w.colour_category,
                w.waste_weight,
                w.facility_name,
                w.facility_location,
                h.hospital_name
            FROM collection_requests cr
            JOIN waste_records w ON cr.waste_id = w.waste_id
            LEFT JOIN hospitals h ON w.hospital_id = h.hospital_id
            WHERE cr.assigned_driver = ?
            ORDER BY cr.request_id DESC
            """,
            (user["user_id"],)
        ).fetchall()

    finally:
        conn.close()

    active_assignments = [
        row for row in assignments
        if row["status"] not in ["Completed", "Cancelled"]
    ]

    accepted_assignments = [
        row for row in active_assignments
        if row["driver_response"] == "Accepted"
    ]

    completed = sum(
        1 for row in assignments
        if row["status"] == "Completed"
    )

    pending = sum(
        1 for row in active_assignments
        if (row["driver_response"] or "Pending") == "Pending"
    )

    # -----------------------------------------
    # DASHBOARD METRICS
    # -----------------------------------------

    st.markdown('<div class="section-heading">📊 Collection Overview</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Assigned", len(assignments))
    c2.metric("Active Collections", len(active_assignments))
    c3.metric("Pending Responses", pending)
    c4.metric("Completed", completed)

    st.divider()

    # -----------------------------------------
    # ASSIGNMENT RESPONSE
    # -----------------------------------------

    st.markdown(
        '<div class="section-heading">📋 Assignment Management</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Review your assigned biomedical waste collections "
        "and accept or reject them."
    )

    if not active_assignments:
        st.info("There are no active collection assignments.")
    else:

        for record in active_assignments:

            response = record["driver_response"] or "Pending"

            with st.expander(
                f"Request #{record['request_id']}  |  Waste ID {record['waste_id']}",
                expanded=(response == "Pending")
            ):

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Hospital**")
                    st.write(record["hospital_name"] or "Not available")

                    st.write("**Waste Category**")
                    st.write(record["colour_category"])

                    st.write("**Waste Weight**")
                    st.write(f"{record['waste_weight']} kg")

                with col2:
                    st.write("**Facility**")
                    st.write(record["facility_name"])

                    st.write("**Facility Location**")
                    st.write(record["facility_location"])

                    st.write("**Assignment Response**")
                    st.write(response)

                if response == "Pending":

                    st.info("Please respond to this collection assignment.")

                    accept_col, reject_col = st.columns(2)

                    # ACCEPT ASSIGNMENT
                    with accept_col:

                        if st.button(
                            "✓ Accept Assignment",
                            key=f"accept_{record['request_id']}",
                            use_container_width=True
                        ):

                            conn = get_connection()

                            try:
                                result = conn.execute(
                                    """
                                    UPDATE collection_requests
                                    SET driver_response = 'Accepted',
                                        driver_response_at = CURRENT_TIMESTAMP
                                    WHERE request_id = ?
                                    AND assigned_driver = ?
                                    AND driver_response = 'Pending'
                                    """,
                                    (
                                        record["request_id"],
                                        user["user_id"]
                                    )
                                )

                                if result.rowcount == 0:
                                    conn.rollback()
                                    st.error(
                                        "Unable to accept. Please refresh and try again."
                                    )
                                else:
                                    conn.execute(
                                        """
                                        INSERT INTO activity_logs
                                        (user_id, action, details)
                                        VALUES (?, ?, ?)
                                        """,
                                        (
                                            user["user_id"],
                                            "Assignment Accepted",
                                            f"Request {record['request_id']} accepted"
                                        )
                                    )

                                    conn.commit()

                                    admin_conn = get_connection()

                                    try:
                                        admins = admin_conn.execute(
                                            """
                                            SELECT user_id
                                            FROM users
                                            WHERE role = 'admin'
                                            AND is_active = 1
                                            """
                                        ).fetchall()
                                    finally:
                                        admin_conn.close()

                                    for admin in admins:
                                        create_notification(
                                            admin["user_id"],
                                            f"Driver {user['full_name']} accepted Request #{record['request_id']}.",
                                            record["waste_id"]
                                        )

                                    st.success("Assignment accepted successfully!")
                                    st.rerun()

                            except Exception as error:
                                conn.rollback()
                                st.error(f"Unable to accept assignment: {error}")

                            finally:
                                conn.close()

                    # REJECT ASSIGNMENT
                    with reject_col:

                        reject_reason = st.text_area(
                            "Reason for rejection",
                            key=f"reject_reason_{record['request_id']}",
                            placeholder="Enter the reason for rejecting..."
                        )

                        if st.button(
                            "✕ Reject Assignment",
                            key=f"reject_{record['request_id']}",
                            use_container_width=True
                        ):

                            if not reject_reason.strip():
                                st.warning(
                                    "Please enter a reason for rejection."
                                )

                            else:
                                conn = get_connection()

                                try:
                                    result = conn.execute(
                                        """
                                        UPDATE collection_requests
                                        SET driver_response = 'Rejected',
                                            driver_response_at = CURRENT_TIMESTAMP
                                        WHERE request_id = ?
                                        AND assigned_driver = ?
                                        AND driver_response = 'Pending'
                                        """,
                                        (
                                            record["request_id"],
                                            user["user_id"]
                                        )
                                    )

                                    if result.rowcount == 0:
                                        conn.rollback()
                                        st.error(
                                            "Unable to reject. Please refresh and try again."
                                        )

                                    else:
                                        conn.execute(
                                            """
                                            INSERT INTO activity_logs
                                            (user_id, action, details)
                                            VALUES (?, ?, ?)
                                            """,
                                            (
                                                user["user_id"],
                                                "Assignment Rejected",
                                                f"Request {record['request_id']} rejected: {reject_reason.strip()}"
                                            )
                                        )

                                        conn.commit()

                                        admin_conn = get_connection()

                                        try:
                                            admins = admin_conn.execute(
                                                """
                                                SELECT user_id
                                                FROM users
                                                WHERE role = 'admin'
                                                AND is_active = 1
                                                """
                                            ).fetchall()
                                        finally:
                                            admin_conn.close()

                                        for admin in admins:
                                            create_notification(
                                                admin["user_id"],
                                                f"Driver {user['full_name']} rejected Request #{record['request_id']}. Reason: {reject_reason.strip()}",
                                                record["waste_id"]
                                            )

                                        st.success("Assignment rejected successfully!")
                                        st.rerun()

                                except Exception as error:
                                    conn.rollback()
                                    st.error(f"Unable to reject assignment: {error}")

                                finally:
                                    conn.close()

                elif response == "Accepted":
                    st.success("You accepted this assignment.")

                elif response == "Rejected":
                    st.warning(
                        "You rejected this assignment. "
                        "The administrator can reassign it."
                    )

    # -----------------------------------------
    # GPS LOCATION SHARING
    # -----------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-heading">📍 Driver Location Sharing</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Allow browser location permission to detect your current location. "
        "Your coordinates will only be saved when you click "
        "'Save Current Location'."
    )

    if not accepted_assignments:

        st.warning(
            "You need to accept an assignment before sharing your location."
        )

    else:

        location = streamlit_geolocation()

        if (
            location
            and location.get("latitude") is not None
            and location.get("longitude") is not None
        ):

            latitude = location["latitude"]
            longitude = location["longitude"]

            st.success("Current location detected successfully!")

            col1, col2 = st.columns(2)

            col1.metric("Latitude", round(latitude, 6))
            col2.metric("Longitude", round(longitude, 6))

            request_options = {
                f"Request #{row['request_id']} - Waste ID {row['waste_id']}":
                row["request_id"]
                for row in accepted_assignments
            }

            selected_request = st.selectbox(
                "Select Accepted Collection",
                list(request_options.keys()),
                key="gps_collection_request"
            )

            if st.button(
                "📍 Save Current Location",
                key="save_driver_location",
                use_container_width=True
            ):

                request_id = request_options[selected_request]

                conn = get_connection()

                try:
                    result = conn.execute(
                        """
                        INSERT INTO transport_logs
                        (
                            request_id,
                            driver_id,
                            status,
                            latitude,
                            longitude,
                            location_updated_at,
                            notes
                        )
                        SELECT
                            request_id,
                            assigned_driver,
                            status,
                            ?,
                            ?,
                            CURRENT_TIMESTAMP,
                            ?
                        FROM collection_requests
                        WHERE request_id = ?
                        AND assigned_driver = ?
                        AND driver_response = 'Accepted'
                        AND status NOT IN ('Completed', 'Cancelled')
                        """,
                        (
                            latitude,
                            longitude,
                            "Driver shared current GPS location",
                            request_id,
                            user["user_id"]
                        )
                    )

                    if result.rowcount == 0:
                        conn.rollback()
                        st.error(
                            "Location was not saved. Please refresh and try again."
                        )

                    else:
                        conn.execute(
                            """
                            INSERT INTO activity_logs
                            (user_id, action, details)
                            VALUES (?, ?, ?)
                            """,
                            (
                                user["user_id"],
                                "Location Shared",
                                f"GPS location saved for Request {request_id}"
                            )
                        )

                        conn.commit()

                        st.session_state["location_saved"] = True
                        st.rerun()

                except Exception as error:
                    conn.rollback()
                    st.error(f"Unable to save location: {error}")

                finally:
                    conn.close()

        else:
            st.warning(
                "Location not detected. Press the location button "
                "and allow browser permission."
            )

    # -----------------------------------------
    # TRANSPORTATION STATUS MANAGEMENT
    # -----------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-heading">🚛 Transportation Management</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Update the collection progress after accepting an assignment."
    )

    if not assignments:

        st.info("No collection requests have been assigned to you yet.")

    else:

        for record in assignments:

            with st.expander(
                f"Request #{record['request_id']}  |  Waste ID {record['waste_id']}",
                expanded=False
            ):

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Hospital:**", record["hospital_name"] or "Not available")
                    st.write("**Waste Category:**", record["colour_category"])
                    st.write("**Weight:**", f"{record['waste_weight']} kg")

                with col2:
                    st.write("**Facility:**", record["facility_name"])
                    st.write("**Location:**", record["facility_location"])
                    st.write("**Requested At:**", record["requested_at"])

                st.write("**Assignment Response:**",
                         record["driver_response"] or "Pending")

                st.write("**Current Collection Status:**",
                         record["status"])

                if record["status"] in ["Completed", "Cancelled"]:

                    st.success(
                        f"This collection is {record['status'].lower()}."
                    )
                    continue

                if record["driver_response"] != "Accepted":

                    st.info(
                        "Accept the assignment before updating transportation status."
                    )
                    continue

                status_options = [
                    "Assigned",
                    "In Transit",
                    "Completed"
                ]

                current_status = record["status"]

                if current_status not in status_options:
                    st.warning(
                        f"Unknown collection status: {current_status}"
                    )
                    continue

                selected_index = status_options.index(current_status)

                new_status = st.selectbox(
                    "Update Collection Status",
                    status_options,
                    index=selected_index,
                    key=f"driver_status_{record['request_id']}"
                )

                notes = st.text_area(
                    "Update Notes",
                    key=f"driver_notes_{record['request_id']}",
                    placeholder="Enter an optional status update..."
                )

                if st.button(
                    "💾 Save Transportation Update",
                    key=f"save_driver_{record['request_id']}",
                    use_container_width=True
                ):

                    if new_status == current_status:

                        st.warning("Please select a different status.")

                    else:

                        conn = get_connection()

                        try:
                            result = conn.execute(
                                """
                                UPDATE collection_requests
                                SET status = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE request_id = ?
                                AND assigned_driver = ?
                                AND status = ?
                                AND driver_response = 'Accepted'
                                """,
                                (
                                    new_status,
                                    record["request_id"],
                                    user["user_id"],
                                    current_status
                                )
                            )

                            if result.rowcount == 0:

                                conn.rollback()

                                st.error(
                                    "This collection could not be updated. "
                                    "Please refresh the page."
                                )

                            else:

                                conn.execute(
                                    """
                                    UPDATE waste_records
                                    SET collection_status = ?
                                    WHERE waste_id = ?
                                    """,
                                    (
                                        new_status,
                                        record["waste_id"]
                                    )
                                )

                                conn.execute(
                                    """
                                    INSERT INTO transport_logs
                                    (request_id, driver_id, status, notes)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        record["request_id"],
                                        user["user_id"],
                                        new_status,
                                        notes.strip()
                                    )
                                )

                                conn.execute(
                                    """
                                    INSERT INTO activity_logs
                                    (user_id, action, details)
                                    VALUES (?, ?, ?)
                                    """,
                                    (
                                        user["user_id"],
                                        "Transportation Update",
                                        f"Request {record['request_id']}: {new_status}"
                                    )
                                )

                                conn.commit()

                                st.success(
                                    "Transportation status updated successfully."
                                )

                                st.rerun()

                        except Exception as error:

                            conn.rollback()

                            st.error(
                                f"Unable to update status: {error}"
                            )

                        finally:
                            conn.close()

    # -----------------------------------------
    # FOOTER
    # -----------------------------------------

    st.divider()

    st.caption("MED WASTE AI | Smart Biomedical Waste Management System")