import streamlit as st
import uuid
from pathlib import Path
from io import BytesIO
from PIL import Image

from database import get_connection
from qr_utils import generate_qr_for_waste, get_qr_record
from gemini_classifier import classify_waste_image
from notification import create_notification


BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads" / "waste_images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def waste_management_page(user):

    # =========================================
    # HEALTHCARE UI STYLING
    # =========================================

    st.markdown("""
    <style>
    .waste-header {
        background: linear-gradient(120deg, #087f8c, #13a89e);
        padding: 26px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
    }

    .waste-header h2 {
        color: white;
        font-size: 27px;
        margin: 0;
    }

    .waste-header p {
        color: #e7ffff;
        margin-top: 8px;
        margin-bottom: 0;
    }

    .section-heading {
        font-size: 20px;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 12px;
    }

    .waste-card {
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

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================================
    # HEADER
    # =========================================

    st.markdown("""
    <div class="waste-header">
        <h2>♻️ Biomedical Waste Management</h2>
        <p>Register, classify and monitor biomedical waste
        using AI-powered waste management.</p>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        f"Welcome, {user['full_name']}! "
        "Manage biomedical waste records for your hospital."
    )

    # =========================================
    # TABS
    # =========================================

    register_tab, view_tab = st.tabs(
        ["➕ Register Waste", "📋 View Waste Records"]
    )

    # =========================================
    # REGISTER WASTE
    # =========================================

    with register_tab:

        st.markdown(
            '<div class="section-heading">Register New Waste</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "Enter waste details and optionally upload an image "
            "for Gemini AI classification."
        )

        with st.form("waste_registration_form"):

            st.markdown("#### ⚖️ Waste Information")

            col1, col2 = st.columns(2)

            with col1:

                waste_weight = st.number_input(
                    "Waste Weight (kg)",
                    min_value=0.1,
                    step=0.1
                )

                colour_category = st.selectbox(
                    "Waste Colour Category",
                    ["Yellow", "Red", "White", "Blue"]
                )

            with col2:

                facility_type = st.selectbox(
                    "Facility Type",
                    ["Hospital", "Clinic", "Laboratory", "Other"]
                )

                waste_materials = st.text_area(
                    "Waste Materials Description",
                    placeholder="Describe the biomedical waste materials..."
                )

            st.divider()

            st.markdown("#### 🏥 Facility Information")

            col3, col4 = st.columns(2)

            with col3:

                facility_name = st.text_input(
                    "Facility Name",
                    placeholder="Enter facility name"
                )

            with col4:

                facility_location = st.text_input(
                    "Facility Location",
                    placeholder="Enter facility location"
                )

            st.divider()

            st.markdown("#### 📷 Waste Image Upload")

            uploaded_image = st.file_uploader(
                "Upload Waste Image (Optional)",
                type=["jpg", "jpeg", "png"],
                key="waste_image"
            )

            if uploaded_image is not None:

                st.image(
                    uploaded_image,
                    caption="Uploaded Waste Image",
                    width=250
                )

                st.caption("Maximum image size: 5 MB")

            submitted = st.form_submit_button(
                "Register Waste",
                use_container_width=True
            )

        # =====================================
        # FORM VALIDATION
        # =====================================

        if submitted:

            if not waste_materials.strip():

                st.error(
                    "Please enter the waste materials description."
                )

            elif not facility_name.strip():

                st.error("Please enter the facility name.")

            elif not facility_location.strip():

                st.error("Please enter the facility location.")

            elif user.get("hospital_id") is None:

                st.error(
                    "Your account is not assigned to a hospital."
                )

            else:

                image_path = None
                ai_category = None
                ai_explanation = None
                ai_confidence = None

                try:

                    # =================================
                    # GEMINI AI IMAGE ANALYSIS
                    # =================================

                    if uploaded_image is not None:

                        image_bytes = uploaded_image.getvalue()

                        if len(image_bytes) > 5 * 1024 * 1024:

                            raise ValueError(
                                "Image size must be below 5 MB."
                            )

                        mime_type = uploaded_image.type

                        st.divider()

                        st.markdown(
                            "#### 🤖 Gemini AI Image Analysis"
                        )

                        with st.spinner(
                            "Gemini AI is analysing the uploaded image..."
                        ):

                            ai_result = classify_waste_image(
                                image_bytes,
                                mime_type
                            )

                        if ai_result["success"]:

                            ai_category = ai_result["category"]
                            ai_explanation = ai_result["explanation"]
                            ai_confidence = ai_result.get("confidence")

                            st.success(
                                "Gemini AI analysis completed successfully!"
                            )

                            col1, col2 = st.columns(2)

                            col1.metric(
                                "AI Suggested Category",
                                ai_category or "Uncertain"
                            )

                            col2.metric(
                                "AI Confidence",
                                ai_confidence or "Not available"
                            )

                            st.markdown(
                                '<div class="waste-card">',
                                unsafe_allow_html=True
                            )

                            st.markdown("**AI Explanation**")

                            st.write(ai_explanation)

                            st.markdown("</div>", unsafe_allow_html=True)

                            st.warning(
                                "AI classification is only a suggestion. "
                                "A qualified human reviewer must verify "
                                "the waste category."
                            )

                        else:

                            st.warning(
                                "Gemini AI analysis failed: "
                                + str(
                                    ai_result.get(
                                        "explanation",
                                        "Unknown error"
                                    )
                                )
                            )

                    # =================================
                    # SAVE UPLOADED IMAGE
                    # =================================

                    if uploaded_image is not None:

                        image_bytes = uploaded_image.getvalue()

                        image = Image.open(
                            BytesIO(image_bytes)
                        )

                        image.verify()

                        image = Image.open(
                            BytesIO(image_bytes)
                        ).convert("RGB")

                        filename = f"{uuid.uuid4().hex}.jpg"

                        full_image_path = UPLOAD_DIR / filename

                        image.save(
                            full_image_path,
                            format="JPEG"
                        )

                        image_path = str(
                            Path("uploads") /
                            "waste_images" /
                            filename
                        )

                    # =================================
                    # SAVE WASTE RECORD
                    # =================================

                    st.divider()

                    with st.spinner(
                        "Saving waste record..."
                    ):

                        conn = get_connection()

                        try:

                            cursor = conn.execute(
                                """
                                INSERT INTO waste_records (
                                    user_id,
                                    hospital_id,
                                    waste_weight,
                                    colour_category,
                                    waste_materials,
                                    facility_type,
                                    facility_name,
                                    facility_location,
                                    image_path,
                                    ai_suggested_category,
                                    ai_explanation,
                                    ai_confidence
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    user["user_id"],
                                    user["hospital_id"],
                                    waste_weight,
                                    colour_category,
                                    waste_materials.strip(),
                                    facility_type,
                                    facility_name.strip(),
                                    facility_location.strip(),
                                    image_path,
                                    ai_category,
                                    ai_explanation,
                                    ai_confidence
                                )
                            )

                            waste_id = cursor.lastrowid

                            conn.commit()

                        finally:
                            conn.close()

                    # =================================
                    # NOTIFY ACTIVE DOCTORS
                    # =================================

                    if user.get("role") == "staff":

                        doctor_conn = get_connection()

                        try:

                            doctors = doctor_conn.execute(
                                """
                                SELECT user_id
                                FROM users
                                WHERE hospital_id = ?
                                AND role = 'doctor'
                                AND is_active = 1
                                """,
                                (user["hospital_id"],)
                            ).fetchall()

                        finally:
                            doctor_conn.close()

                        notification_errors = []

                        for doctor in doctors:

                            try:

                                create_notification(
                                    doctor["user_id"],
                                    (
                                        f"New waste record #{waste_id} "
                                        "has been registered and is waiting "
                                        "for your verification."
                                    ),
                                    waste_id
                                )

                            except Exception as notification_error:

                                notification_errors.append(
                                    str(notification_error)
                                )

                        if notification_errors:

                            st.warning(
                                "Waste was registered, but one or more "
                                "doctor notifications could not be created."
                            )

                        elif doctors:

                            st.success(
                                "Notification sent to the active doctors."
                            )

                        else:

                            st.info(
                                "No active doctors were found in this hospital."
                            )

                    # =================================
                    # GENERATE QR CODE
                    # =================================

                    try:

                        qr_token, qr_code_path = generate_qr_for_waste(
                            waste_id
                        )

                        st.success(
                            f"Waste record registered successfully! "
                            f"Waste ID: {waste_id}"
                        )

                        st.markdown(
                            "#### 📱 Generated Waste QR Code"
                        )

                        qr_full_path = BASE_DIR / qr_code_path

                        if qr_full_path.exists():

                            st.image(
                                str(qr_full_path),
                                caption=f"QR Code for Waste ID: {waste_id}",
                                width=250
                            )

                            with open(qr_full_path, "rb") as qr_file:

                                qr_data = qr_file.read()

                            st.download_button(
                                "⬇️ Download QR Code",
                                data=qr_data,
                                file_name=f"waste_{waste_id}_QR.png",
                                mime="image/png"
                            )

                        else:

                            st.warning(
                                "Waste was registered, but QR image "
                                "could not be found."
                            )

                    except Exception as qr_error:

                        st.warning(
                            f"Waste was registered, but QR generation "
                            f"failed: {qr_error}"
                        )

                except Exception as error:

                    st.error(
                        f"Unable to register waste: {error}"
                    )

    # =========================================
    # VIEW WASTE RECORDS
    # =========================================

    with view_tab:

        st.markdown(
            '<div class="section-heading">📋 Registered Waste Records</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "View waste records registered under your hospital."
        )

        conn = get_connection()

        try:

            records = conn.execute(
                """
                SELECT *
                FROM waste_records
                WHERE hospital_id = ?
                ORDER BY waste_id DESC
                """,
                (user["hospital_id"],)
            ).fetchall()

        finally:
            conn.close()

        if records:

            # =================================
            # RECORD SUMMARY METRICS
            # =================================

            total_records = len(records)

            approved_count = sum(
                1 for record in records
                if record["verification_status"] == "Approved"
            )

            pending_count = sum(
                1 for record in records
                if record["verification_status"] == "Pending"
            )

            rejected_count = sum(
                1 for record in records
                if record["verification_status"] == "Rejected"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Total Records", total_records)
            col2.metric("Approved", approved_count)
            col3.metric("Pending", pending_count)
            col4.metric("Rejected", rejected_count)

            st.divider()

            # =================================
            # RECORD SEARCH
            # =================================

            search_id = st.text_input(
                "🔎 Search by Waste ID",
                placeholder="Enter Waste ID"
            )

            filtered_records = records

            if search_id.strip():

                if search_id.strip().isdigit():

                    search_value = int(search_id.strip())

                    filtered_records = [
                        record for record in records
                        if record["waste_id"] == search_value
                    ]

                else:

                    filtered_records = []

            if not filtered_records:

                st.info("No matching waste records found.")

            # =================================
            # DISPLAY RECORDS
            # =================================

            for record in filtered_records:

                with st.expander(
                    f"♻️ Waste Record #{record['waste_id']}",
                    expanded=False
                ):

                    # Waste summary
                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Waste Weight",
                        f"{record['waste_weight']} kg"
                    )

                    col2.metric(
                        "Colour Category",
                        record["colour_category"]
                    )

                    col3.metric(
                        "Verification",
                        record["verification_status"]
                    )

                    st.divider()

                    # AI analysis
                    st.markdown("#### 🤖 Gemini AI Analysis")

                    ai_col1, ai_col2 = st.columns(2)

                    with ai_col1:

                        st.write("**AI Suggested Category**")

                        st.write(
                            record["ai_suggested_category"]
                            or "Not analysed"
                        )

                        st.write("**AI Confidence**")

                        st.write(
                            record["ai_confidence"]
                            or "Not available"
                        )

                    with ai_col2:

                        st.write("**Staff Selected Category**")

                        st.write(record["colour_category"])

                        if (
                            record["ai_suggested_category"]
                            and record["ai_suggested_category"].lower()
                            != record["colour_category"].lower()
                        ):

                            st.warning(
                                "AI suggestion differs from the "
                                "staff-selected category. "
                                "Please ensure human verification."
                            )

                    st.write("**AI Explanation**")

                    st.info(
                        record["ai_explanation"]
                        or "AI explanation not available."
                    )

                    st.caption(
                        "AI classification is a suggestion only. "
                        "A qualified human reviewer must verify the result."
                    )

                    st.divider()

                    # Waste details
                    st.markdown("#### ♻️ Waste Information")

                    st.write(
                        "**Waste Materials:**",
                        record["waste_materials"]
                    )

                    st.write(
                        "**Facility Type:**",
                        record["facility_type"]
                    )

                    st.write(
                        "**Facility Name:**",
                        record["facility_name"]
                    )

                    st.write(
                        "**Facility Location:**",
                        record["facility_location"]
                    )

                    st.divider()

                    # Record status
                    st.markdown("#### 📊 Collection Information")

                    status_col1, status_col2 = st.columns(2)

                    with status_col1:

                        st.write("**Verification Status**")

                        if record["verification_status"] == "Approved":

                            st.success("Approved")

                        elif record["verification_status"] == "Rejected":

                            st.error("Rejected")

                        else:

                            st.warning(
                                record["verification_status"]
                                or "Pending"
                            )

                    with status_col2:

                        st.write("**Collection Status**")

                        if record["collection_status"] == "Completed":

                            st.success("Completed")

                        elif record["collection_status"] == "In Transit":

                            st.info("In Transit")

                        else:

                            st.warning(
                                record["collection_status"]
                                or "Not available"
                            )

                    st.divider()

                    # Uploaded image
                    st.markdown("#### 📷 Uploaded Waste Image")

                    if record["image_path"]:

                        image_full_path = BASE_DIR / record["image_path"]

                        if image_full_path.exists():

                            st.image(
                                str(image_full_path),
                                caption="Uploaded Waste Image",
                                width=250
                            )

                        else:

                            st.warning(
                                "The uploaded image file is missing."
                            )

                    else:

                        st.info(
                            "No image was uploaded for this record."
                        )

                    st.divider()

                    # QR code
                    st.markdown("#### 📱 Waste Identification QR Code")

                    qr_record = get_qr_record(record["waste_id"])

                    if qr_record:

                        qr_full_path = BASE_DIR / qr_record["qr_code_path"]

                        if qr_full_path.exists():

                            st.image(
                                str(qr_full_path),
                                caption="Waste Identification QR Code",
                                width=200
                            )

                            with open(qr_full_path, "rb") as qr_file:

                                qr_data = qr_file.read()

                            st.download_button(
                                "⬇️ Download Waste QR Code",
                                data=qr_data,
                                file_name=f"waste_{record['waste_id']}_QR.png",
                                mime="image/png",
                                key=f"download_qr_{record['waste_id']}"
                            )

                        else:

                            st.info(
                                "QR record exists, but its image file "
                                "is missing."
                            )

                    else:

                        st.info(
                            "No QR code has been generated for this record."
                        )

        else:

            st.info(
                "No waste records found for this hospital."
            )

    # =========================================
    # FOOTER
    # =========================================

    st.divider()

    st.caption(
        "MED WASTE AI | Smart Biomedical Waste Management System"
    )