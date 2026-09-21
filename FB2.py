import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    folium = None
    st_folium = None


# =========================================================
# KONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Fundbüro",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATABASE = Path("fundbuero.db")

KATEGORIEN = [
    "Handy",
    "Schlüssel",
    "Portemonnaie",
    "Tasche",
    "Kleidung",
    "Dokumente",
    "Elektronik",
    "Brille",
    "Schmuck",
    "Sonstiges",
]

STATUS = ["Gefunden", "Anfrage", "Abgeholt"]


# =========================================================
# SCHWARZ / WEISS / DUNKELBLAU DESIGN
# =========================================================

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: "Inter", sans-serif;
        }

        .stApp {
            background: #ffffff;
            color: #0b1220;
        }

        [data-testid="stHeader"] {
            background: #ffffff;
        }

        [data-testid="stSidebar"] {
            background: #0b1f3a;
            border-right: 1px solid #dbe3ee;
        }

        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }

        [data-testid="stSidebar"] .stRadio label {
            color: #ffffff !important;
        }

        .hero {
            background: #0b1f3a;
            color: #ffffff;
            padding: 34px;
            border-radius: 18px;
            margin-bottom: 24px;
            border: 1px solid #0b1f3a;
        }

        .hero h1 {
            font-size: 42px;
            font-weight: 800;
            margin: 0;
            letter-spacing: -1px;
        }

        .hero p {
            color: #dbe5f2;
            font-size: 16px;
            margin-bottom: 0;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid #d8e0ea;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 16px rgba(11, 31, 58, 0.06);
        }

        .metric-title {
            color: #526174;
            font-size: 13px;
            font-weight: 600;
        }

        .metric-number {
            color: #0b1f3a;
            font-size: 30px;
            font-weight: 800;
            margin-top: 4px;
        }

        .item-card {
            background: #ffffff;
            border: 1px solid #d8e0ea;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 16px rgba(11, 31, 58, 0.05);
        }

        .item-title {
            font-size: 20px;
            font-weight: 700;
            color: #0b1f3a;
        }

        .item-meta {
            color: #64748b;
            font-size: 13px;
        }

        .badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: #eef3f9;
            color: #0b1f3a;
            font-size: 12px;
            font-weight: 700;
            border: 1px solid #d7e0eb;
        }

        .section-title {
            color: #0b1f3a;
            font-size: 25px;
            font-weight: 800;
            margin: 24px 0 14px;
        }

        div.stButton > button {
            border-radius: 9px;
            font-weight: 600;
            border: 1px solid #0b1f3a;
        }

        div.stButton > button[kind="primary"] {
            background: #0b1f3a;
            color: #ffffff;
        }

        div.stButton > button[kind="primary"]:hover {
            background: #16355f;
            color: #ffffff;
        }

        .map-box {
            border: 1px solid #d8e0ea;
            border-radius: 16px;
            padding: 10px;
            background: #ffffff;
        }

        .info-box {
            background: #f7f9fc;
            border: 1px solid #d8e0ea;
            border-radius: 12px;
            padding: 14px;
            color: #526174;
        }

        hr {
            border-color: #d8e0ea;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATENBANK
# =========================================================

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fundstuecke (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kategorie TEXT NOT NULL,
                ort TEXT NOT NULL,
                datum TEXT NOT NULL,
                beschreibung TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Gefunden',
                latitude REAL,
                longitude REAL
            )
            """
        )

        # Alte Datenbanken aus der vorherigen Version werden automatisch
        # um die Karten-Spalten ergänzt.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(fundstuecke)"
            ).fetchall()
        }

        if "latitude" not in columns:
            connection.execute(
                "ALTER TABLE fundstuecke ADD COLUMN latitude REAL"
            )

        if "longitude" not in columns:
            connection.execute(
                "ALTER TABLE fundstuecke ADD COLUMN longitude REAL"
            )


def add_item(
    name,
    category,
    location,
    found_date,
    description,
    latitude,
    longitude,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO fundstuecke
            (
                name,
                kategorie,
                ort,
                datum,
                beschreibung,
                status,
                latitude,
                longitude
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                category,
                location.strip(),
                found_date.isoformat(),
                description.strip(),
                "Gefunden",
                latitude,
                longitude,
            ),
        )


def get_items(search="", category="Alle", status="Alle"):
    sql = """
        SELECT *
        FROM fundstuecke
        WHERE 1=1
    """

    params = []

    if search.strip():
        sql += """
            AND (
                LOWER(name) LIKE ?
                OR LOWER(ort) LIKE ?
                OR LOWER(beschreibung) LIKE ?
            )
        """

        term = f"%{search.strip().lower()}%"
        params.extend([term, term, term])

    if category != "Alle":
        sql += " AND kategorie = ?"
        params.append(category)

    if status != "Alle":
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC"

    with get_connection() as connection:
        return connection.execute(sql, params).fetchall()


def update_status(item_id, new_status):
    with get_connection() as connection:
        connection.execute(
            "UPDATE fundstuecke SET status = ? WHERE id = ?",
            (new_status, item_id),
        )


def delete_item(item_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM fundstuecke WHERE id = ?",
            (item_id,),
        )


def get_statistics():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM fundstuecke"
        ).fetchone()[0]

        found = connection.execute(
            "SELECT COUNT(*) FROM fundstuecke WHERE status = 'Gefunden'"
        ).fetchone()[0]

        requests = connection.execute(
            "SELECT COUNT(*) FROM fundstuecke WHERE status = 'Anfrage'"
        ).fetchone()[0]

        returned = connection.execute(
            "SELECT COUNT(*) FROM fundstuecke WHERE status = 'Abgeholt'"
        ).fetchone()[0]

    return total, found, requests, returned


# =========================================================
# KARTE
# =========================================================

def create_map(items):
    valid_items = [
        item
        for item in items
        if item["latitude"] is not None
        and item["longitude"] is not None
    ]

    if not valid_items:
        return None

    center_lat = sum(item["latitude"] for item in valid_items) / len(valid_items)
    center_lon = sum(item["longitude"] for item in valid_items) / len(valid_items)

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    for item in valid_items:
        color = "blue"

        if item["status"] == "Abgeholt":
            color = "gray"
        elif item["status"] == "Anfrage":
            color = "orange"

        popup = f"""
        <b>{item["name"]}</b><br>
        Kategorie: {item["kategorie"]}<br>
        Fundort: {item["ort"]}<br>
        Datum: {item["datum"]}<br>
        Status: {item["status"]}
        """

        folium.Marker(
            location=[item["latitude"], item["longitude"]],
            popup=folium.Popup(popup, max_width=280),
            tooltip=item["name"],
            icon=folium.Icon(
                color=color,
                icon="info-sign",
            ),
        ).add_to(fmap)

    return fmap


# =========================================================
# INITIALISIERUNG
# =========================================================

init_database()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 🔎 Fundbüro")
    st.caption("Version 1.1")

    page = st.radio(
        "Navigation",
        [
            "Übersicht",
            "Karte",
            "Fundstück melden",
            "Verwaltung",
        ],
    )

    st.divider()

    st.markdown(
        """
        **Design**

        Schwarz · Weiß · Dunkelblau
        """
    )

    st.caption("SQLite-Datenbank aktiv")


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
        <h1>Fundbüro</h1>
        <p>Fundstücke erfassen, suchen und Fundorte auf der Karte anzeigen.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# ÜBERSICHT
# =========================================================

if page == "Übersicht":

    total, found, requests, returned = get_statistics()

    st.markdown(
        '<div class="section-title">Übersicht</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(4)

    metrics = [
        ("Alle Fundstücke", total),
        ("Gefunden", found),
        ("Anfragen", requests),
        ("Abgeholt", returned),
    ]

    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">{label}</div>
                    <div class="metric-number">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    col1, col2 = st.columns([2, 1])

    with col1:
        search = st.text_input(
            "🔍 Suche",
            placeholder="iPhone, Schlüssel, Bahnhof ..."
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["Alle"] + STATUS,
        )

    category_filter = st.selectbox(
        "Kategorie",
        ["Alle"] + KATEGORIEN,
    )

    items = get_items(
        search,
        category_filter,
        status_filter,
    )

    st.markdown(
        f'<div class="section-title">Fundstücke ({len(items)})</div>',
        unsafe_allow_html=True,
    )

    if not items:
        st.info("Keine Fundstücke gefunden.")

    for item in items:

        st.markdown(
            f"""
            <div class="item-card">
                <div class="item-title">
                    {item["name"]}
                </div>

                <p>
                    <span class="badge">
                        {item["kategorie"]}
                    </span>
                    &nbsp;
                    <span class="badge">
                        {item["status"]}
                    </span>
                </p>

                <div class="item-meta">
                    📍 {item["ort"]}
                    &nbsp;·&nbsp;
                    📅 {item["datum"]}
                    &nbsp;·&nbsp;
                    ID #{item["id"]}
                </div>

                <p>
                    {item["beschreibung"]}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            if item["status"] != "Abgeholt":
                if st.button(
                    "✓ Abgeholt",
                    key=f"return_{item['id']}",
                ):
                    update_status(item["id"], "Abgeholt")
                    st.rerun()

        with c2:
            if item["status"] == "Gefunden":
                if st.button(
                    "Anfrage",
                    key=f"request_{item['id']}",
                ):
                    update_status(item["id"], "Anfrage")
                    st.rerun()

        with c3:
            if st.button(
                "Löschen",
                key=f"delete_{item['id']}",
            ):
                delete_item(item["id"])
                st.success("Fundstück gelöscht.")
                st.rerun()

        st.divider()


# =========================================================
# KARTE
# =========================================================

elif page == "Karte":

    st.markdown(
        '<div class="section-title">🗺️ Fundorte</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Hier werden alle Fundstücke angezeigt, für die Koordinaten gespeichert wurden."
    )

    if folium is None or st_folium is None:
        st.error(
            "Für die Karte fehlen Pakete. Installiere sie mit: "
            "`pip install folium streamlit-folium`"
        )
        st.stop()

    map_items = get_items()

    fmap = create_map(map_items)

    if fmap is None:
        st.info(
            "Noch keine Fundstücke mit Kartenkoordinaten vorhanden. "
            "Beim Anlegen eines Fundstücks kannst du die Koordinaten eintragen."
        )
    else:
        st.markdown(
            '<div class="map-box">',
            unsafe_allow_html=True,
        )

        st_folium(
            fmap,
            width=None,
            height=600,
            returned_objects=[],
        )

        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# FUNDSTÜCK MELDEN
# =========================================================

elif page == "Fundstück melden":

    st.markdown(
        '<div class="section-title">Neues Fundstück</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Für die Kartenanzeige kannst du beim Fundort optional "
        "GPS-Koordinaten angeben. Beispiel: Schleswig ≈ 54.5215, 9.5586."
    )

    with st.form("new_item_form"):

        name = st.text_input(
            "Name des Gegenstands *",
            placeholder="z. B. Schwarzes iPhone",
        )

        category = st.selectbox(
            "Kategorie *",
            KATEGORIEN,
        )

        location = st.text_input(
            "Fundort *",
            placeholder="z. B. Bahnhof Schleswig",
        )

        found_date = st.date_input(
            "Funddatum *",
            value=date.today(),
        )

        description = st.text_area(
            "Beschreibung *",
            placeholder="Farbe, Marke, besondere Merkmale ...",
            height=130,
        )

        st.markdown("### 📍 Kartenposition")

        map_col1, map_col2 = st.columns(2)

        with map_col1:
            latitude = st.number_input(
                "Breitengrad",
                min_value=-90.0,
                max_value=90.0,
                value=54.5215,
                step=0.0001,
                format="%.4f",
            )

        with map_col2:
            longitude = st.number_input(
                "Längengrad",
                min_value=-180.0,
                max_value=180.0,
                value=9.5586,
                step=0.0001,
                format="%.4f",
            )

        submitted = st.form_submit_button(
            "Fundstück speichern",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        if not name.strip():
            st.error("Bitte einen Namen eingeben.")

        elif not location.strip():
            st.error("Bitte einen Fundort eingeben.")

        elif not description.strip():
            st.error("Bitte eine Beschreibung eingeben.")

        else:
            add_item(
                name=name,
                category=category,
                location=location,
                found_date=found_date,
                description=description,
                latitude=latitude,
                longitude=longitude,
            )

            st.success("Fundstück wurde erfolgreich gespeichert.")
            st.rerun()


# =========================================================
# VERWALTUNG
# =========================================================

elif page == "Verwaltung":

    st.markdown(
        '<div class="section-title">Verwaltung</div>',
        unsafe_allow_html=True,
    )

    items = get_items()

    if not items:
        st.info("Noch keine Fundstücke vorhanden.")

    else:
        data = pd.DataFrame(
            [dict(item) for item in items]
        )

        data = data[
            [
                "id",
                "name",
                "kategorie",
                "ort",
                "datum",
                "beschreibung",
                "status",
                "latitude",
                "longitude",
            ]
        ]

        data.columns = [
            "ID",
            "Name",
            "Kategorie",
            "Fundort",
            "Datum",
            "Beschreibung",
            "Status",
            "Breitengrad",
            "Längengrad",
        ]

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = data.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ CSV exportieren",
            data=csv_data,
            file_name="fundstuecke.csv",
            mime="text/csv",
        )
