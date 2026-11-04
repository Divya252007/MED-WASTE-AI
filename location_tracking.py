import streamlit as st
import folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_folium import st_folium


def location_tracking_page():

    st.title("📍 Location Tracking")

    st.write(
        "Detect your current location and view it on the map."
    )

    st.info(
        "Click the location button and allow browser permission "
        "to share your location."
    )

    location = streamlit_geolocation()

    if (
        location
        and location.get("latitude") is not None
        and location.get("longitude") is not None
    ):

        latitude = location["latitude"]
        longitude = location["longitude"]

        st.success("Location detected successfully!")

        col1, col2 = st.columns(2)

        col1.metric("Latitude", round(latitude, 6))
        col2.metric("Longitude", round(longitude, 6))

        location_map = folium.Map(
            location=[latitude, longitude],
            zoom_start=15,
            tiles="OpenStreetMap"
        )

        folium.Marker(
            [latitude, longitude],
            tooltip="Detected Location",
            popup="Your current location",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(location_map)

        st.subheader("Your Location on Map")

        st_folium(
            location_map,
            width=None,
            height=450,
            key="user_location_map"
        )

    else:

        st.warning(
            "Location not detected yet. "
            "Please press the location button and allow permission."
        )