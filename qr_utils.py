import qrcode
import secrets
from pathlib import Path
from database import get_connection


# Project folders
BASE_DIR = Path(__file__).resolve().parent

QR_DIR = BASE_DIR / "generated_qr"
QR_DIR.mkdir(parents=True, exist_ok=True)


def generate_qr_for_waste(waste_id):

    conn = get_connection()

    try:
        # Check whether QR code already exists
        existing = conn.execute(
            """
            SELECT qr_token, qr_code_path
            FROM qr_records
            WHERE waste_id = ?
            """,
            (waste_id,)
        ).fetchone()

        if existing:
            return existing["qr_token"], existing["qr_code_path"]

        # Generate unique token
        qr_token = secrets.token_urlsafe(32)

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )

        # Store only the secure token in the QR code
        qr.add_data(qr_token)
        qr.make(fit=True)

        qr_image = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        # Save QR image
        filename = f"waste_{waste_id}.png"
        file_path = QR_DIR / filename

        qr_image.save(file_path)

        relative_path = str(
            Path("generated_qr") / filename
        )

        # Save QR details in SQLite
        conn.execute(
            """
            INSERT INTO qr_records (
                waste_id,
                qr_code_path,
                qr_token
            )
            VALUES (?, ?, ?)
            """,
            (
                waste_id,
                relative_path,
                qr_token
            )
        )

        conn.commit()

        return qr_token, relative_path

    finally:
        conn.close()


def get_qr_record(waste_id):

    conn = get_connection()

    try:
        record = conn.execute(
            """
            SELECT *
            FROM qr_records
            WHERE waste_id = ?
            """,
            (waste_id,)
        ).fetchone()

        return record

    finally:
        conn.close()