import streamlit as st

from database import get_connection


def nurse_portal_page(user):

    # =========================================
    # PAGE HEADER
    # =========================================

    st.title("Nurse Dashboard")

    st.markdown(
        f"### Welcome, {user['full_name']} 👋"
    )

    st.caption(
        "Manage biomedical waste records, monitor AI analysis "
        "and request waste collection."
    )

    hospital_id = user.get("hospital_id")

    if hospital_id is None:
        st.error(
            "Your account is not assigned to a hospital. "
            "Please contact the administrator."
        )
        return

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

        requests = conn.execute(
            """
            SELECT COUNT(*)
            FROM collection_requests cr
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            WHERE w.hospital_id = ?
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

        records = conn.execute(
            """
            SELECT
                waste_id,
                colour_category,
                waste_weight,
                ai_suggested_category,
                ai_confidence,
                verification_status,
                collection_status,
                created_at
            FROM waste_records
            WHERE hospital_id = ?
            ORDER BY waste_id DESC
            LIMIT 10
            """,
            (hospital_id,)
        ).fetchall()

        eligible = conn.execute(
            """
            SELECT
                w.waste_id,
                w.colour_category,
                w.waste_weight,
                w.ai_suggested_category,
                w.ai_confidence,
                w.ai_explanation
            FROM waste_records w
            WHERE w.hospital_id = ?
              AND w.verification_status = 'Approved'
              AND NOT EXISTS (
                  SELECT 1
                  FROM collection_requests cr
                  WHERE cr.waste_id = w.waste_id
              )
            ORDER BY w.waste_id DESC
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
    # HOSPITAL OVERVIEW
    # =========================================

    st.subheader(f"🏥 {hospital_name}")

    st.caption(
        "Hospital-wise biomedical waste management overview."
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

    c4, c5 = st.columns(2)

    c4.metric(
        "Collection Requests",
        requests,
        border=True
    )

    c5.metric(
        "Ready for Collection",
        len(eligible),
        border=True
    )

    st.divider()

    # =========================================
    # MAIN TABS
    # =========================================

    tab1, tab2 = st.tabs(
        [
            "📋 Waste Records",
            "🚚 Request Collection"
        ]
    )

    # =========================================
    # TAB 1: WASTE RECORDS
    # =========================================

    with tab1:

        st.subheader("Recent Waste Records")

        st.caption(
            "View the latest registered waste records "
            "and their verification status."
        )

        if records:

            st.dataframe(
                [dict(row) for row in records],
                width="stretch",
                hide_index=True
            )

            st.divider()

            st.subheader("🤖 AI Analysis Details")

            record_ids = [
                row["waste_id"]
                for row in records
            ]

            selected_record_id = st.selectbox(
                "Select Waste Record",
                record_ids,
                format_func=lambda value: f"Waste Record #{value}",
                key="nurse_record"
            )

            conn = get_connection()

            try:

                selected_record = conn.execute(
                    """
                    SELECT
                        waste_id,
                        colour_category,
                        ai_suggested_category,
                        ai_confidence,
                        ai_explanation,
                        verification_status
                    FROM waste_records
                    WHERE waste_id = ?
                      AND hospital_id = ?
                    """,
                    (
                        selected_record_id,
                        hospital_id
                    )
                ).fetchone()

            finally:
                conn.close()

            if selected_record:

                with st.container(border=True):

                    st.markdown(
                        f"**Waste Record #{selected_record['waste_id']}**"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        st.write(
                            "**Registered Category:**",
                            selected_record["colour_category"]
                        )

                        st.write(
                            "**AI Suggested Category:**",
                            selected_record["ai_suggested_category"]
                            or "Not available"
                        )

                    with col2:

                        st.write(
                            "**AI Confidence:**",
                            selected_record["ai_confidence"]
                            or "Not available"
                        )

                        st.write(
                            "**Verification Status:**",
                            selected_record["verification_status"]
                        )

                    st.markdown("**AI Explanation**")

                    st.info(
                        selected_record["ai_explanation"]
                        or "No AI explanation available."
                    )

                    ai_category = selected_record[
                        "ai_suggested_category"
                    ]

                    registered_category = selected_record[
                        "colour_category"
                    ]

                    valid_categories = [
                        "yellow",
                        "red",
                        "white",
                        "blue"
                    ]

                    if (
                        ai_category
                        and registered_category
                        and str(ai_category).strip().lower()
                        in valid_categories
                        and str(registered_category).strip().lower()
                        in valid_categories
                    ):

                        if (
                            str(ai_category).strip().lower()
                            != str(registered_category).strip().lower()
                        ):

                            st.warning(
                                "AI suggestion differs from the "
                                "registered category. Please refer "
                                "the record for human review."
                            )

                        else:

                            st.success(
                                "AI suggestion and registered "
                                "category match."
                            )

                    st.caption(
                        "AI results are suggestions only. "
                        "They do not replace qualified human verification."
                    )

        else:

            st.info(
                "No waste records are available for this hospital."
            )

    # =========================================
    # TAB 2: REQUEST COLLECTION
    # =========================================

    with tab2:

        st.subheader("Request Waste Collection")

        st.caption(
            "Submit a collection request for approved waste records."
        )

        st.metric(
            "Approved Records Available",
            len(eligible),
            border=True
        )

        if not eligible:

            st.info(
                "No approved waste records are currently available "
                "for a new collection request."
            )

        else:

            selected_id = st.selectbox(
                "Select Approved Waste Record",
                [
                    row["waste_id"]
                    for row in eligible
                ],
                format_func=lambda value: f"Waste Record #{value}",
                key="collection_record"
            )

            selected_waste = next(
                row for row in eligible
                if row["waste_id"] == selected_id
            )

            st.divider()

            st.markdown("### Selected Waste Information")

            with st.container(border=True):

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Waste ID:**",
                        selected_waste["waste_id"]
                    )

                    st.write(
                        "**Registered Category:**",
                        selected_waste["colour_category"]
                    )

                    st.write(
                        "**Weight:**",
                        f"{selected_waste['waste_weight']} kg"
                    )

                with col2:

                    st.write(
                        "**AI Suggested Category:**",
                        selected_waste["ai_suggested_category"]
                        or "Not available"
                    )

                    st.write(
                        "**AI Confidence:**",
                        selected_waste["ai_confidence"]
                        or "Not available"
                    )

                st.markdown("**AI Explanation**")

                st.info(
                    selected_waste["ai_explanation"]
                    or "No AI explanation available."
                )

            st.warning(
                "Collection requests are available only after "
                "human verification and approval."
            )

            if st.button(
                "Submit Collection Request",
                type="primary",
                use_container_width=True
            ):

                conn = get_connection()

                try:

                    # Recheck eligibility before creating request

                    current_record = conn.execute(
                        """
                        SELECT waste_id
                        FROM waste_records
                        WHERE waste_id = ?
                          AND hospital_id = ?
                          AND verification_status = 'Approved'
                          AND NOT EXISTS (
                              SELECT 1
                              FROM collection_requests
                              WHERE collection_requests.waste_id =
                                    waste_records.waste_id
                          )
                        """,
                        (
                            selected_id,
                            hospital_id
                        )
                    ).fetchone()

                    if not current_record:

                        conn.rollback()

                        st.warning(
                            "This record is no longer available "
                            "for a new collection request. "
                            "Please refresh the page."
                        )

                    else:

                        conn.execute(
                            """
                            INSERT INTO collection_requests
                            (waste_id, requested_by)
                            VALUES (?, ?)
                            """,
                            (
                                selected_id,
                                user["user_id"]
                            )
                        )

                        conn.execute(
                            """
                            UPDATE waste_records
                            SET collection_status = 'Requested'
                            WHERE waste_id = ?
                              AND hospital_id = ?
                            """,
                            (
                                selected_id,
                                hospital_id
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
                                "Collection Requested",
                                f"Waste ID {selected_id}"
                            )
                        )

                        conn.commit()

                        st.success(
                            f"Collection request submitted "
                            f"successfully for Waste Record #{selected_id}."
                        )

                        st.rerun()

                except Exception as error:

                    conn.rollback()

                    st.error(
                        f"Unable to submit collection request: {error}"
                    )

                finally:
                    conn.close()

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Healthcare Staff Portal"
    )