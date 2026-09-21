from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = "fundbuero.db"


# ============================================================
# DATENBANK
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def datenbank_erstellen():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fundstuecke (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kategorie TEXT NOT NULL,
            ort TEXT NOT NULL,
            datum TEXT NOT NULL,
            beschreibung TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Gefunden',
            erstellt_am TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Datenbank beim Start erstellen
datenbank_erstellen()


# ============================================================
# HTML
# ============================================================

HTML = """
<!DOCTYPE html>
<html lang="de">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Fundbüro App</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
        }

        header {
            background: #0f172a;
            color: white;
            padding: 25px 15px;
            text-align: center;
        }

        header h1 {
            margin: 0;
            font-size: 32px;
        }

        header p {
            margin-bottom: 0;
            color: #cbd5e1;
        }

        .container {
            width: 95%;
            max-width: 1000px;
            margin: 25px auto;
        }

        .box {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }

        .box h2 {
            margin-top: 0;
        }

        input,
        select,
        textarea {
            width: 100%;
            padding: 12px;
            margin-top: 6px;
            margin-bottom: 15px;

            border: 1px solid #cbd5e1;
            border-radius: 8px;

            font-size: 16px;
        }

        textarea {
            min-height: 100px;
            resize: vertical;
        }

        button,
        .button {
            display: inline-block;

            border: none;
            border-radius: 8px;

            padding: 12px 18px;

            background: #2563eb;
            color: white;

            font-size: 16px;
            font-weight: bold;

            cursor: pointer;
            text-decoration: none;
        }

        button:hover,
        .button:hover {
            background: #1d4ed8;
        }

        .button-red {
            background: #dc2626;
        }

        .button-red:hover {
            background: #b91c1c;
        }

        .fundstueck {
            background: white;

            border-radius: 15px;

            padding: 20px;

            margin-bottom: 15px;

            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }

        .fundstueck h3 {
            margin-top: 0;
            font-size: 23px;
        }

        .status {
            display: inline-block;

            padding: 6px 12px;

            border-radius: 20px;

            background: #dcfce7;
            color: #166534;

            font-size: 14px;
            font-weight: bold;
        }

        .status-abgeholt {
            background: #e2e8f0;
            color: #475569;
        }

        .status-anfrage {
            background: #fef3c7;
            color: #92400e;
        }

        .info {
            color: #64748b;
        }

        .leer {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }

        .meldung {
            padding: 15px;

            background: #dcfce7;
            color: #166534;

            border-radius: 10px;

            margin-bottom: 20px;
        }

        .fehler {
            padding: 15px;

            background: #fee2e2;
            color: #991b1b;

            border-radius: 10px;

            margin-bottom: 20px;
        }

        .aktionen {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;

            margin-top: 15px;
        }

        footer {
            text-align: center;
            padding: 30px;
            color: #64748b;
        }

        @media (max-width: 600px) {

            header h1 {
                font-size: 26px;
            }

            .container {
                width: 92%;
            }

            .box,
            .fundstueck {
                padding: 16px;
            }

            .aktionen {
                flex-direction: column;
            }

            .aktionen .button,
            .aktionen button {
                width: 100%;
                text-align: center;
            }

        }

    </style>

</head>


<body>


<header>

    <h1>🔎 Fundbüro</h1>

    <p>
        Verlorene Gegenstände schnell wiederfinden
    </p>

</header>


<div class="container">


    {% if meldung %}

        <div class="meldung">
            {{ meldung }}
        </div>

    {% endif %}


    {% if fehler %}

        <div class="fehler">
            {{ fehler }}
        </div>

    {% endif %}


    <!-- SUCHEN -->

    <div class="box">

        <h2>🔍 Fundstücke suchen</h2>

        <form method="GET" action="/">

            <input
                type="text"
                name="suche"
                placeholder="z.B. iPhone, Schlüssel, Bahnhof..."
                value="{{ suche }}"
            >

            <select name="kategorie">

                <option value="">
                    Alle Kategorien
                </option>

                {% for kategorie in kategorien %}

                    <option
                        value="{{ kategorie }}"
                        {% if kategorie == ausgewaehlte_kategorie %}
                            selected
                        {% endif %}
                    >
                        {{ kategorie }}
                    </option>

                {% endfor %}

            </select>


            <select name="status">

                <option value="">
                    Alle Status
                </option>

                <option
                    value="Gefunden"
                    {% if status == "Gefunden" %}
                        selected
                    {% endif %}
                >
                    Gefunden
                </option>

                <option
                    value="Anfrage"
                    {% if status == "Anfrage" %}
                        selected
                    {% endif %}
                >
                    Anfrage
                </option>

                <option
                    value="Abgeholt"
                    {% if status == "Abgeholt" %}
                        selected
                    {% endif %}
                >
                    Abgeholt
                </option>

            </select>


            <button type="submit">
                🔎 Suchen
            </button>

        </form>

    </div>


    <!-- NEUES FUNDSTÜCK -->

    <div class="box">

        <h2>➕ Fundstück melden</h2>

        <form
            method="POST"
            action="/hinzufuegen"
        >

            <label>
                <strong>Name des Gegenstands</strong>
            </label>

            <input
                type="text"
                name="name"
                placeholder="z.B. Schwarzes iPhone"
                required
            >


            <label>
                <strong>Kategorie</strong>
            </label>

            <select
                name="kategorie"
                required
            >

                {% for kategorie in kategorien %}

                    <option value="{{ kategorie }}">
                        {{ kategorie }}
                    </option>

                {% endfor %}

            </select>


            <label>
                <strong>Fundort</strong>
            </label>

            <input
                type="text"
                name="ort"
                placeholder="z.B. Bahnhof Schleswig"
                required
            >


            <label>
                <strong>Funddatum</strong>
            </label>

            <input
                type="date"
                name="datum"
                required
            >


            <label>
                <strong>Beschreibung</strong>
            </label>

            <textarea
                name="beschreibung"
                placeholder="Beschreibe den Gegenstand..."
                required
            ></textarea>


            <button type="submit">
                💾 Fundstück speichern
            </button>

        </form>

    </div>


    <!-- LISTE -->

    <div class="box">

        <h2>
            📦 Fundstücke
            ({{ fundstuecke|length }})
        </h2>


        {% if fundstuecke %}


            {% for item in fundstuecke %}

                <div class="fundstueck">

                    <h3>
                        {{ item["name"] }}
                    </h3>


                    {% if item["status"] == "Gefunden" %}

                        <span class="status">
                            🟢 Gefunden
                        </span>

                    {% elif item["status"] == "Anfrage" %}

                        <span class="status status-anfrage">
                            🟡 Anfrage
                        </span>

                    {% else %}

                        <span class="status status-abgeholt">
                            ⚪ Abgeholt
                        </span>

                    {% endif %}


                    <p>
                        <strong>Kategorie:</strong>
                        {{ item["kategorie"] }}
                    </p>


                    <p>
                        <strong>📍 Fundort:</strong>
                        {{ item["ort"] }}
                    </p>


                    <p>
                        <strong>📅 Funddatum:</strong>
                        {{ item["datum"] }}
                    </p>


                    <p>
                        <strong>Beschreibung:</strong><br>

                        {{ item["beschreibung"] }}

                    </p>


                    <p class="info">

                        Fundstück-ID:
                        <strong>
                            #{{ item["id"] }}
                        </strong>

                    </p>


                    <div class="aktionen">


                        {% if item["status"] != "Abgeholt" %}

                            <form
                                method="POST"
                                action="/abgeholt/{{ item['id'] }}"
                            >

                                <button type="submit">
                                    ✅ Als abgeholt markieren
                                </button>

                            </form>

                        {% endif %}


                        <form
                            method="POST"
                            action="/loeschen/{{ item['id'] }}"
                            onsubmit="return confirm('Möchtest du dieses Fundstück wirklich löschen?');"
                        >

                            <button
                                type="submit"
                                class="button-red"
                            >
                                🗑️ Löschen
                            </button>

                        </form>


                    </div>

                </div>

            {% endfor %}


        {% else %}

            <div class="leer">

                <h3>
                    🔎 Keine Fundstücke gefunden
                </h3>

                <p>
                    Versuche einen anderen Suchbegriff.
                </p>

            </div>

        {% endif %}

    </div>

</div>


<footer>

    Fundbüro App · Version 1.0

</footer>


</body>

</html>
"""


# ============================================================
# KATEGORIEN
# ============================================================

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
    "Sonstiges"
]


# ============================================================
# STARTSEITE
# ============================================================

@app.route("/", methods=["GET"])
def startseite():

    suche = request.args.get("suche", "").strip()
    kategorie = request.args.get("kategorie", "").strip()
    status = request.args.get("status", "").strip()


    conn = get_db()


    sql = """
        SELECT *
        FROM fundstuecke
        WHERE 1 = 1
    """

    parameter = []


    # Suche
    if suche:

        sql += """
            AND (
                LOWER(name) LIKE ?
                OR LOWER(beschreibung) LIKE ?
                OR LOWER(ort) LIKE ?
            )
        """

        suchbegriff = "%" + suche.lower() + "%"

        parameter.extend([
            suchbegriff,
            suchbegriff,
            suchbegriff
        ])


    # Kategorie
    if kategorie:

        sql += """
            AND kategorie = ?
        """

        parameter.append(kategorie)


    # Status
    if status:

        sql += """
            AND status = ?
        """

        parameter.append(status)


    sql += """
        ORDER BY id DESC
    """


    fundstuecke = conn.execute(
        sql,
        parameter
    ).fetchall()


    conn.close()


    return render_template_string(
        HTML,

        fundstuecke=fundstuecke,

        kategorien=KATEGORIEN,

        suche=suche,

        ausgewaehlte_kategorie=kategorie,

        status=status,

        meldung=request.args.get("meldung"),

        fehler=request.args.get("fehler")
    )


# ============================================================
# FUNDSTÜCK HINZUFÜGEN
# ============================================================

@app.route("/hinzufuegen", methods=["POST"])
def hinzufuegen():

    try:

        name = request.form.get("name", "").strip()
        kategorie = request.form.get("kategorie", "").strip()
        ort = request.form.get("ort", "").strip()
        datum = request.form.get("datum", "").strip()
        beschreibung = request.form.get(
            "beschreibung",
            ""
        ).strip()


        # Pflichtfelder überprüfen
        if not name:
            return redirect(
                url_for(
                    "startseite",
                    fehler="Bitte einen Namen eingeben."
                )
            )


        if not kategorie:
            return redirect(
                url_for(
                    "startseite",
                    fehler="Bitte eine Kategorie auswählen."
                )
            )


        if not ort:
            return redirect(
                url_for(
                    "startseite",
                    fehler="Bitte einen Fundort eingeben."
                )
            )


        if not datum:
            return redirect(
                url_for(
                    "startseite",
                    fehler="Bitte ein Datum auswählen."
                )
            )


        if not beschreibung:
            return redirect(
                url_for(
                    "startseite",
                    fehler="Bitte eine Beschreibung eingeben."
                )
            )


        conn = get_db()


        conn.execute(
            """
            INSERT INTO fundstuecke
            (
                name,
                kategorie,
                ort,
                datum,
                beschreibung,
                status,
                erstellt_am
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,

            (
                name,
                kategorie,
                ort,
                datum,
                beschreibung,
                "Gefunden",
                datetime.now().isoformat()
            )
        )


        conn.commit()
        conn.close()


        return redirect(
            url_for(
                "startseite",
                meldung="Fundstück wurde erfolgreich gespeichert."
            )
        )


    except Exception as e:

        print("Fehler beim Speichern:", e)

        return redirect(
            url_for(
                "startseite",
                fehler="Beim Speichern ist ein Fehler aufgetreten."
            )
        )


# ============================================================
# ALS ABGEHOLT MARKIEREN
# ============================================================

@app.route("/abgeholt/<int:item_id>", methods=["POST"])
def abgeholt(item_id):

    conn = get_db()


    conn.execute(
        """
        UPDATE fundstuecke
        SET status = ?
        WHERE id = ?
        """,
        ("Abgeholt", item_id)
    )


    conn.commit()
    conn.close()


    return redirect(
        url_for(
            "startseite",
            meldung="Fundstück wurde als abgeholt markiert."
        )
    )


# ============================================================
# FUNDSTÜCK LÖSCHEN
# ============================================================

@app.route("/loeschen/<int:item_id>", methods=["POST"])
def loeschen(item_id):

    conn = get_db()


    conn.execute(
        """
        DELETE FROM fundstuecke
        WHERE id = ?
        """,
        (item_id,)
    )


    conn.commit()
    conn.close()


    return redirect(
        url_for(
            "startseite",
            meldung="Fundstück wurde gelöscht."
        )
    )


# ============================================================
# APP STARTEN
# ============================================================

if __name__ == "__main__":

    print("")
    print("===================================")
    print("       FUNDBÜRO APP 1.0")
    print("===================================")
    print("")
    print("Die App läuft unter:")
    print("http://127.0.0.1:5000")
    print("")
    print("Zum Beenden: STRG + C")
    print("")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
