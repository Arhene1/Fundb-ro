import streamlit as st
import sqlite3
from datetime import date
from pathlib import Path
import hashlib


# =========================================================
# KONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Fundbüro",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "fundbuero.db"


# =========================================================
# DESIGN
# =========================================================

st.markdown(
    """
    <style>

    /* Grundlayout */
    .stApp {
        background-color: #f8fafc;
    }

    /* Hauptbereich */
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Überschriften */
    h1, h2, h3 {
        color: #0f172a;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Karten */
    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
    }

    .card-title {
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 8px;
    }

    .muted {
        color: #64748b;
        font-size: 14px;
    }

    /* Status */
    .status {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .found {
        background: #dcfce7;
        color: #166534;
    }

    .claimed {
        background: #fef3c7;
        color: #92400e;
    }

    .returned {
        background: #e2e8f0;
        color: #475569;
    }

    /* Statistik */
    .stat-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
    }

    .stat-number {
        font-size: 30px;
        font-weight: 800;
        color: #0f172a;
    }

    .stat-label {
        color: #64748b;
        font-size: 14px;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }

    /* Trennlinie */
    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 25px 0;
    }

    /* Mobile */
    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        h1 {
            font-size: 28px;
        }

        h2 {
            font-size: 22px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# DATENBANK
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            found_date TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Gefunden',
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_database()


# =========================================================
# FUNKTIONEN
# =========================================================

def add_item(
    name,
    category,
    location,
    found_date,
    description
):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO items
        (
            name,
            category,
            location,
            found_date,
            description,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            name,
            category,
            location,
            found_date,
            description,
            "Gefunden"
        )
    )

    conn.commit()
    conn.close()


def get_items(
    search="",
    category="Alle",
    status="Alle"
):

    conn = get_connection()

    query = """
        SELECT *
        FROM items
        WHERE 1 = 1
    """

    parameters = []

    if search:

        query += """
            AND (
                LOWER(name) LIKE ?
                OR LOWER(description) LIKE ?
                OR LOWER(location) LIKE ?
            )
        """

        search_value = f"%{search.lower()}%"

        parameters.extend(
            [
                search_value,
                search_value,
                search_value
            ]
        )

    if category != "Alle":

        query += """
            AND category = ?
        """

        parameters.append(category)

    if status != "Alle":

        query += """
            AND status = ?
        """

        parameters.append(status)

    query += """
        ORDER BY id DESC
    """

    rows = conn.execute(
        query,
        parameters
    ).fetchall()

    conn.close()

    return rows


def update_status(item_id, status):

    conn = get_connection()

    conn.execute(
        """
        UPDATE items
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            item_id
        )
    )

    conn.commit()
    conn.close()


def delete_item(item_id):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM items
        WHERE id = ?
        """,
        (item_id,)
    )

    conn.commit()
    conn.close()


def get_statistics():

    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM items"
    ).fetchone()[0]

    found = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status = 'Gefunden'"
    ).fetchone()[0]

    claimed = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status = 'Anfrage'"
    ).fetchone()[0]

    returned = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status = 'Abgeholt'"
    ).fetchone()[0]

    conn.close()

    return total, found, claimed, returned


# =========================================================
# SESSION
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "Fundstücke"


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            padding: 10px 0 25px 0;
            font-size: 24px;
            font-weight: 800;
            color: #0f172a;
        ">
            🔎 Fundbüro
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("Digitale Fundbüro-Verwaltung")

    st.divider()

    if st.button(
        "📦 Fundstücke",
        use_container_width=True
    ):
        st.session_state.page = "Fundstücke"

    if st.button(
        "➕ Fundstück hinzufügen",
        use_container_width=True
    ):
        st.session_state.page = "Hinzufügen"

    if st.button(
        "📊 Dashboard",
        use_container_width=True
    ):
        st.session_state.page = "Dashboard"

    st.divider()

    st.caption("Version 1.0")


# =========================================================
# FUNDSTÜCKE
# =========================================================

if st.session_state.page == "Fundstücke":

    st.title("Fundstücke")

    st.write(
        "Durchsuche alle aktuell erfassten Fundstücke."
    )

    st.divider()

    col1, col2, col3 = st.columns(
        [2, 1, 1]
    )

    with col1:

        search = st.text_input(
            "Suche",
            placeholder="z. B. iPhone, Schlüssel, Bahnhof..."
        )

    with col2:

        categories = [
            "Alle",
            "Handy",
            "Schlüssel",
            "Portemonnaie",
            "Tasche",
            "Kleidung",
            "Dokumente",
            "Elektronik",
            "Brille",
            "Schmuck",
            "Sonstiges"
        ]

        category = st.selectbox(
            "Kategorie",
            categories
        )

    with col3:

        status = st.selectbox(
            "Status",
            [
                "Alle",
                "Gefunden",
                "Anfrage",
                "Abgeholt"
            ]
        )

    st.divider()

    items = get_items(
        search,
        category,
        status
    )

    if not items:

        st.info(
            "🔎 Keine Fundstücke gefunden."
        )

    else:

        st.write(
            f"**{len(items)} Fundstück(e)**"
        )

        for item in items:

            if item["status"] == "Gefunden":
                status_class = "found"

            elif item["status"] == "Anfrage":
                status_class = "claimed"

            else:
                status_class = "returned"

            st.markdown(
                f"""
                <div class="card">

                    <div class="card-title">
                        {item["name"]}
                    </div>

                    <span class="status {status_class}">
                        {item["status"]}
                    </span>

                    <div class="muted">
                        📍 {item["location"]}
                        &nbsp; · &nbsp;
                        📅 {item["found_date"]}
                        &nbsp; · &nbsp;
                        🏷️ {item["category"]}
                    </div>

                    <br>

                    <div>
                        {item["description"]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            col_a, col_b, col_c = st.columns(
                [1, 1, 1]
            )

            with col_a:

                if item["status"] != "Abgeholt":

                    if st.button(
                        "✅ Abgeholt",
                        key=f"returned_{item['id']}",
                        use_container_width=True
                    ):

                        update_status(
                            item["id"],
                            "Abgeholt"
                        )

                        st.rerun()

            with col_b:

                if item["status"] == "Gefunden":

                    if st.button(
                        "🟡 Anfrage",
                        key=f"claim_{item['id']}",
                        use_container_width=True
                    ):

                        update_status(
                            item["id"],
                            "Anfrage"
                        )

                        st.rerun()

            with col_c:

                if st.button(
                    "🗑️ Löschen",
                    key=f"delete_{item['id']}",
                    use_container_width=True
                ):

                    delete_item(
                        item["id"]
                    )

                    st.rerun()


# =========================================================
# FUNDSTÜCK HINZUFÜGEN
# =========================================================

elif st.session_state.page == "Hinzufügen":

    st.title("Fundstück hinzufügen")

    st.write(
        "Erfasse einen neu gefundenen Gegenstand."
    )

    st.divider()

    with st.form(
        "new_item_form",
        clear_on_submit=True
    ):

        name = st.text_input(
            "Name des Gegenstands *",
            placeholder="z. B. iPhone 15"
        )

        category = st.selectbox(
            "Kategorie *",
            [
                "Handy",
                "Schlüssel",
                "Portemonnaie",
                "Tasche",
                "Kleidung",
                "Dokumente",
                "Elektronik",
                "Brille",
                "Schmuck",
                "Sonstiges"
            ]
        )

        location = st.text_input(
            "Fundort *",
            placeholder="z. B. Bahnhof Schleswig"
        )

        found_date = st.date_input(
            "Funddatum *",
            value=date.today()
        )

        description = st.text_area(
            "Beschreibung *",
            placeholder=(
                "Beschreibe Farbe, Marke, "
                "besondere Merkmale usw."
            )
        )

        submitted = st.form_submit_button(
            "💾 Fundstück speichern",
            use_container_width=True
        )

        if submitted:

            if not name.strip():

                st.error(
                    "Bitte einen Namen eingeben."
                )

            elif not location.strip():

                st.error(
                    "Bitte einen Fundort eingeben."
                )

            elif not description.strip():

                st.error(
                    "Bitte eine Beschreibung eingeben."
                )

            else:

                add_item(
                    name.strip(),
                    category,
                    location.strip(),
                    found_date.isoformat(),
                    description.strip()
                )

                st.success(
                    "✅ Fundstück wurde erfolgreich gespeichert."
                )


# =========================================================
# DASHBOARD
# =========================================================

elif st.session_state.page == "Dashboard":

    st.title("Dashboard")

    st.write(
        "Übersicht über das digitale Fundbüro."
    )

    st.divider()

    total, found, claimed, returned = (
        get_statistics()
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">
                    {total}
                </div>
                <div class="stat-label">
                    Alle Fundstücke
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">
                    {found}
                </div>
                <div class="stat-label">
                    Gefunden
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">
                    {claimed}
                </div>
                <div class="stat-label">
                    Anfragen
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">
                    {returned}
                </div>
                <div class="stat-label">
                    Abgeholt
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Letzte Fundstücke")

    recent_items = get_items()

    if recent_items:

        for item in recent_items[:5]:

            st.markdown(
                f"""
                <div class="card">

                    <div class="card-title">
                        {item["name"]}
                    </div>

                    <div class="muted">
                        {item["category"]}
                        ·
                        {item["location"]}
                        ·
                        {item["found_date"]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "Noch keine Fundstücke vorhanden."
        )
        
