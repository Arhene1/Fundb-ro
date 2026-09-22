import streamlit as st
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime

import numpy as np
from PIL import Image
import tensorflow as tf
import pandas as pd
import folium
from streamlit_folium import st_folium


# ============================================================
# KONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Fundbüro",
    page_icon="🔎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "keras_model.h5"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "fundbuero.db"

UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# KI-KLASSEN
# ============================================================

AI_LABELS = [
    "Flaschen",
    "Hose",
    "Jacken",
    "Federtasche",
]


# ============================================================
# DESIGN
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #ffffff;
        color: #111111;
    }

    .block-container {
        max-width: 620px;
        padding: 1rem 0.8rem 4rem 0.8rem;
    }

    h1, h2, h3 {
        color: #111111;
    }

    div.stButton > button {
        width: 100%;
        min-height: 50px;
        border-radius: 12px;
        font-weight: 600;
    }

    div[data-testid="stFileUploader"] {
        border: 2px dashed #69bff2;
        border-radius: 16px;
        padding: 12px;
        background: #f2faff;
    }

    .photo-box {
        background: #eef8ff;
        border: 1px solid #b7e1fb;
        border-radius: 16px;
        padding: 16px;
        margin-top: 12px;
        margin-bottom: 16px;
    }

    .ai-box {
        background: #eef8ff;
        border: 1px solid #9ed6f7;
        border-radius: 16px;
        padding: 16px;
        margin-top: 15px;
        margin-bottom: 15px;
    }

    .ai-title {
        color: #0879c9;
        font-weight: 700;
        font-size: 18px;
    }

    .ai-result {
        font-size: 26px;
        font-weight: 800;
        margin-top: 5px;
    }

    .ai-confidence {
        color: #666666;
        margin-top: 5px;
    }

    .info-box {
        background: #f7f7f7;
        border-radius: 14px;
        padding: 14px;
        margin: 10px 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATENBANK
# ============================================================

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = get_db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS fundstuecke (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT NOT NULL,
            kategorie TEXT,
            beschreibung TEXT,
            fundort TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'Gefunden',
            foto TEXT,
            ki_label TEXT,
            ki_confidence REAL,
            created_at TEXT NOT NULL
        )
        """
    )

    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(fundstuecke)"
        ).fetchall()
    }

    required_columns = {
        "latitude": "REAL",
        "longitude": "REAL",
        "foto": "TEXT",
        "ki_label": "TEXT",
        "ki_confidence": "REAL",
    }

    for column_name, column_type in required_columns.items():

        if column_name not in columns:

            connection.execute(
                f"ALTER TABLE fundstuecke "
                f"ADD COLUMN {column_name} {column_type}"
            )

    connection.commit()
    connection.close()


init_database()


# ============================================================
# KI LADEN
# ============================================================

class CompatibleDepthwiseConv2D(tf.keras.layers.DepthwiseConv2D):
    def __init__(self, *args, **kwargs):
        # Teachable Machine speichert bei älteren H5-Modellen
        # zusätzlich "groups": 1.
        # Keras 3 akzeptiert diesen Parameter nicht.
        kwargs.pop("groups", None)
        super().__init__(*args, **kwargs)


@st.cache_resource
def load_ai_model():

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            "Das KI-Modell wurde nicht gefunden.\n\n"
            "Bitte lege 'keras_model.h5' neben 'app.py'."
        )

    model = tf.keras.models.load_model(
        MODEL_PATH,
        compile=False,
        custom_objects={
            "DepthwiseConv2D": CompatibleDepthwiseConv2D
        }
    )

    return model


# ============================================================
# KI BILDERKENNUNG
# ============================================================

def recognize_image(image):

    model = load_ai_model()

    # Bild in RGB umwandeln
    image = image.convert("RGB")

    # Modell erwartet 224 x 224
    image = image.resize((224, 224))

    # Bild in NumPy umwandeln
    image_array = np.asarray(
        image,
        dtype=np.float32
    )

    # Normalisierung
    image_array = image_array / 255.0

    # Batch-Dimension hinzufügen
    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    # KI-Vorhersage
    prediction = model.predict(
        image_array,
        verbose=0
    )

    prediction = np.asarray(
        prediction
    ).reshape(-1)

    # Beste Klasse
    class_index = int(
        np.argmax(prediction)
    )

    confidence = float(
        prediction[class_index]
    )

    # Klassenname
    if class_index < len(AI_LABELS):

        label = AI_LABELS[class_index]

    else:

        label = f"Klasse {class_index}"

    return label, confidence


# ============================================================
# HEADER
# ============================================================

st.title("🔎 Fundbüro")

st.caption(
    "Fundstücke fotografieren, automatisch erkennen "
    "und speichern."
)


# ============================================================
# NAVIGATION
# ============================================================

page = st.radio(
    "Bereich auswählen",
    [
        "📸 Fundstück melden",
        "📋 Übersicht",
        "🗺️ Karte",
        "⚙️ Verwaltung",
    ],
    horizontal=True,
)


# ============================================================
# FOTO / FUNDSTÜCK MELDEN
# ============================================================

if page == "📸 Fundstück melden":

    st.header("Fundstück melden")

    st.markdown(
        """
        <div class="photo-box">
        <b>📸 Foto des Fundstücks</b><br>
        <span style="color:#666">
        Fotografiere das Fundstück oder wähle ein vorhandenes Foto aus.
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # ECHTER FOTO-UPLOAD
    # ========================================================

    uploaded_photo = st.file_uploader(
        "📸 Foto aufnehmen oder auswählen",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp"
        ],
        accept_multiple_files=False,
        help=(
            "Auf dem Smartphone kannst du hier ein Foto "
            "auswählen oder – je nach Browser – direkt "
            "die Kamera verwenden."
        ),
    )

    ai_label = None
    ai_confidence = None

    # ========================================================
    # FOTO ANGEZEIGT
    # ========================================================

    if uploaded_photo is not None:

        image = Image.open(
            uploaded_photo
        )

        st.image(
            image,
            caption="Hochgeladenes Fundstück",
            width="stretch",
        )

        # ====================================================
        # KI STARTEN
        # ====================================================

        with st.spinner(
            "🤖 KI analysiert das Foto ..."
        ):

            try:

                ai_label, ai_confidence = recognize_image(
                    image
                )

                st.markdown(
                    f"""
                    <div class="ai-box">

                    <div class="ai-title">
                    🤖 KI-Erkennung
                    </div>

                    <div class="ai-result">
                    {ai_label}
                    </div>

                    <div class="ai-confidence">
                    Sicherheit:
                    {ai_confidence * 100:.1f} %
                    </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if ai_confidence < 0.60:

                    st.warning(
                        "Die KI ist sich bei dieser Erkennung "
                        "nicht sehr sicher. Bitte überprüfe "
                        "die Kategorie."
                    )

                else:

                    st.success(
                        "Fundstück erfolgreich erkannt."
                    )

            except Exception as error:

                st.error(
                    "Die KI konnte das Foto nicht analysieren."
                )

                st.code(
                    str(error)
                )

    # ========================================================
    # KATEGORIE
    # ========================================================

    categories = [
        "Flaschen",
        "Hose",
        "Jacken",
        "Federtasche",
        "Sonstiges",
    ]

    if ai_label in categories:

        default_category = categories.index(
            ai_label
        )

    else:

        default_category = 0

    category = st.selectbox(
        "Kategorie",
        categories,
        index=default_category,
    )

    # ========================================================
    # TITEL
    # ========================================================

    title = st.text_input(
        "Titel",
        placeholder="z. B. Schwarze Jacke",
    )

    # ========================================================
    # BESCHREIBUNG
    # ========================================================

    description = st.text_area(
        "Beschreibung",
        placeholder=(
            "Farbe, Marke, besondere Merkmale usw."
        ),
    )

    # ========================================================
    # FUNDORT
    # ========================================================

    location = st.text_input(
        "📍 Fundort",
        placeholder="z. B. Bahnhof Schleswig",
    )

    # ========================================================
    # KOORDINATEN
    # ========================================================

    st.subheader("🗺️ Kartenposition")

    col1, col2 = st.columns(2)

    with col1:

        latitude = st.number_input(
            "Breitengrad",
            value=0.0,
            format="%.6f",
        )

    with col2:

        longitude = st.number_input(
            "Längengrad",
            value=0.0,
            format="%.6f",
        )

    # ========================================================
    # SPEICHERN
    # ========================================================

    if st.button(
        "💾 Fundstück speichern",
        type="primary",
    ):

        if not title.strip():

            st.error(
                "Bitte gib einen Titel ein."
            )

        else:

            saved_photo = None

            # ================================================
            # FOTO SPEICHERN
            # ================================================

            if uploaded_photo is not None:

                file_extension = (
                    Path(
                        uploaded_photo.name
                    ).suffix.lower()
                )

                if not file_extension:

                    file_extension = ".jpg"

                filename = (
                    f"{uuid.uuid4().hex}"
                    f"{file_extension}"
                )

                saved_photo = (
                    UPLOAD_DIR /
                    filename
                )

                saved_photo.write_bytes(
                    uploaded_photo.getbuffer()
                )

            # ================================================
            # DATENBANK
            # ================================================

            connection = get_db()

            connection.execute(
                """
                INSERT INTO fundstuecke
                (
                    titel,
                    kategorie,
                    beschreibung,
                    fundort,
                    latitude,
                    longitude,
                    status,
                    foto,
                    ki_label,
                    ki_confidence,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),

                    category,

                    description.strip(),

                    location.strip(),

                    latitude
                    if latitude != 0
                    else None,

                    longitude
                    if longitude != 0
                    else None,

                    "Gefunden",

                    str(saved_photo)
                    if saved_photo
                    else None,

                    ai_label,

                    ai_confidence,

                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            connection.commit()
            connection.close()

            st.success(
                "✅ Fundstück wurde gespeichert!"
            )

            st.rerun()


# ============================================================
# ÜBERSICHT
# ============================================================

elif page == "📋 Übersicht":

    st.header(
        "📋 Gefundene Gegenstände"
    )

    connection = get_db()

    items = connection.execute(
        """
        SELECT *
        FROM fundstuecke
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    if not items:

        st.info(
            "Noch keine Fundstücke vorhanden."
        )

    else:

        for item in items:

            with st.container(
                border=True
            ):

                # Foto
                if item["foto"]:

                    photo_path = Path(
                        item["foto"]
                    )

                    if photo_path.exists():

                        st.image(
                            photo_path,
                            width="stretch",
                        )

                # Titel
                st.subheader(
                    item["titel"]
                )

                # Kategorie
                if item["kategorie"]:

                    st.write(
                        f"**Kategorie:** "
                        f"{item['kategorie']}"
                    )

                # Fundort
                if item["fundort"]:

                    st.write(
                        f"📍 **Fundort:** "
                        f"{item['fundort']}"
                    )

                # Beschreibung
                if item["beschreibung"]:

                    st.write(
                        item["beschreibung"]
                    )

                # KI
                if item["ki_label"]:

                    confidence = (
                        item["ki_confidence"]
                        or 0
                    ) * 100

                    st.caption(
                        f"🤖 KI-Erkennung: "
                        f"{item['ki_label']} "
                        f"({confidence:.1f} %)"
                    )

                # Status
                st.caption(
                    f"Status: {item['status']} "
                    f"· {item['created_at']}"
                )


# ============================================================
# KARTE
# ============================================================

elif page == "🗺️ Karte":

    st.header(
        "🗺️ Fundorte"
    )

    connection = get_db()

    items = connection.execute(
        """
        SELECT *
        FROM fundstuecke
        WHERE latitude IS NOT NULL
        AND longitude IS NOT NULL
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    if not items:

        st.info(
            "Noch keine Fundstücke mit "
            "Kartenkoordinaten vorhanden."
        )

    else:

        first_item = items[0]

        map_center = [
            first_item["latitude"],
            first_item["longitude"],
        ]

        fmap = folium.Map(
            location=map_center,
            zoom_start=13,
        )

        for item in items:

            popup = f"""
            <b>{item['titel']}</b><br>
            Kategorie: {item['kategorie'] or ''}<br>
            Fundort: {item['fundort'] or ''}
            """

            folium.Marker(
                [
                    item["latitude"],
                    item["longitude"],
                ],
                tooltip=item["titel"],
                popup=popup,
            ).add_to(fmap)

        st_folium(
            fmap,
            width=None,
            height=500,
        )


# ============================================================
# VERWALTUNG
# ============================================================

elif page == "⚙️ Verwaltung":

    st.header(
        "⚙️ Verwaltung"
    )

    connection = get_db()

    items = connection.execute(
        """
        SELECT *
        FROM fundstuecke
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    st.metric(
        "Anzahl Fundstücke",
        len(items),
    )

    if items:

        data = [
            dict(item)
            for item in items
        ]

        dataframe = pd.DataFrame(
            data
        )

        st.dataframe(
            dataframe,
            width="stretch",
            hide_index=True,
        )

        csv_data = (
            dataframe
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ CSV exportieren",
            csv_data,
            "fundstuecke.csv",
            "text/csv",
            width="stretch",
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Fundbüro · Streamlit · TensorFlow/Keras"
)
