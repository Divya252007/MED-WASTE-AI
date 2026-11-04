import streamlit as st
from database import get_connection
def create_notification(user_id, message, related_waste_id=None):

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO notifications (
                user_id,
                message,
                related_waste_id
            )
            VALUES (?, ?, ?)
            """,
            (user_id, message, related_waste_id)
        )

        conn.commit()

    finally:
        conn.close()

def notification_page(user):

    st.title("🔔 Notifications")
    st.write("View and manage your notifications.")

    conn = get_connection()

    try:
        notifications = conn.execute(
            """
            SELECT notification_id, message, related_waste_id,
                   is_read, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY notification_id DESC
            """,
            (user["user_id"],)
        ).fetchall()

        unread_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            """,
            (user["user_id"],)
        ).fetchone()[0]

    finally:
        conn.close()

    total_count = len(notifications)

    col1, col2 = st.columns(2)

    col1.metric("Total Notifications", total_count)
    col2.metric("Unread Notifications", unread_count)

    st.divider()

    if not notifications:
        st.info("You don't have any notifications yet.")
        return

    if st.button("Mark All as Read"):
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE notifications
                SET is_read = 1
                WHERE user_id = ?
                """,
                (user["user_id"],)
            )
            conn.commit()
            st.success("All notifications marked as read.")
        finally:
            conn.close()

        st.rerun()

    st.subheader("Your Notifications")

    for item in notifications:

        with st.container(border=True):

            col1, col2 = st.columns([4, 1])

            with col1:
                if item["is_read"] == 0:
                    st.markdown("🔵 **New Notification**")
                else:
                    st.markdown("**Notification**")

                st.write(item["message"])

                if item["related_waste_id"]:
                    st.caption(
                        f"Waste ID: {item['related_waste_id']}"
                    )

                st.caption(f"Date: {item['created_at']}")

            with col2:
                if item["is_read"] == 0:
                    if st.button(
                        "Mark Read",
                        key=f"read_{item['notification_id']}"
                    ):
                        conn = get_connection()
                        try:
                            conn.execute(
                                """
                                UPDATE notifications
                                SET is_read = 1
                                WHERE notification_id = ?
                                AND user_id = ?
                                """,
                                (
                                    item["notification_id"],
                                    user["user_id"]
                                )
                            )
                            conn.commit()
                        finally:
                            conn.close()

                        st.rerun()