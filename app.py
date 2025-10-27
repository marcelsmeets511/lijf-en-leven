# app.py
import os
from datetime import date
from flask import Flask, render_template, request, redirect, jsonify
from flask_mail import Mail
from dotenv import load_dotenv          # ← nieuw
from supabase import create_client, Client

# ---------- LAAD .ENV BESTAND ----------
# zoekt naar .env in dezelfde map als dit script
load_dotenv()

# ---------- IMPORTEER JE EIGEN MODULES ----------
from facturenaanmaken import facturenaanmaken
from facturenprinten import facturenprinten
from overzichtaanmaken import overzichtaanmaken

# ---------- FLASK APP ----------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# ---------- CONFIG UIT .ENV ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.getenv("MAIL_USER")
MAIL_PASSWORD = os.getenv("MAIL_PASS")
MAIL_DEFAULT_SENDER = MAIL_USERNAME

mail = Mail(app)
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- HOME ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- SNELINVOEREN ----------
@app.route("/snelinvoeren")
def snelinvoeren():
    clients = sb.table("clienten").select("naam_client").execute().data
    tarieven = sb.table("tarieven").select("*").execute().data
    return render_template("snelinvoeren.html", clients=clients, tarieven=tarieven)

@app.post("/api/snelinvoeren")
def api_snelinvoeren():
    from decimal import Decimal
    data = request.form
    btw_pct = Decimal(data["btw_incl_pct"] or 21)
    bedrag_incl = Decimal(data["bedrag_incl"] or 0)
    bedrag_ex = bedrag_incl / (100 + btw_pct) * 100
    btw = bedrag_incl - bedrag_ex

    sb.table("overzicht").insert({
        "datum_dienst": data["datum"],
        "naam": data["naam"],
        "tijd": data["tijd"],
        "contant": data.get("contant") == "on",
        "te_ontvangen": data["te_ontvangen"],
        "opmerking": data["opmerking"],
        "bedrag": bedrag_incl,
        "ex_btw": bedrag_ex,
        "btw_21_pct": btw,
        "factuurbedrag": bedrag_incl,
        "factuurnummer": data["factuurnummer"],
        "datum_factuur": date.today(),
        "deb_nr": data["deb_nr"]
    }).execute()
    return redirect("/")

# ---------- FACTUREN AANMAKEN ----------
@app.route("/facturen/aanmaken")
def facturen_aanmaken():
    facturenaanmaken()
    return "Facturen aangemaakt (PDF gegenereerd)", 200

# ---------- FACTUREN PRINTEN ----------
@app.route("/facturen/printen")
def facturen_printen():
    facturenprinten()
    return "Facturen geprint (PDF gegenereerd)", 200

# ---------- OVERZICHT AANMAKEN ----------
@app.route("/overzicht/aanmaken")
def overzicht_aanmaken():
    overzichtaanmaken()
    return "Overzicht aangemaakt (PDF gegenereerd)", 200

# ---------- API HELPERS ----------
@app.get("/api/client/<naam>")
def api_client(naam):
    c = sb.table("clienten").select("*").ilike("naam_client", naam).execute().data
    return jsonify(c[0] if c else {})

# ---------- START FLASK ----------
if __name__ == "__main__":
    app.run(debug=True)