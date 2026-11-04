import streamlit as st
import folium

from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

from database import get_connection
from notification import create_notification


def admin_portal_page(user):

    # =========================================
    # PAGE HEADER
    # =========================================

    st.title("Admin Dashboard")

    st.markdown(
        f"""
        <div class="portal-header">
            <div>
                <h3>Welcome, {user['full_name']} 👋</h3>
                <p>Manage hospitals, biomedical waste, drivers and system activities.</p>
            </div>
            <div class="portal-tag">SYSTEM ADMINISTRATION</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st_autorefresh(
        interval=30 * 1000,
        key="admin_location_auto_refresh"
    )

    st.divider()

    # =========================================
    # LOAD DATABASE INFORMATION
    # =========================================

    conn = get_connection()

    try:

        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_hospitals = conn.execute(
            "SELECT COUNT(*) FROM hospitals"
        ).fetchone()[0]

        total_waste = conn.execute(
            "SELECT COUNT(*) FROM waste_records"
        ).fetchone()[0]

        pending = conn.execute(
            """
            SELECT COUNT(*) FROM waste_records
            WHERE verification_status = 'Pending'
            """
        ).fetchone()[0]

        total_requests = conn.execute(
            "SELECT COUNT(*) FROM collection_requests"
        ).fetchone()[0]

        recent_records = conn.execute(
            """
            SELECT
                w.waste_id,
                h.hospital_name,
                w.colour_category,
                w.waste_weight,
                w.verification_status,
                w.collection_status,
                w.created_at
            FROM waste_records w
            LEFT JOIN hospitals h
                ON w.hospital_id = h.hospital_id
            ORDER BY w.waste_id DESC
            LIMIT 10
            """
        ).fetchall()

        # Driver response summary
        response_counts = conn.execute(
            """
            SELECT
                COALESCE(driver_response, 'Pending') AS response,
                COUNT(*) AS total
            FROM collection_requests
            WHERE assigned_driver IS NOT NULL
              AND status NOT IN ('Completed', 'Cancelled')
            GROUP BY COALESCE(driver_response, 'Pending')
            """
        ).fetchall()

        response_summary = {
            "Pending": 0,
            "Accepted": 0,
            "Rejected": 0
        }

        for row in response_counts:
            if row["response"] in response_summary:
                response_summary[row["response"]] = row["total"]

        # Pending driver responses
        pending_responses = conn.execute(
            """
            SELECT
                cr.request_id,
                cr.waste_id,
                cr.status,
                cr.driver_response,
                w.colour_category,
                w.waste_weight,
                h.hospital_name,
                u.full_name AS driver_name
            FROM collection_requests cr
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            LEFT JOIN hospitals h
                ON w.hospital_id = h.hospital_id
            LEFT JOIN users u
                ON cr.assigned_driver = u.user_id
            WHERE cr.assigned_driver IS NOT NULL
              AND COALESCE(cr.driver_response, 'Pending') = 'Pending'
              AND cr.status NOT IN ('Completed', 'Cancelled')
            ORDER BY cr.request_id DESC
            """
        ).fetchall()

        # Overdue requests
        overdue_requests = conn.execute(
            """
            SELECT
                cr.request_id,
                cr.waste_id,
                cr.status,
                cr.driver_response,
                cr.requested_at,
                w.colour_category,
                w.waste_weight,
                h.hospital_name,
                u.full_name AS driver_name,
                ROUND(
                    (julianday('now') -
                    julianday(cr.requested_at)) * 24,
                    1
                ) AS waiting_hours
            FROM collection_requests cr
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            LEFT JOIN hospitals h
                ON w.hospital_id = h.hospital_id
            LEFT JOIN users u
                ON cr.assigned_driver = u.user_id
            WHERE cr.status NOT IN ('Completed', 'Cancelled')
              AND cr.requested_at IS NOT NULL
              AND (
                  julianday('now') -
                  julianday(cr.requested_at)
              ) * 24 >= 2
            ORDER BY cr.requested_at ASC
            """
        ).fetchall()

        # Create overdue notifications
        active_admins = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE role = 'admin'
              AND is_active = 1
            """
        ).fetchall()

        for request in overdue_requests:

            alert_message = (
                f"Overdue Collection Alert: Request "
                f"#{request['request_id']} for Waste "
                f"#{request['waste_id']} has crossed "
                f"the 2-hour waiting limit."
            )

            for admin in active_admins:

                existing_alert = conn.execute(
                    """
                    SELECT notification_id
                    FROM notifications
                    WHERE user_id = ?
                      AND message = ?
                    LIMIT 1
                    """,
                    (admin["user_id"], alert_message)
                ).fetchone()

                if not existing_alert:
                    create_notification(
                        admin["user_id"],
                        alert_message,
                        request["waste_id"]
                    )

        # Admin notifications
        admin_notifications = conn.execute(
            """
            SELECT
                notification_id,
                message,
                related_waste_id,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY notification_id DESC
            LIMIT 20
            """,
            (user["user_id"],)
        ).fetchall()

        unread_notifications = conn.execute(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = ?
              AND is_read = 0
            """,
            (user["user_id"],)
        ).fetchone()[0]

        # Driver location information
        location_logs = conn.execute(
            """
            SELECT
                tl.request_id,
                tl.driver_id,
                u.full_name AS driver_name,
                tl.latitude,
                tl.longitude,
                tl.status,
                datetime(
                    tl.location_updated_at,
                    '+5 hours 30 minutes'
                ) AS location_updated_at,
                cr.waste_id,
                w.facility_name,
                w.facility_location
            FROM transport_logs tl
            JOIN users u
                ON tl.driver_id = u.user_id
            JOIN collection_requests cr
                ON tl.request_id = cr.request_id
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            WHERE tl.latitude IS NOT NULL
              AND tl.longitude IS NOT NULL
            ORDER BY tl.location_updated_at DESC
            """
        ).fetchall()

        # Location history
        history = conn.execute(
            """
            SELECT
                tl.request_id,
                tl.driver_id,
                u.full_name AS driver_name,
                tl.latitude,
                tl.longitude,
                tl.status,
                datetime(
                    tl.location_updated_at,
                    '+5 hours 30 minutes'
                ) AS location_updated_at,
                w.facility_name
            FROM transport_logs tl
            JOIN users u
                ON tl.driver_id = u.user_id
            JOIN collection_requests cr
                ON tl.request_id = cr.request_id
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            WHERE tl.latitude IS NOT NULL
              AND tl.longitude IS NOT NULL
            ORDER BY tl.location_updated_at DESC
            """
        ).fetchall()

    finally:
        conn.close()

    # =========================================
    # DASHBOARD SUMMARY
    # =========================================

    st.subheader("System Overview")

    st.caption("A quick overview of your hospital waste management system.")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Users", total_users, border=True)
    c2.metric("Hospitals", total_hospitals, border=True)
    c3.metric("Waste Records", total_waste, border=True)
    c4.metric("Pending Verification", pending, border=True)

    st.markdown("")

    c5, c6 = st.columns(2)

    c5.metric("Collection Requests", total_requests, border=True)
    c6.metric(
        "Unread Notifications",
        unread_notifications,
        border=True
    )

    # =========================================
    # DRIVER ASSIGNMENT MANAGEMENT
    # =========================================

    st.divider()

    st.subheader("🚚 Driver Assignment Management")

    st.caption(
        "Monitor driver responses to assigned waste collection requests."
    )

    n1, n2, n3 = st.columns(3)

    n1.metric(
        "Pending Responses",
        response_summary["Pending"],
        border=True
    )

    n2.metric(
        "Accepted Assignments",
        response_summary["Accepted"],
        border=True
    )

    n3.metric(
        "Rejected Assignments",
        response_summary["Rejected"],
        border=True
    )

    with st.container(border=True):

        st.markdown("**Drivers Yet to Respond**")

        if pending_responses:

            st.dataframe(
                [
                    {
                        "Request ID": row["request_id"],
                        "Waste ID": row["waste_id"],
                        "Driver": row["driver_name"] or "N/A",
                        "Hospital": row["hospital_name"] or "N/A",
                        "Category": row["colour_category"],
                        "Weight (kg)": row["waste_weight"],
                        "Response": row["driver_response"]
                    }
                    for row in pending_responses
                ],
                width="stretch",
                hide_index=True
            )

        else:
            st.success("All active assigned drivers have responded.")

    # =========================================
    # NOTIFICATION CENTER
    # =========================================

    st.divider()

    st.subheader("🔔 Notification Center")

    st.caption("Recent system notifications for this administrator.")

    if admin_notifications:

        for notification in admin_notifications:

            with st.container(border=True):

                col1, col2 = st.columns([5, 1])

                with col1:

                    if notification["is_read"] == 0:
                        st.markdown("🔵 **Unread**")
                    else:
                        st.caption("Read notification")

                    st.write(notification["message"])

                    st.caption(
                        f"Notification #{notification['notification_id']} "
                        f"• Waste ID: "
                        f"{notification['related_waste_id'] or 'N/A'} "
                        f"• {notification['created_at']}"
                    )

                with col2:

                    if notification["is_read"] == 0:

                        if st.button(
                            "Mark Read",
                            key=f"admin_read_{notification['notification_id']}",
                            use_container_width=True
                        ):

                            read_conn = get_connection()

                            try:
                                read_conn.execute(
                                    """
                                    UPDATE notifications
                                    SET is_read = 1
                                    WHERE notification_id = ?
                                      AND user_id = ?
                                    """,
                                    (
                                        notification["notification_id"],
                                        user["user_id"]
                                    )
                                )

                                read_conn.commit()
                                st.rerun()

                            except Exception as error:
                                read_conn.rollback()
                                st.error(
                                    f"Unable to update notification: {error}"
                                )

                            finally:
                                read_conn.close()

    else:
        st.info("No notifications available yet.")

    # =========================================
    # OVERDUE COLLECTION ALERTS
    # =========================================

    st.divider()

    st.subheader("🚨 Overdue Collection Monitoring")

    st.caption(
        "Active collection requests that have been waiting for at least 2 hours."
    )

    if overdue_requests:

        st.error(
            f"{len(overdue_requests)} collection request(s) "
            "have crossed the 2-hour waiting limit."
        )

        overdue_data = [
            {
                "Request ID": row["request_id"],
                "Waste ID": row["waste_id"],
                "Hospital": row["hospital_name"] or "N/A",
                "Category": row["colour_category"],
                "Weight (kg)": row["waste_weight"],
                "Driver": row["driver_name"] or "Not Assigned",
                "Collection Status": row["status"],
                "Driver Response": row["driver_response"] or "Pending",
                "Waiting Hours": row["waiting_hours"]
            }
            for row in overdue_requests
        ]

        st.dataframe(
            overdue_data,
            width="stretch",
            hide_index=True
        )

        st.warning(
            "Review these requests and follow up with the drivers "
            "or arrange reassignment if necessary."
        )

    else:
        st.success("No overdue collection requests at the moment.")

    # =========================================
    # RECENT WASTE RECORDS
    # =========================================

    st.divider()

    st.subheader("♻️ Recent Waste Records")

    st.caption("The latest 10 biomedical waste records in the system.")

    if recent_records:

        st.dataframe(
            [dict(row) for row in recent_records],
            width="stretch",
            hide_index=True
        )

    else:
        st.info("No waste records available.")

    # =========================================
    # DRIVER LOCATION MONITORING
    # =========================================

    st.divider()

    st.subheader("📍 Driver Location Monitoring")

    st.caption(
        "View the latest GPS locations voluntarily shared by drivers."
    )

    latest_locations = {}

    for log in location_logs:

        request_id = log["request_id"]

        if request_id not in latest_locations:
            latest_locations[request_id] = log

    if latest_locations:

        locations = list(latest_locations.values())

        st.metric(
            "Requests With Saved Locations",
            len(locations),
            border=True
        )

        with st.container(border=True):

            st.markdown("**Latest Driver Location Details**")

            location_details = [
                {
                    "Request ID": log["request_id"],
                    "Waste ID": log["waste_id"],
                    "Driver": log["driver_name"],
                    "Facility": log["facility_name"],
                    "Latitude": log["latitude"],
                    "Longitude": log["longitude"],
                    "Status": log["status"],
                    "Last Updated": log["location_updated_at"]
                }
                for log in locations
            ]

            st.dataframe(
                location_details,
                width="stretch",
                hide_index=True
            )

        # Map
        valid_locations = [
            log for log in locations
            if log["latitude"] is not None
            and log["longitude"] is not None
        ]

        if valid_locations:

            first_location = valid_locations[0]

            location_map = folium.Map(
                location=[
                    first_location["latitude"],
                    first_location["longitude"]
                ],
                zoom_start=7,
                tiles="OpenStreetMap"
            )

            for log in valid_locations:

                popup_text = f"""
                Driver: {log['driver_name']}<br>
                Request ID: {log['request_id']}<br>
                Waste ID: {log['waste_id']}<br>
                Facility: {log['facility_name']}<br>
                Status: {log['status']}<br>
                Last Updated: {log['location_updated_at']}
                """

                folium.Marker(
                    location=[
                        log["latitude"],
                        log["longitude"]
                    ],
                    popup=folium.Popup(
                        popup_text,
                        max_width=300
                    ),
                    tooltip=f"Driver: {log['driver_name']}",
                    icon=folium.Icon(
                        color="blue",
                        icon="truck",
                        prefix="fa"
                    )
                ).add_to(location_map)

            with st.container(border=True):

                st.markdown("**Driver Locations on Map**")

                st_folium(
                    location_map,
                    width=None,
                    height=500,
                    key="admin_driver_location_map"
                )

    else:
        st.info(
            "No driver GPS locations have been saved yet. "
            "Locations will appear after drivers share their location."
        )

    # =========================================
    # DRIVER LOCATION HISTORY
    # =========================================

    st.divider()

    st.subheader("🗺️ Driver Location History")

    st.caption("Previous GPS updates recorded for collection requests.")

    if history:

        with st.container(border=True):

            st.dataframe(
                [dict(row) for row in history],
                width="stretch",
                hide_index=True
            )

    else:
        st.info("No location history available yet.")

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Healthcare Waste Management Administration"
    )