
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
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATABASE = Path("fundbuero.db")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

KATEGORIEN = [
    "Handy", "Schlüssel", "Portemonnaie", "Tasche", "Kleidung",
    "Dokumente", "Elektronik", "Brille", "Schmuck", "Sonstiges"
]
STATUS = ["Gefunden", "Anfrage", "Abgeholt"]


# =========================================================
# MOBILE DESIGN: WEISS / SCHWARZ / HELLBLAU
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
            color: #111827;
        }

        [data-testid="stHeader"] {
            background: #ffffff;
        }

        /* Mobile first */
        .block-container {
            max-width: 560px !important;
            padding: 0.8rem 0.9rem 5.5rem 0.9rem !important;
        }

        .hero {
            background: #ffffff;
            color: #111827;
            padding: 10px 2px 18px 2px;
            margin-bottom: 6px;
        }

        .hero h1 {
            font-size: 30px;
            line-height: 1.05;
            font-weight: 800;
            margin: 0;
            color: #111827;
        }

        .hero p {
            color: #64748b;
            font-size: 13px;
            margin: 6px 0 0 0;
        }

        .mobile-nav {
            background: #eef7ff;
            border: 1px solid #cfe8ff;
            border-radius: 14px;
            padding: 9px 12px;
            margin: 0 0 14px 0;
            color: #1677c8;
            font-size: 12px;
            font-weight: 700;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 14px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        }

        .metric-title {
            color: #64748b;
            font-size: 11px;
            font-weight: 600;
        }

        .metric-number {
            color: #1590e6;
            font-size: 25px;
            font-weight: 800;
            margin-top: 2px;
        }

        .item-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        }

        .item-title {
            font-size: 17px;
            font-weight: 750;
            color: #111827;
        }

        .item-meta {
            color: #64748b;
            font-size: 12px;
            line-height: 1.5;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            background: #eef7ff;
            color: #1677c8;
            font-size: 10px;
            font-weight: 700;
            border: 1px solid #cfe8ff;
        }

        .section-title {
            color: #111827;
            font-size: 21px;
            font-weight: 800;
            margin: 14px 0 10px;
        }

        .upload-box {
            background: #f8fbff;
            border: 1px dashed #8ccfff;
            border-radius: 14px;
            padding: 10px;
        }

        .info-box {
            background: #f8fbff;
            border: 1px solid #d9edff;
            border-radius: 12px;
            padding: 12px;
            color: #526174;
            font-size: 12px;
        }

        .photo-preview {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
            margin-top: 8px;
        }

        /* Touch friendly controls */
        div.stButton > button,
        div.stDownloadButton > button {
            min-height: 44px;
            border-radius: 11px;
            font-weight: 650;
            border: 1px solid #cbd5e1;
        }

        div.stButton > button[kind="primary"] {
            background: #1590e6;
            color: #ffffff;
            border-color: #1590e6;
        }

        div.stButton > button[kind="primary"]:hover {
            background: #0d7bc5;
            border-color: #0d7bc5;
        }

        input, textarea, [data-baseweb="select"] {
            border-radius: 10px !important;
        }

        /* Sidebar bleibt hell und kompakt */
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
        }

        [data-testid="stSidebar"] * {
            color: #111827 !important;
        }

        hr {
            border-color: #e2e8f0;
        }

        /* Mobile Tabellen scrollbar */
        [data-testid="stDataFrame"] {
            overflow-x: auto;
        }

        @media (max-width: 600px) {
            .block-container {
                padding-left: 0.7rem !important;
                padding-right: 0.7rem !important;
            }

            .hero h1 {
                font-size: 27px;
            }

            .metric-card {
                padding: 11px;
            }

            .metric-number {
                font-size: 22px;
            }

            .stButton button {
                width: 100%;
            }
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
                longitude REAL,
                foto TEXT
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(fundstuecke)").fetchall()
        }

        if "latitude" not in columns:
            connection.execute("ALTER TABLE fundstuecke ADD COLUMN latitude REAL")

        if "longitude" not in columns:
            connection.execute("ALTER TABLE fundstuecke ADD COLUMN longitude REAL")

        if "foto" not in columns:
            connection.execute("ALTER TABLE fundstuecke ADD COLUMN foto TEXT")


def add_item(name, category, location, found_date, description, latitude, longitude, foto):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO fundstuecke
            (name, kategorie, ort, datum, beschreibung, status, latitude, longitude, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                foto,
            ),
        )


def get_items(search="", category="Alle", status="Alle"):
    sql = "SELECT * FROM fundstuecke WHERE 1=1"
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
        row = connection.execute(
            "SELECT foto FROM fundstuecke WHERE id = ?", (item_id,)
        ).fetchone()

        connection.execute("DELETE FROM fundstuecke WHERE id = ?", (item_id,))

        if row and row["foto"]:
            try:
                Path(row["foto"]).unlink(missing_ok=True)
            except Exception:
                pass


def get_statistics():
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(*) FROM fundstuecke").fetchone()[0]
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
        item for item in items
        if item["latitude"] is not None and item["longitude"] is not None
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
            color = "lightblue"

        popup = f"""
        <b>{item["name"]}</b><br>
        Kategorie: {item["kategorie"]}<br>
        Fundort: {item["ort"]}<br>
        Datum: {item["datum"]}<br>
        Status: {item["status"]}
        """

        folium.Marker(
            location=[item["latitude"], item["longitude"]],
            popup=folium.Popup(popup, max_width=260),
            tooltip=item["name"],
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(fmap)

    return fmap


# =========================================================
# INITIALISIERUNG
# =========================================================

init_database()


# =========================================================
# MOBILE NAVIGATION
# =========================================================

with st.sidebar:
    st.markdown("## 🔎 Fundbüro")
    st.caption("Mobile Version 1.2")

    page = st.radio(
        "Bereich",
        ["Übersicht", "Karte", "Fundstück melden", "Verwaltung"],
    )

    st.divider()
    st.caption("Weiß · Schwarz · Hellblau")


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
        <h1>Fundbüro</h1>
        <p>Fundstücke schnell erfassen, finden und zuordnen.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="mobile-nav">📱 Für Smartphone-Nutzung optimiert</div>',
    unsafe_allow_html=True,
)


# =========================================================
# ÜBERSICHT
# =========================================================

if page == "Übersicht":
    total, found, requests, returned = get_statistics()

    st.markdown('<div class="section-title">Übersicht</div>', unsafe_allow_html=True)

    # Zwei Spalten statt vier: deutlich besser auf Handys.
    cols = st.columns(2)
    metrics = [
        ("Alle", total),
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

    search = st.text_input(
        "🔍 Suche",
        placeholder="Gegenstand oder Fundort ..."
    )

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        status_filter = st.selectbox("Status", ["Alle"] + STATUS)

    with filter_col2:
        category_filter = st.selectbox("Kategorie", ["Alle"] + KATEGORIEN)

    items = get_items(search, category_filter, status_filter)

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
                <div class="item-title">{item["name"]}</div>
                <p>
                    <span class="badge">{item["kategorie"]}</span>
                    &nbsp;
                    <span class="badge">{item["status"]}</span>
                </p>
                <div class="item-meta">
                    📍 {item["ort"]}<br>
                    📅 {item["datum"]} · ID #{item["id"]}
                </div>
                <p>{item["beschreibung"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if item["foto"] and Path(item["foto"]).exists():
            st.image(item["foto"], caption="Foto des Fundstücks", use_container_width=True)

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if item["status"] != "Abgeholt":
                if st.button("✓ Abgeholt", key=f"return_{item['id']}"):
                    update_status(item["id"], "Abgeholt")
                    st.rerun()

        with action_col2:
            if item["status"] == "Gefunden":
                if st.button("Anfrage", key=f"request_{item['id']}"):
                    update_status(item["id"], "Anfrage")
                    st.rerun()

        if st.button("Löschen", key=f"delete_{item['id']}"):
            delete_item(item["id"])
            st.success("Fundstück gelöscht.")
            st.rerun()

        st.divider()


# =========================================================
# KARTE
# =========================================================

elif page == "Karte":
    st.markdown('<div class="section-title">🗺️ Fundorte</div>', unsafe_allow_html=True)

    if folium is None or st_folium is None:
        st.error(
            "Für die Karte fehlen Pakete. Installiere: "
            "`pip install folium streamlit-folium`"
        )
        st.stop()

    fmap = create_map(get_items())

    if fmap is None:
        st.info("Noch keine Fundstücke mit Kartenposition vorhanden.")
    else:
        st_folium(
            fmap,
            width=520,
            height=520,
            returned_objects=[],
        )


# =========================================================
# FUNDSTÜCK MELDEN
# =========================================================

elif page == "Fundstück melden":
    st.markdown(
        '<div class="section-title">Fundstück melden</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">Foto hinzufügen, Fundort eintragen und speichern. '
        'Das Foto wird zusammen mit dem Fundstück gespeichert.</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    with st.form("new_item_form"):
        name = st.text_input(
            "Gegenstand *",
            placeholder="z. B. Schwarzes iPhone",
        )

        category = st.selectbox("Kategorie *", KATEGORIEN)

        location = st.text_input(
            "Fundort *",
            placeholder="z. B. Bahnhof",
        )

        found_date = st.date_input(
            "Funddatum *",
            value=date.today(),
        )

        description = st.text_area(
            "Beschreibung *",
            placeholder="Farbe, Marke, besondere Merkmale ...",
            height=110,
        )

        st.markdown("**📷 Foto des Fundstücks**")
        uploaded_photo = st.file_uploader(
            "Foto auswählen oder mit der Handykamera aufnehmen",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
            help="Auf Smartphones kann je nach Browser direkt die Kamera verwendet werden.",
        )

        if uploaded_photo is not None:
            st.image(
                uploaded_photo,
                caption="Vorschau",
                use_container_width=True,
            )

        st.markdown("**📍 Kartenposition**")

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
            st.error("Bitte einen Gegenstand eingeben.")
        elif not location.strip():
            st.error("Bitte einen Fundort eingeben.")
        elif not description.strip():
            st.error("Bitte eine Beschreibung eingeben.")
        else:
            saved_photo = None

            if uploaded_photo is not None:
                suffix = Path(uploaded_photo.name).suffix.lower() or ".jpg"
                filename = f"fund_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S_%f')}{suffix}"
                photo_path = UPLOAD_DIR / filename
                photo_path.write_bytes(uploaded_photo.getbuffer())
                saved_photo = str(photo_path)

            add_item(
                name=name,
                category=category,
                location=location,
                found_date=found_date,
                description=description,
                latitude=latitude,
                longitude=longitude,
                foto=saved_photo,
            )

            st.success("Fundstück wurde gespeichert.")
            st.rerun()


# =========================================================
# VERWALTUNG
# =========================================================

elif page == "Verwaltung":
    st.markdown('<div class="section-title">Verwaltung</div>', unsafe_allow_html=True)

    items = get_items()

    if not items:
        st.info("Noch keine Fundstücke vorhanden.")
    else:
        data = pd.DataFrame([dict(item) for item in items])

        data = data[
            [
                "id", "name", "kategorie", "ort", "datum",
                "beschreibung", "status", "latitude", "longitude", "foto"
            ]
        ]

        data.columns = [
            "ID", "Name", "Kategorie", "Fundort", "Datum",
            "Beschreibung", "Status", "Breitengrad",
            "Längengrad", "Foto"
        ]

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = data.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "⬇️ CSV exportieren",
            data=csv_data,
            file_name="fundstuecke.csv",
            mime="text/csv",
            use_container_width=True,
        )
