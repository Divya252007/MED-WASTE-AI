import streamlit as st
from pathlib import Path

from database import get_connection
from notification import create_notification


BASE_DIR = Path(__file__).resolve().parent


def doctor_portal_page(user):

    # =========================================
    # PAGE HEADER
    # =========================================

    st.title("Doctor Dashboard")

    st.markdown(
        f"### Welcome, Dr. {user['full_name']} 👋"
    )

    st.caption(
        "Review biomedical waste records, check AI suggestions "
        "and manage verification decisions."
    )

    hospital_id = user.get("hospital_id")

    if hospital_id is None:
        st.error(
            "Your account is not assigned to a hospital. "
            "Please contact the administrator."
        )
        return

    # =========================================
    # AI CATEGORY MISMATCH CHECK
    # =========================================

    def is_ai_mismatch(record):

        ai_category = record["ai_suggested_category"]
        registered_category = record["colour_category"]

        valid_categories = [
            "yellow",
            "red",
            "white",
            "blue"
        ]

        if not ai_category or not registered_category:
            return False

        ai_category = str(ai_category).strip().lower()
        registered_category = str(
            registered_category
        ).strip().lower()

        return (
            ai_category in valid_categories
            and registered_category in valid_categories
            and ai_category != registered_category
        )

    # =========================================
    # LOAD HOSPITAL DATA
    # =========================================

    conn = get_connection()

    try:

        hospital = conn.execute(
            """
            SELECT hospital_name
            FROM hospitals
            WHERE hospital_id = ?
            """,
            (hospital_id,)
        ).fetchone()

        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM waste_records
            WHERE hospital_id = ?
            """,
            (hospital_id,)
        ).fetchone()[0]

        pending = conn.execute(
            """
            SELECT COUNT(*)
            FROM waste_records
            WHERE hospital_id = ?
              AND verification_status = 'Pending'
            """,
            (hospital_id,)
        ).fetchone()[0]

        approved = conn.execute(
            """
            SELECT COUNT(*)
            FROM waste_records
            WHERE hospital_id = ?
              AND verification_status = 'Approved'
            """,
            (hospital_id,)
        ).fetchone()[0]

        rejected = conn.execute(
            """
            SELECT COUNT(*)
            FROM waste_records
            WHERE hospital_id = ?
              AND verification_status = 'Rejected'
            """,
            (hospital_id,)
        ).fetchone()[0]

        records = conn.execute(
            """
            SELECT *
            FROM waste_records
            WHERE hospital_id = ?
            ORDER BY waste_id DESC
            """,
            (hospital_id,)
        ).fetchall()

    finally:
        conn.close()

    hospital_name = (
        hospital["hospital_name"]
        if hospital
        else "Hospital"
    )

    # =========================================
    # DASHBOARD SUMMARY
    # =========================================

    st.subheader(f"🏥 {hospital_name}")

    st.caption(
        "Hospital-wise biomedical waste verification overview."
    )

    mismatch_count = sum(
        1 for record in records
        if is_ai_mismatch(record)
    )

    pending_mismatches = sum(
        1 for record in records
        if (
            record["verification_status"] == "Pending"
            and is_ai_mismatch(record)
        )
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Waste Records",
        total,
        border=True
    )

    c2.metric(
        "Pending Verification",
        pending,
        border=True
    )

    c3.metric(
        "Approved Records",
        approved,
        border=True
    )

    c4, c5, c6 = st.columns(3)

    c4.metric(
        "Rejected Records",
        rejected,
        border=True
    )

    c5.metric(
        "AI Category Mismatches",
        mismatch_count,
        border=True
    )

    c6.metric(
        "Pending AI Mismatches",
        pending_mismatches,
        border=True
    )

    if pending_mismatches > 0:

        st.warning(
            f"{pending_mismatches} pending record(s) have "
            "different AI-suggested and registered categories. "
            "Please review them carefully."
        )

    else:

        st.success(
            "No pending AI category mismatches found."
        )

    st.info(
        "AI category mismatch is a comparison between the "
        "AI suggestion and the registered category. It is "
        "not an independently measured AI accuracy score. "
        "Final verification must be done by the doctor."
    )

    st.divider()

    # =========================================
    # MAIN TABS
    # =========================================

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Waste Records",
            "🔍 Verify Waste",
            "📜 Verification History"
        ]
    )

    # =========================================
    # TAB 1: WASTE RECORDS
    # =========================================

    with tab1:

        st.subheader("Registered Waste Records")

        st.caption(
            "View waste details and AI classification information."
        )

        if records:

            search_id = st.text_input(
                "Search by Waste ID",
                placeholder="Enter a Waste ID or leave empty",
                key="doctor_waste_search"
            )

            category_filter = st.selectbox(
                "Filter by Waste Category",
                [
                    "All Categories",
                    "Yellow",
                    "Red",
                    "White",
                    "Blue"
                ],
                key="doctor_category_filter"
            )

            status_filter = st.selectbox(
                "Filter by Verification Status",
                [
                    "All Statuses",
                    "Pending",
                    "Approved",
                    "Rejected",
                    "Correction Requested"
                ],
                key="doctor_status_filter"
            )

            filtered_records = []

            for record in records:

                if search_id.strip():

                    if search_id.strip() != str(
                        record["waste_id"]
                    ):
                        continue

                if category_filter != "All Categories":

                    if str(
                        record["colour_category"]
                    ).strip().lower() != category_filter.lower():
                        continue

                if status_filter != "All Statuses":

                    if record["verification_status"] != status_filter:
                        continue

                filtered_records.append(record)

            st.caption(
                f"Showing {len(filtered_records)} "
                f"of {len(records)} records."
            )

            if filtered_records:

                for record in filtered_records:

                    with st.expander(
                        f"Waste Record #{record['waste_id']} "
                        f"• {record['verification_status']}"
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown("**Waste Information**")

                            st.write(
                                "**Weight:**",
                                f"{record['waste_weight']} kg"
                            )

                            st.write(
                                "**Registered Category:**",
                                record["colour_category"]
                            )

                            st.write(
                                "**Materials:**",
                                record["waste_materials"]
                            )

                            st.write(
                                "**Facility:**",
                                record["facility_name"]
                            )

                            st.write(
                                "**Facility Location:**",
                                record["facility_location"]
                            )

                            st.write(
                                "**Verification Status:**",
                                record["verification_status"]
                            )

                        with col2:

                            st.markdown("**AI Analysis**")

                            st.write(
                                "**AI Suggested Category:**",
                                record["ai_suggested_category"]
                                or "Not analysed"
                            )

                            st.write(
                                "**AI Confidence:**",
                                record["ai_confidence"]
                                or "Not available"
                            )

                            st.write(
                                "**AI Explanation:**",
                                record["ai_explanation"]
                                or "Not available"
                            )

                            if is_ai_mismatch(record):

                                st.warning(
                                    "AI category differs from "
                                    "the registered category."
                                )

                            elif (
                                record["ai_suggested_category"]
                                and str(
                                    record["ai_suggested_category"]
                                ).strip().lower()
                                in ["yellow", "red", "white", "blue"]
                            ):

                                st.success(
                                    "AI and registered categories match."
                                )

                        # Image preview

                        if record["image_path"]:

                            image_path = (
                                BASE_DIR / record["image_path"]
                            )

                            if image_path.exists():

                                st.divider()

                                st.image(
                                    str(image_path),
                                    caption="Uploaded Waste Image",
                                    width=350
                                )

            else:

                st.info(
                    "No records match the selected filters."
                )

        else:

            st.info("No waste records found for this hospital.")

    # =========================================
    # TAB 2: VERIFY WASTE
    # =========================================

    with tab2:

        st.subheader("Waste Verification")

        st.caption(
            "Review pending records and submit your verification decision."
        )

        pending_records = [
            row for row in records
            if row["verification_status"] == "Pending"
        ]

        if not pending_records:

            st.success(
                "There are no pending waste records to verify."
            )

        else:

            st.metric(
                "Records Awaiting Verification",
                len(pending_records),
                border=True
            )

            selected_id = st.selectbox(
                "Select Waste Record",
                [
                    row["waste_id"]
                    for row in pending_records
                ],
                format_func=lambda value: f"Waste Record #{value}",
                key="verify_waste_id"
            )

            selected = next(
                row for row in pending_records
                if row["waste_id"] == selected_id
            )

            st.divider()

            st.markdown("### Waste Information")

            col1, col2 = st.columns(2)

            with col1:

                st.write(
                    "**Waste Weight:**",
                    f"{selected['waste_weight']} kg"
                )

                st.write(
                    "**Registered Category:**",
                    selected["colour_category"]
                )

                st.write(
                    "**Materials:**",
                    selected["waste_materials"]
                )

                st.write(
                    "**Facility:**",
                    selected["facility_name"]
                )

                st.write(
                    "**Location:**",
                    selected["facility_location"]
                )

            with col2:

                st.write(
                    "**AI Suggested Category:**",
                    selected["ai_suggested_category"]
                    or "Not analysed"
                )

                st.write(
                    "**AI Confidence:**",
                    selected["ai_confidence"]
                    or "Not available"
                )

                st.write(
                    "**Current Status:**",
                    selected["verification_status"]
                )

            # AI mismatch warning

            if is_ai_mismatch(selected):

                st.warning(
                    "AI Category Mismatch: The AI-suggested "
                    "category differs from the registered category. "
                    "Please review the waste carefully."
                )

            # Gemini AI explanation

            st.markdown("### 🤖 Gemini AI Analysis")

            st.info(
                selected["ai_explanation"]
                or "No AI explanation available."
            )

            st.warning(
                "Gemini AI output is only a suggestion. "
                "Review the uploaded evidence and applicable "
                "biomedical waste rules before making a decision."
            )

            # Image preview

            if selected["image_path"]:

                image_path = (
                    BASE_DIR / selected["image_path"]
                )

                if image_path.exists():

                    st.markdown("### Waste Image")

                    st.image(
                        str(image_path),
                        caption="Image submitted for verification",
                        width=400
                    )

            st.divider()

            # Verification form

            st.markdown("### Verification Decision")

            decision = st.selectbox(
                "Select Decision",
                [
                    "Approved",
                    "Rejected",
                    "Correction Requested"
                ],
                key="verification_decision"
            )

            reason = st.text_area(
                "Reason or Doctor's Remarks",
                placeholder="Enter remarks for this verification...",
                key="verification_reason"
            )

            if st.button(
                "Submit Verification",
                type="primary",
                use_container_width=True
            ):

                if decision != "Approved" and not reason.strip():

                    st.error(
                        "Please enter a reason for this decision."
                    )

                else:

                    conn = get_connection()

                    try:

                        cursor = conn.execute(
                            """
                            UPDATE waste_records
                            SET verification_status = ?
                            WHERE waste_id = ?
                              AND hospital_id = ?
                              AND verification_status = 'Pending'
                            """,
                            (
                                decision,
                                selected_id,
                                hospital_id
                            )
                        )

                        if cursor.rowcount == 0:

                            conn.rollback()

                            st.warning(
                                "This record has already been verified. "
                                "Please refresh the page."
                            )

                        else:

                            # Save verification history

                            conn.execute(
                                """
                                INSERT INTO verification_history
                                (
                                    waste_id,
                                    verifier_id,
                                    decision,
                                    reason
                                )
                                VALUES (?, ?, ?, ?)
                                """,
                                (
                                    selected_id,
                                    user["user_id"],
                                    decision,
                                    reason.strip()
                                )
                            )

                            # Save activity log

                            conn.execute(
                                """
                                INSERT INTO activity_logs
                                (user_id, action, details)
                                VALUES (?, ?, ?)
                                """,
                                (
                                    user["user_id"],
                                    "Waste Verification",
                                    f"Waste ID {selected_id}: {decision}"
                                )
                            )

                            # Commit verification first

                            conn.commit()

                            # Notify original nurse/staff creator

                            try:

                                creator_conn = get_connection()

                                try:

                                    creator = creator_conn.execute(
                                        """
                                        SELECT user_id, role
                                        FROM users
                                        WHERE user_id = ?
                                          AND hospital_id = ?
                                        """,
                                        (
                                            selected["user_id"],
                                            hospital_id
                                        )
                                    ).fetchone()

                                finally:
                                    creator_conn.close()

                                if (
                                    creator
                                    and creator["role"] == "staff"
                                ):

                                    notification_message = (
                                        f"Doctor's decision for Waste "
                                        f"Record #{selected_id}: {decision}."
                                    )

                                    if reason.strip():

                                        notification_message += (
                                            f" Doctor's remarks: "
                                            f"{reason.strip()}"
                                        )

                                    create_notification(
                                        creator["user_id"],
                                        notification_message,
                                        selected_id
                                    )

                                    st.success(
                                        "Nurse notification sent successfully."
                                    )

                                else:

                                    st.warning(
                                        "The original record creator "
                                        "was not found as a staff user."
                                    )

                            except Exception as notification_error:

                                st.warning(
                                    "Verification was saved, but nurse "
                                    "notification failed: "
                                    f"{notification_error}"
                                )

                            st.success(
                                f"Waste record #{selected_id} "
                                f"successfully {decision.lower()}."
                            )

                    except Exception as error:

                        conn.rollback()

                        st.error(
                            f"Verification failed: {error}"
                        )

                    finally:
                        conn.close()

                    st.rerun()

    # =========================================
    # TAB 3: VERIFICATION HISTORY
    # =========================================

    with tab3:

        st.subheader("Verification History")

        st.caption(
            "View previous decisions made by doctors in this hospital."
        )

        conn = get_connection()

        try:

            history = conn.execute(
                """
                SELECT
                    vh.verification_id,
                    vh.waste_id,
                    u.full_name AS verifier_name,
                    vh.decision,
                    vh.reason,
                    vh.verified_at
                FROM verification_history vh
                JOIN users u
                    ON vh.verifier_id = u.user_id
                JOIN waste_records wr
                    ON vh.waste_id = wr.waste_id
                WHERE wr.hospital_id = ?
                ORDER BY vh.verification_id DESC
                """,
                (hospital_id,)
            ).fetchall()

        finally:
            conn.close()

        if history:

            st.dataframe(
                [dict(row) for row in history],
                width="stretch",
                hide_index=True
            )

        else:

            st.info(
                "No verification history available yet."
            )

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Doctor Verification Portal"
    )