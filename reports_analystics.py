import streamlit as st
import pandas as pd
import numpy as np
from database import get_connection


def reports_analytics_page(user):

    st.title("Reports & Analytics")
    st.caption("MED WASTE AI | Complete Analytics Dashboard")

    conn = get_connection()

    try:
        # -----------------------------------------
        # DATE FILTER
        # -----------------------------------------

        date_range = conn.execute(
            """
            SELECT
                MIN(date(created_at)) AS first_date,
                MAX(date(created_at)) AS last_date
            FROM waste_records
            """
        ).fetchone()

        # -----------------------------------------
        # FILTER OPTIONS
        # -----------------------------------------

        hospitals = conn.execute(
            """
            SELECT hospital_id, hospital_name
            FROM hospitals
            ORDER BY hospital_name
            """
        ).fetchall()

        hospital_options = {
            "All Hospitals": None
        }

        for hospital in hospitals:
            hospital_options[hospital["hospital_name"]] = (
                hospital["hospital_id"]
            )

        # -----------------------------------------
        # FILTER UI
        # -----------------------------------------

        st.subheader("Analytics Filters")

        f1, f2 = st.columns(2)

        with f1:
            selected_hospital = st.selectbox(
                "Select Hospital",
                list(hospital_options.keys())
            )

        with f2:
            if date_range["first_date"] and date_range["last_date"]:
                selected_dates = st.date_input(
                    "Select Date Range",
                    value=(
                        pd.to_datetime(
                            date_range["first_date"]
                        ).date(),
                        pd.to_datetime(
                            date_range["last_date"]
                        ).date()
                    )
                )
            else:
                selected_dates = ()

        hospital_id = hospital_options[selected_hospital]

        if (
            isinstance(selected_dates, (tuple, list))
            and len(selected_dates) == 2
        ):
            start_date, end_date = selected_dates
        else:
            start_date = None
            end_date = None

        # Build safe SQL filters
        conditions = []
        params = []

        if hospital_id is not None:
            conditions.append("w.hospital_id = ?")
            params.append(hospital_id)

        if start_date and end_date:
            conditions.append(
                "date(w.created_at) BETWEEN ? AND ?"
            )
            params.extend([
                start_date.isoformat(),
                end_date.isoformat()
            ])

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        # -----------------------------------------
        # WASTE RECORDS
        # -----------------------------------------

        records = conn.execute(
            f"""
            SELECT
                w.waste_id,
                h.hospital_name,
                w.hospital_id,
                w.waste_weight,
                w.colour_category,
                w.waste_materials,
                w.verification_status,
                w.collection_status,
                w.created_at,
                w.ai_suggested_category,
                w.ai_confidence,
                w.ai_explanation,
                w.image_path
            FROM waste_records w
            LEFT JOIN hospitals h
                ON w.hospital_id = h.hospital_id
            {where_clause}
            ORDER BY w.waste_id DESC
            """,
            params
        ).fetchall()

        report_df = pd.DataFrame(
            [dict(row) for row in records]
        )

        # -----------------------------------------
        # COLLECTION REQUESTS
        # -----------------------------------------

        collection_conditions = []
        collection_params = []

        if hospital_id is not None:
            collection_conditions.append(
                "w.hospital_id = ?"
            )
            collection_params.append(hospital_id)

        if start_date and end_date:
            collection_conditions.append(
                "date(w.created_at) BETWEEN ? AND ?"
            )
            collection_params.extend([
                start_date.isoformat(),
                end_date.isoformat()
            ])

        collection_where = (
            "WHERE " + " AND ".join(collection_conditions)
            if collection_conditions else ""
        )

        collection_data = conn.execute(
            f"""
            SELECT
                cr.request_id,
                cr.waste_id,
                cr.status,
                cr.assigned_driver,
                cr.driver_response,
                cr.requested_at,
                cr.updated_at,
                w.hospital_id,
                w.waste_weight,
                w.colour_category,
                h.hospital_name,
                u.full_name AS driver_name
            FROM collection_requests cr
            JOIN waste_records w
                ON cr.waste_id = w.waste_id
            LEFT JOIN hospitals h
                ON w.hospital_id = h.hospital_id
            LEFT JOIN users u
                ON cr.assigned_driver = u.user_id
            {collection_where}
            ORDER BY cr.request_id DESC
            """,
            collection_params
        ).fetchall()

        collection_df = pd.DataFrame(
            [dict(row) for row in collection_data]
        )

        # -----------------------------------------
        # HOSPITAL-WISE ANALYTICS
        # -----------------------------------------

        hospital_conditions = []
        hospital_params = []

        if hospital_id is not None:
            hospital_conditions.append(
                "w.hospital_id = ?"
            )
            hospital_params.append(hospital_id)

        if start_date and end_date:
            hospital_conditions.append(
                "date(w.created_at) BETWEEN ? AND ?"
            )
            hospital_params.extend([
                start_date.isoformat(),
                end_date.isoformat()
            ])

        hospital_data = conn.execute(
            f"""
            SELECT
                h.hospital_name,
                COUNT(w.waste_id) AS total_records,
                COALESCE(SUM(w.waste_weight), 0) AS total_weight
            FROM hospitals h
            LEFT JOIN waste_records w
                ON h.hospital_id = w.hospital_id
                {
                    "AND " + " AND ".join(hospital_conditions)
                    if hospital_conditions else ""
                }
            GROUP BY h.hospital_id, h.hospital_name
            ORDER BY total_weight DESC
            """,
            hospital_params
        ).fetchall()

        hospital_df = pd.DataFrame(
            [dict(row) for row in hospital_data]
        )

        # -----------------------------------------
        # CATEGORY ANALYTICS
        # -----------------------------------------

        category_data = conn.execute(
            f"""
            SELECT
                w.colour_category,
                COUNT(*) AS total_records,
                COALESCE(SUM(w.waste_weight), 0) AS total_weight
            FROM waste_records w
            {where_clause}
            GROUP BY w.colour_category
            ORDER BY total_records DESC
            """,
            params
        ).fetchall()

        category_df = pd.DataFrame(
            [dict(row) for row in category_data]
        )

        # -----------------------------------------
        # MONTHLY WASTE GENERATION
        # -----------------------------------------

        monthly_data = conn.execute(
            f"""
            SELECT
                strftime('%Y-%m', w.created_at) AS month,
                COUNT(*) AS total_records,
                COALESCE(SUM(w.waste_weight), 0) AS total_weight
            FROM waste_records w
            {where_clause}
            GROUP BY strftime('%Y-%m', w.created_at)
            ORDER BY month
            """,
            params
        ).fetchall()

        monthly_df = pd.DataFrame(
            [dict(row) for row in monthly_data]
        )

        # -----------------------------------------
        # DRIVER PERFORMANCE
        # -----------------------------------------

        driver_data = conn.execute(
            f"""
            SELECT
                u.full_name AS driver_name,
                COUNT(cr.request_id) AS assigned,
                SUM(
                    CASE WHEN cr.driver_response = 'Accepted'
                    THEN 1 ELSE 0 END
                ) AS accepted,
                SUM(
                    CASE WHEN cr.driver_response = 'Rejected'
                    THEN 1 ELSE 0 END
                ) AS rejected,
                SUM(
                    CASE WHEN cr.status = 'Completed'
                    THEN 1 ELSE 0 END
                ) AS completed
            FROM users u
            LEFT JOIN collection_requests cr
                ON u.user_id = cr.assigned_driver
            LEFT JOIN waste_records w
                ON cr.waste_id = w.waste_id
            WHERE u.role = 'driver'
            {"AND w.hospital_id = ?" if hospital_id is not None else ""}
            {
                "AND date(w.created_at) BETWEEN ? AND ?"
                if start_date and end_date else ""
            }
            GROUP BY u.user_id, u.full_name
            ORDER BY completed DESC
            """,
            (
                ([hospital_id] if hospital_id is not None else [])
                + (
                    [
                        start_date.isoformat(),
                        end_date.isoformat()
                    ]
                    if start_date and end_date else []
                )
            )
        ).fetchall()

        driver_df = pd.DataFrame(
            [dict(row) for row in driver_data]
        )

    finally:
        conn.close()

    # -----------------------------------------
    # SUMMARY METRICS
    # -----------------------------------------

    st.divider()
    st.subheader("Waste Management Summary")

    total_waste = len(report_df)

    total_weight = (
        pd.to_numeric(
            report_df["waste_weight"],
            errors="coerce"
        ).fillna(0).sum()
        if not report_df.empty else 0
    )

    pending = (
        (report_df["verification_status"] == "Pending").sum()
        if not report_df.empty else 0
    )

    approved = (
        (report_df["verification_status"] == "Approved").sum()
        if not report_df.empty else 0
    )

    rejected = (
        (report_df["verification_status"] == "Rejected").sum()
        if not report_df.empty else 0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Waste Records", total_waste)
    c2.metric("Total Waste Weight", f"{total_weight:.2f} kg")
    c3.metric("Pending Verification", int(pending))

    c4, c5 = st.columns(2)

    c4.metric("Approved Records", int(approved))
    c5.metric("Rejected Records", int(rejected))

    # -----------------------------------------
    # COLLECTION COMPLETION
    # -----------------------------------------

    st.divider()
    st.subheader("Collection Completion Analysis")

    if not collection_df.empty:

        eligible = collection_df[
            ~collection_df["status"].isin(["Cancelled"])
        ]

        completed_count = (
            eligible["status"] == "Completed"
        ).sum()

        total_eligible = len(eligible)

        completion_percentage = (
            completed_count / total_eligible * 100
            if total_eligible > 0 else 0
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "Total Eligible Requests",
            total_eligible
        )

        m2.metric(
            "Completed Collections",
            int(completed_count)
        )

        m3.metric(
            "Completion Percentage",
            f"{completion_percentage:.1f}%"
        )

        st.progress(completion_percentage / 100)

    else:
        st.info("No collection data available.")

    # -----------------------------------------
    # HOSPITAL-WISE WASTE GENERATION
    # -----------------------------------------

    st.divider()
    st.subheader("Hospital-wise Waste Generation")

    if not hospital_df.empty:

        st.bar_chart(
            hospital_df.set_index("hospital_name")[
                "total_weight"
            ]
        )

        st.dataframe(
            hospital_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No hospital data available.")

    # -----------------------------------------
    # WASTE CATEGORY DISTRIBUTION
    # -----------------------------------------

    st.divider()
    st.subheader("Waste Category Distribution")

    if not category_df.empty:

        chart_tab1, chart_tab2 = st.tabs(
            ["Record Count", "Waste Weight"]
        )

        with chart_tab1:
            st.bar_chart(
                category_df.set_index("colour_category")[
                    "total_records"
                ]
            )

        with chart_tab2:
            st.bar_chart(
                category_df.set_index("colour_category")[
                    "total_weight"
                ]
            )

        st.dataframe(
            category_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No category data available.")

    # -----------------------------------------
    # MONTHLY WASTE GENERATION TRENDS
    # -----------------------------------------

    st.divider()
    st.subheader("Monthly Waste Generation Trends")

    if not monthly_df.empty:

        monthly_df["month"] = pd.to_datetime(
            monthly_df["month"],
            errors="coerce"
        )

        monthly_df = monthly_df.dropna(
            subset=["month"]
        )

        if not monthly_df.empty:

            monthly_df["Month"] = (
                monthly_df["month"].dt.strftime("%b %Y")
            )

            st.line_chart(
                monthly_df.set_index("Month")[
                    ["total_weight"]
                ]
            )

            st.dataframe(
                monthly_df[
                    ["Month", "total_records", "total_weight"]
                ],
                use_container_width=True,
                hide_index=True
            )

    else:
        st.info("No monthly data available.")

    # -----------------------------------------
    # WASTE GENERATION PREDICTION
    # -----------------------------------------

    st.divider()
    st.subheader("🔮 Waste Generation Prediction Dashboard")

    st.caption(
        "Estimates future monthly waste generation "
        "using historical waste records."
    )

    if not monthly_df.empty:

        prediction_df = monthly_df.copy()

        prediction_df["month"] = pd.to_datetime(
            prediction_df["month"],
            errors="coerce"
        )

        prediction_df = prediction_df.dropna(
            subset=["month"]
        ).sort_values("month")

        prediction_df["total_weight"] = pd.to_numeric(
            prediction_df["total_weight"],
            errors="coerce"
        )

        prediction_df = prediction_df.dropna(
            subset=["total_weight"]
        )

        if len(prediction_df) >= 3:

            # Prepare historical data
            x = np.arange(len(prediction_df))

            y = prediction_df[
                "total_weight"
            ].to_numpy(dtype=float)

            # Linear regression
            slope, intercept = np.polyfit(x, y, 1)

            # Predict next 3 months
            future_x = np.arange(
                len(prediction_df),
                len(prediction_df) + 3
            )

            predicted_weights = (
                slope * future_x + intercept
            )

            predicted_weights = np.maximum(
                predicted_weights,
                0
            )

            # Future month dates
            last_month = prediction_df["month"].max()

            future_months = pd.date_range(
                start=last_month + pd.offsets.MonthBegin(1),
                periods=3,
                freq="MS"
            )

            future_df = pd.DataFrame({
                "Month": future_months.strftime("%b %Y"),
                "Predicted Weight (kg)": (
                    predicted_weights.round(2)
                )
            })

            # Prediction metrics
            p1, p2, p3 = st.columns(3)

            p1.metric(
                "Average Monthly Waste",
                f"{np.mean(y):.2f} kg"
            )

            p2.metric(
                "Next Month Prediction",
                f"{predicted_weights[0]:.2f} kg"
            )

            p3.metric(
                "Three-Month Total Prediction",
                f"{predicted_weights.sum():.2f} kg"
            )

            st.success(
                "Prediction generated successfully "
                "using historical waste records."
            )

            # Future prediction table
            st.subheader(
                "Future Waste Generation Estimates"
            )

            st.dataframe(
                future_df,
                use_container_width=True,
                hide_index=True
            )

            # Historical and predicted data
            historical_plot = pd.DataFrame({
                "Month": prediction_df[
                    "month"
                ].dt.strftime("%b %Y"),
                "Historical Waste": y,
                "Predicted Waste": np.nan
            })

            future_plot = pd.DataFrame({
                "Month": future_months.strftime("%b %Y"),
                "Historical Waste": np.nan,
                "Predicted Waste": predicted_weights
            })

            combined_plot = pd.concat(
                [historical_plot, future_plot],
                ignore_index=True
            )

            st.subheader(
                "Historical vs Predicted Waste Generation"
            )

            st.line_chart(
                combined_plot.set_index("Month")
            )

            # Download prediction report
            prediction_csv = future_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                label="Download Prediction Report (CSV)",
                data=prediction_csv,
                file_name="med_waste_prediction.csv",
                mime="text/csv"
            )

            st.info(
                "These are indicative estimates based on "
                "a linear trend in historical monthly records. "
                "They are not guaranteed future quantities. "
                "More historical data can improve the usefulness "
                "of the estimates."
            )

        else:

            st.warning(
                "At least 3 months of historical waste records "
                "are required to generate predictions. "
                "Add more monthly records and try again."
            )

    else:

        st.info(
            "No historical monthly waste data is available "
            "for prediction."
        )
# -----------------------------------------
    # AI WASTE CLASSIFICATION ANALYTICS
    # -----------------------------------------

    st.divider()
    st.subheader("🤖 AI Waste Classification Dashboard")

    st.caption(
        "Analysis of Gemini AI image classification results "
        "and doctor verification decisions."
    )

    if not report_df.empty and "ai_suggested_category" in report_df.columns:

        # Records with a saved AI prediction
        ai_df = report_df[
            report_df["ai_suggested_category"].notna()
            & (report_df["ai_suggested_category"].astype(str).str.strip() != "")
        ].copy()

        if not ai_df.empty:

            # ---------------------------------
            # AI SUMMARY METRICS
            # ---------------------------------

            total_analysed = len(ai_df)

            uncertain_count = (
                ai_df["ai_suggested_category"]
                .astype(str)
                .str.lower()
                .eq("uncertain")
                .sum()
            )

            confident_count = total_analysed - uncertain_count

            high_confidence = (
                ai_df["ai_confidence"]
                .astype(str)
                .str.lower()
                .eq("high")
                .sum()
            )

            medium_confidence = (
                ai_df["ai_confidence"]
                .astype(str)
                .str.lower()
                .eq("medium")
                .sum()
            )

            low_confidence = (
                ai_df["ai_confidence"]
                .astype(str)
                .str.lower()
                .eq("low")
                .sum()
            )

            a1, a2, a3 = st.columns(3)

            a1.metric("AI-Analysed Records", total_analysed)
            a2.metric("Uncertain Predictions", int(uncertain_count))
            a3.metric("Categorised Predictions", int(confident_count))

            a4, a5, a6 = st.columns(3)

            a4.metric("High Confidence", int(high_confidence))
            a5.metric("Medium Confidence", int(medium_confidence))
            a6.metric("Low Confidence", int(low_confidence))

            # ---------------------------------
            # AI CATEGORY DISTRIBUTION
            # ---------------------------------

            st.subheader("AI Predicted Category Distribution")

            ai_category_df = (
                ai_df.groupby("ai_suggested_category")
                .size()
                .reset_index(name="total_predictions")
                .sort_values("total_predictions", ascending=False)
            )

            st.bar_chart(
                ai_category_df.set_index("ai_suggested_category")
            )

            st.dataframe(
                ai_category_df,
                use_container_width=True,
                hide_index=True
            )

            # ---------------------------------
            # AI CONFIDENCE DISTRIBUTION
            # ---------------------------------

            st.subheader("AI Confidence Level Analysis")

            confidence_order = ["High", "Medium", "Low", "Not provided"]

            ai_df["Confidence Level"] = (
                ai_df["ai_confidence"]
                .fillna("Not provided")
                .astype(str)
                .str.title()
            )

            ai_df.loc[
                ~ai_df["Confidence Level"].isin(
                    ["High", "Medium", "Low"]
                ),
                "Confidence Level"
            ] = "Not provided"

            confidence_df = (
                ai_df["Confidence Level"]
                .value_counts()
                .reindex(confidence_order, fill_value=0)
                .reset_index()
            )

            confidence_df.columns = [
                "Confidence Level",
                "Total Records"
            ]

            st.bar_chart(
                confidence_df.set_index("Confidence Level")
            )

            st.dataframe(
                confidence_df,
                use_container_width=True,
                hide_index=True
            )

            # ---------------------------------
            # AI VS REGISTRATION CATEGORY
            # ---------------------------------

            st.subheader(
                "AI Prediction vs Registered Category"
            )

            comparison_df = ai_df[
                ai_df["ai_suggested_category"]
                .astype(str).str.lower().isin(
                    ["yellow", "red", "white", "blue"]
                )
                & ai_df["colour_category"]
                .astype(str).str.lower().isin(
                    ["yellow", "red", "white", "blue"]
                )
            ].copy()

            if not comparison_df.empty:

                comparison_df["AI Agreement"] = (
                    comparison_df["ai_suggested_category"]
                    .astype(str).str.lower()
                    ==
                    comparison_df["colour_category"]
                    .astype(str).str.lower()
                )

                agreement_count = int(
                    comparison_df["AI Agreement"].sum()
                )

                comparison_count = len(comparison_df)

                agreement_percentage = (
                    agreement_count / comparison_count * 100
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Compared Records",
                    comparison_count
                )

                c2.metric(
                    "Matching Categories",
                    agreement_count
                )

                c3.metric(
                    "AI–Registration Agreement",
                    f"{agreement_percentage:.1f}%"
                )

                st.progress(agreement_percentage / 100)

                agreement_summary = (
                    comparison_df.groupby("AI Agreement")
                    .size()
                    .reset_index(name="Total Records")
                )

                agreement_summary["Comparison Result"] = (
                    agreement_summary["AI Agreement"]
                    .map({
                        True: "Matching",
                        False: "Different"
                    })
                )

                st.dataframe(
                    agreement_summary[
                        ["Comparison Result", "Total Records"]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "This measures agreement with the category "
                    "selected during registration. It is not a "
                    "verified AI accuracy score."
                )

            else:
                st.info(
                    "No comparable AI and registration categories "
                    "are available."
                )

            # ---------------------------------
            # AI PREDICTION VS DOCTOR VERIFICATION
            # ---------------------------------

            st.subheader(
                "AI Predictions vs Doctor Verification"
            )

            verification_df = (
                ai_df.groupby(
                    ["ai_suggested_category", "verification_status"],
                    dropna=False
                )
                .size()
                .reset_index(name="total_records")
            )

            if not verification_df.empty:

                st.bar_chart(
                    verification_df.pivot_table(
                        index="ai_suggested_category",
                        columns="verification_status",
                        values="total_records",
                        aggfunc="sum",
                        fill_value=0
                    )
                )

                st.dataframe(
                    verification_df,
                    use_container_width=True,
                    hide_index=True
                )

            # ---------------------------------
            # AI CLASSIFICATION REPORT
            # ---------------------------------

            st.subheader("Complete AI Classification Report")

            ai_display_df = ai_df[
                [
                    "waste_id",
                    "hospital_name",
                    "ai_suggested_category",
                    "colour_category",
                    "ai_confidence",
                    "verification_status",
                    "created_at"
                ]
            ].copy()

            ai_display_df = ai_display_df.rename(
                columns={
                    "waste_id": "Waste ID",
                    "hospital_name": "Hospital",
                    "ai_suggested_category": "AI Predicted Category",
                    "colour_category": "Registered Category",
                    "ai_confidence": "AI Confidence",
                    "verification_status": "Doctor Verification",
                    "created_at": "Created At"
                }
            )

            st.dataframe(
                ai_display_df,
                use_container_width=True,
                hide_index=True
            )

            ai_csv = ai_display_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                label="Download AI Classification Report (CSV)",
                data=ai_csv,
                file_name="med_waste_ai_classification_report.csv",
                mime="text/csv"
            )

            st.info(
                "Gemini AI provides suggestions to support waste "
                "classification. A qualified human reviewer must "
                "verify every biomedical waste classification. "
                "Confidence levels are model-reported labels, not "
                "calibrated probabilities."
            )

        else:

            st.info(
                "No successful AI image classification records "
                "are available for the selected filters."
            )

    else:

        st.info(
            "No waste records are available for AI analytics."
        )
    # -----------------------------------------
    # DRIVER PERFORMANCE
    # -----------------------------------------

    st.divider()
    st.subheader("Driver Performance Analytics")

    if not driver_df.empty:

        st.bar_chart(
            driver_df.set_index("driver_name")[
                ["assigned", "accepted", "rejected", "completed"]
            ]
        )

        st.dataframe(
            driver_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No driver performance data available.")

    # -----------------------------------------
    # COMPLETE WASTE RECORDS
    # -----------------------------------------

    st.divider()
    st.subheader("Complete Waste Records")

    if not report_df.empty:

        display_df = report_df.drop(
            columns=["hospital_id"],
            errors="ignore"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = display_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download Waste Report (CSV)",
            data=csv_data,
            file_name="med_waste_report.csv",
            mime="text/csv"
        )

    else:
        st.info("No waste records available for download.")

    # -----------------------------------------
    # COLLECTION REPORT DOWNLOAD
    # -----------------------------------------

    st.divider()
    st.subheader("Download Collection Report")

    if not collection_df.empty:

        collection_csv = collection_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download Collection Report (CSV)",
            data=collection_csv,
            file_name="med_waste_collection_report.csv",
            mime="text/csv"
        )

    else:
        st.info("No collection records available.")

    st.caption("MED WASTE AI | Reports & Analytics")