import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    folium = None
    st_folium = None

# KI wird nur geladen, wenn sie tatsächlich gebraucht wird.
try:
    import tensorflow as tf
except ImportError:
    tf = None

st.set_page_config(
    page_title="Fundbüro",
    page_icon="🔎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fundbuero.db"
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "ai_model"
MODEL_PATH = MODEL_DIR / "keras_model.h5"
LABEL_PATH = MODEL_DIR / "labels.txt"
UPLOAD_DIR.mkdir(exist_ok=True)

KATEGORIEN = [
    "Handy", "Schlüssel", "Portemonnaie", "Tasche", "Kleidung",
    "Dokumente", "Elektronik", "Brille", "Schmuck", "Flaschen",
    "Hose", "Jacke", "Federtasche", "Sonstiges"
]
STATUS = ["Gefunden", "Anfrage", "Abgeholt"]

AI_TO_CATEGORY = {
    "Flaschen": "Flaschen",
    "Hose": "Hose",
    "Jacken": "Jacke",
    "Federtasche": "Federtasche",
}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: Inter, sans-serif; }
    .stApp { background:#fff; color:#111827; }
    [data-testid="stHeader"] { background:#fff; }
    .block-container { max-width:560px!important; padding:.7rem .75rem 5rem!important; }
    .hero { padding:8px 2px 14px; }
    .hero h1 { font-size:29px; line-height:1.05; margin:0; color:#111827; font-weight:800; }
    .hero p { margin:5px 0 0; color:#64748b; font-size:13px; }
    .section-title { color:#111827; font-size:21px; font-weight:800; margin:15px 0 10px; }
    .card { background:#fff; border:1px solid #e2e8f0; border-radius:15px; padding:14px; margin-bottom:10px; box-shadow:0 2px 10px rgba(15,23,42,.05); }
    .ai-card { background:#eef8ff; border:1px solid #bfe3ff; border-radius:14px; padding:13px; margin:8px 0 14px; }
    .ai-title { color:#0b78bd; font-weight:800; font-size:14px; }
    .ai-text { color:#334155; font-size:12px; margin-top:3px; }
    .metric { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:12px; }
    .metric small { color:#64748b; font-weight:600; }
    .metric strong { display:block; color:#1590e6; font-size:23px; margin-top:2px; }
    .badge { display:inline-block; padding:4px 8px; border-radius:999px; background:#eef7ff; color:#1677c8; font-size:10px; font-weight:700; border:1px solid #cfe8ff; }
    .item-title { font-size:17px; font-weight:750; color:#111827; }
    .item-meta { color:#64748b; font-size:12px; line-height:1.5; }
    div.stButton > button, div.stDownloadButton > button { min-height:44px; border-radius:11px; font-weight:650; border:1px solid #cbd5e1; }
    div.stButton > button[kind="primary"] { background:#1590e6; color:#fff; border-color:#1590e6; }
    .info { background:#f8fbff; border:1px solid #d9edff; border-radius:12px; padding:11px; color:#526174; font-size:12px; }
    [data-testid="stSidebar"] { background:#fff; border-right:1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color:#111827!important; }
    @media(max-width:600px){ .block-container{padding-left:.65rem!important;padding-right:.65rem!important;} .stButton button{width:100%;} }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_connection():
    c = sqlite3.connect(DATABASE)
    c.row_factory = sqlite3.Row
    return c


def init_database():
    with get_connection() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS fundstuecke (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kategorie TEXT NOT NULL,
            ort TEXT NOT NULL,
            datum TEXT NOT NULL,
            beschreibung TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Gefunden',
            latitude REAL,
            longitude REAL,
            foto TEXT,
            ai_label TEXT,
            ai_confidence REAL
        )""")
        cols = {r["name"] for r in c.execute("PRAGMA table_info(fundstuecke)").fetchall()}
        for name, typ in [("latitude", "REAL"), ("longitude", "REAL"), ("foto", "TEXT"), ("ai_label", "TEXT"), ("ai_confidence", "REAL")]:
            if name not in cols:
                c.execute(f"ALTER TABLE fundstuecke ADD COLUMN {name} {typ}")


def add_item(name, category, location, found_date, description, lat, lon, photo, ai_label, ai_confidence):
    with get_connection() as c:
        c.execute("""INSERT INTO fundstuecke
        (name,kategorie,ort,datum,beschreibung,status,latitude,longitude,foto,ai_label,ai_confidence)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (name.strip(), category, location.strip(), found_date.isoformat(), description.strip(),
         "Gefunden", lat, lon, photo, ai_label, ai_confidence))


def get_items(search="", category="Alle", status="Alle"):
    sql = "SELECT * FROM fundstuecke WHERE 1=1"
    params = []
    if search.strip():
        sql += " AND (LOWER(name) LIKE ? OR LOWER(ort) LIKE ? OR LOWER(beschreibung) LIKE ?)"
        term = f"%{search.strip().lower()}%"
        params += [term, term, term]
    if category != "Alle":
        sql += " AND kategorie=?"; params.append(category)
    if status != "Alle":
        sql += " AND status=?"; params.append(status)
    sql += " ORDER BY id DESC"
    with get_connection() as c:
        return c.execute(sql, params).fetchall()


def update_status(item_id, status):
    with get_connection() as c:
        c.execute("UPDATE fundstuecke SET status=? WHERE id=?", (status, item_id))


def delete_item(item_id):
    with get_connection() as c:
        row = c.execute("SELECT foto FROM fundstuecke WHERE id=?", (item_id,)).fetchone()
        c.execute("DELETE FROM fundstuecke WHERE id=?", (item_id,))
    if row and row["foto"]:
        try: Path(row["foto"]).unlink(missing_ok=True)
        except Exception: pass


def stats():
    with get_connection() as c:
        return tuple(c.execute("SELECT COUNT(*) FROM fundstuecke WHERE status=?", (s,)).fetchone()[0] for s in STATUS), c.execute("SELECT COUNT(*) FROM fundstuecke").fetchone()[0]


@st.cache_resource(show_spinner=False)
def load_ai():
    if tf is None or not MODEL_PATH.exists():
        return None, []
    labels = []
    if LABEL_PATH.exists():
        for line in LABEL_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            # Unterstützt z. B. "0 Flaschen" genauso wie "Flaschen".
            parts = line.split(maxsplit=1)
            labels.append(parts[1].strip() if len(parts) == 2 and parts[0].isdigit() else line)

    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    return model, labels


def predict_fundstueck(uploaded_file):
    """Analysiert das hochgeladene Foto mit dem mitgelieferten Keras-Modell."""
    model, labels = load_ai()
    if model is None:
        raise RuntimeError(
            "KI-Modell nicht gefunden. Erwartet wird: ai_model/keras_model.h5"
        )

    # Die mitgelieferte KI erwartet 224x224 RGB-Bilder.
    image = Image.open(uploaded_file).convert("RGB").resize((224, 224))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    batch = np.expand_dims(arr, axis=0)

    prediction = model.predict(batch, verbose=0)
    prediction = np.asarray(prediction).squeeze()

    # Falls das Modell eine einzelne Zahl/mehrdimensionale Ausgabe liefert.
    if prediction.ndim != 1:
        prediction = prediction.reshape(-1)

    index = int(np.argmax(prediction))
    confidence = float(prediction[index])

    # Falls das Modell keine Wahrscheinlichkeiten ausgibt, trotzdem den
    # höchsten Klassenwert als Sicherheitswert anzeigen.
    confidence = max(0.0, min(1.0, confidence))

    label = labels[index] if index < len(labels) else f"Klasse {index}"
    return label, confidence


def create_map(items, selected=None):
    valid = [x for x in items if x["latitude"] is not None and x["longitude"] is not None]
    if selected and selected["latitude"] is not None and selected["longitude"] is not None:
        center = [selected["latitude"], selected["longitude"]]
    elif valid:
        center = [sum(x["latitude"] for x in valid)/len(valid), sum(x["longitude"] for x in valid)/len(valid)]
    else:
        center = [54.5215, 9.5586]
    fmap = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap", control_scale=True)
    for x in valid:
        color = "blue" if x["status"] == "Gefunden" else ("lightblue" if x["status"] == "Anfrage" else "gray")
        popup = f"<b>{x['name']}</b><br>{x['kategorie']}<br>📍 {x['ort']}<br>📅 {x['datum']}<br>Status: {x['status']}"
        folium.Marker([x["latitude"], x["longitude"]], popup=folium.Popup(popup, max_width=260), tooltip=x["name"], icon=folium.Icon(color=color, icon="info-sign")).add_to(fmap)
    return fmap


init_database()

with st.sidebar:
    st.markdown("## 🔎 Fundbüro")
    page = st.radio("Bereich", ["Übersicht", "Fundstück melden", "Karte", "Verwaltung"])
    st.divider()
    st.caption("Mobile · Weiß · Schwarz · Hellblau")

st.markdown('<div class="hero"><h1>Fundbüro</h1><p>Fundstücke fotografieren, per KI erkennen und Fundorte speichern.</p></div>', unsafe_allow_html=True)

model_available = tf is not None and MODEL_PATH.exists() and LABEL_PATH.exists()
if model_available:
    st.markdown(
        '<div class="ai-card"><div class="ai-title">🤖 KI aktiv</div>'
        '<div class="ai-text">Das mitgelieferte Modell wird beim Foto-Upload automatisch verwendet.</div></div>',
        unsafe_allow_html=True,
    )
else:
    st.warning("KI-Modell nicht verfügbar. Prüfe ai_model/keras_model.h5 und TensorFlow.")

if page == "Übersicht":
    (found, requests, returned), total = stats()
    st.markdown('<div class="section-title">Übersicht</div>', unsafe_allow_html=True)
    a,b = st.columns(2)
    for col, label, value in [(a,"Alle",total),(b,"Gefunden",found)]:
        with col: st.markdown(f'<div class="metric"><small>{label}</small><strong>{value}</strong></div>', unsafe_allow_html=True)
    st.write("")
    a,b = st.columns(2)
    for col, label, value in [(a,"Anfragen",requests),(b,"Abgeholt",returned)]:
        with col: st.markdown(f'<div class="metric"><small>{label}</small><strong>{value}</strong></div>', unsafe_allow_html=True)
    st.write("")
    search = st.text_input("🔍 Suche", placeholder="Gegenstand oder Fundort …")
    a,b = st.columns(2)
    with a: status = st.selectbox("Status", ["Alle"] + STATUS)
    with b: category = st.selectbox("Kategorie", ["Alle"] + KATEGORIEN)
    items = get_items(search, category, status)
    st.markdown(f'<div class="section-title">Fundstücke ({len(items)})</div>', unsafe_allow_html=True)
    for item in items:
        st.markdown(f'<div class="card"><div class="item-title">{item["name"]}</div><p><span class="badge">{item["kategorie"]}</span> <span class="badge">{item["status"]}</span></p><div class="item-meta">📍 {item["ort"]}<br>📅 {item["datum"]} · ID #{item["id"]}</div><p>{item["beschreibung"]}</p></div>', unsafe_allow_html=True)
        if item["foto"] and Path(item["foto"]).exists(): st.image(item["foto"], use_container_width=True)
        a,b = st.columns(2)
        with a:
            if item["status"] != "Abgeholt" and st.button("✓ Abgeholt", key=f"r{item['id']}"): update_status(item["id"], "Abgeholt"); st.rerun()
        with b:
            if item["status"] == "Gefunden" and st.button("Anfrage", key=f"q{item['id']}"): update_status(item["id"], "Anfrage"); st.rerun()
        if st.button("Löschen", key=f"d{item['id']}"): delete_item(item["id"]); st.rerun()
        st.divider()

elif page == "Fundstück melden":
    st.markdown('<div class="section-title">Fundstück melden</div>', unsafe_allow_html=True)
    st.markdown('<div class="info">📷 Foto hochladen oder am Smartphone direkt mit der Kamera aufnehmen. Die integrierte KI erkennt aktuell Flaschen, Hosen, Jacken und Federtaschen.</div>', unsafe_allow_html=True)

    photo = st.file_uploader("📷 Foto der Fundsache", type=["jpg","jpeg","png","webp"], accept_multiple_files=False)
    ai_label = None; ai_confidence = None
    if photo is not None:
        st.image(photo, caption="Foto", use_container_width=True)
        with st.spinner("KI analysiert die Fundsache …"):
            try: ai_label, ai_confidence = predict_fundstueck(photo)
            except Exception as e: st.error(f"KI konnte das Bild nicht analysieren: {e}")
        if ai_label:
            mapped = AI_TO_CATEGORY.get(ai_label, "Sonstiges")
            st.markdown(f'<div class="ai-card"><div class="ai-title">🤖 KI-Erkennung: {ai_label}</div><div class="ai-text">Erkennungswahrscheinlichkeit: {ai_confidence:.1%}<br>Kategorie-Vorschlag: <b>{mapped}</b></div></div>', unsafe_allow_html=True)

    with st.form("new_item_form"):
        default_cat = AI_TO_CATEGORY.get(ai_label, "Sonstiges") if ai_label else "Sonstiges"
        category = st.selectbox("Kategorie *", KATEGORIEN, index=KATEGORIEN.index(default_cat))
        name = st.text_input("Gegenstand *", value=ai_label or "", placeholder="z. B. Schwarze Jacke")
        location = st.text_input("Fundort *", placeholder="z. B. Bahnhof Schleswig")
        found_date = st.date_input("Funddatum *", value=date.today())
        description = st.text_area("Beschreibung *", placeholder="Farbe, Marke, besondere Merkmale …", height=100)
        st.markdown("**📍 Fundort auf der Karte**")
        a,b = st.columns(2)
        with a: lat = st.number_input("Breitengrad", -90.0, 90.0, 54.5215, 0.0001, format="%.4f")
        with b: lon = st.number_input("Längengrad", -180.0, 180.0, 9.5586, 0.0001, format="%.4f")
        submitted = st.form_submit_button("Fundstück speichern", type="primary", use_container_width=True)

    if submitted:
        if not name.strip() or not location.strip() or not description.strip(): st.error("Bitte Gegenstand, Fundort und Beschreibung ausfüllen.")
        else:
            saved = None
            if photo is not None:
                suffix = Path(photo.name).suffix.lower() or ".jpg"
                filename = f"fund_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S_%f')}{suffix}"
                path = UPLOAD_DIR / filename
                path.write_bytes(photo.getbuffer()); saved = str(path)
            add_item(name, category, location, found_date, description, lat, lon, saved, ai_label, ai_confidence)
            st.success("Fundstück gespeichert.")
            st.rerun()

elif page == "Karte":
    st.markdown('<div class="section-title">🗺️ Fundorte</div>', unsafe_allow_html=True)
    if folium is None or st_folium is None:
        st.error("Für die Karte fehlen folium und streamlit-folium.")
    else:
        items = get_items()
        fmap = create_map(items)
        st_folium(fmap, width=520, height=560, returned_objects=[])
        st.markdown('<div class="info">🔵 Gefunden · Hellblau = Anfrage · Grau = Abgeholt</div>', unsafe_allow_html=True)

elif page == "Verwaltung":
    st.markdown('<div class="section-title">Verwaltung</div>', unsafe_allow_html=True)
    items = get_items()
    if items:
        data = pd.DataFrame([dict(x) for x in items])
        data = data[["id","name","kategorie","ort","datum","status","ai_label","ai_confidence","latitude","longitude","foto"]]
        data.columns = ["ID","Name","Kategorie","Fundort","Datum","Status","KI-Erkennung","KI-Sicherheit","Breitengrad","Längengrad","Foto"]
        st.dataframe(data, use_container_width=True, hide_index=True)
        st.download_button("⬇️ CSV exportieren", data=data.to_csv(index=False).encode("utf-8-sig"), file_name="fundstuecke.csv", mime="text/csv", use_container_width=True)
    else: st.info("Noch keine Fundstücke vorhanden.")
