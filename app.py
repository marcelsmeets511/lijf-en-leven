# app.py
import os
from datetime import date
from flask import Flask, render_template, request, redirect, jsonify
from flask_mail import Mail
from dotenv import load_dotenv          # ← nieuw
from supabase import create_client, Client
from flask import request, jsonify, render_template
from math import ceil

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
# ---------- PAGINERING ----------
PER_PAGE = 50

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

# ---------- CRUD BEWERKEN ----------
@app.route("/clientenbewerken")
def clientenbewerken():
    mode = request.args.get("mode", "form")          # form | table
    page = int(request.args.get("page", 1))
    if mode == "table":
        total = sb.table("clienten").select("*", count="exact").execute().count
        pages = ceil(total / PER_PAGE)
        offset = (page - 1) * PER_PAGE
        records = sb.table("clienten").select("*").range(offset, offset + PER_PAGE - 1).execute().data
        return render_template("clientenform.html", mode="table", records=records, page=page, pages=pages)
    return render_template("clientenform.html", mode="form")

@app.route("/tarievenbewerken")
def tarievenbewerken():
    return render_template("tarievenform.html")

@app.route("/overzichtbewerken")
def overzichtbewerken():
    return render_template("overzichtform.html")

# ---------- API: ZOEKEN ----------
@app.post("/api/zoek/<tabel>")
def api_zoek(tabel):
    data = request.json
    veld = data["veld"]
    waarde = data["waarde"]
    resp = sb.table(tabel).select("*").ilike(veld, f"%{waarde}%").execute()
    return jsonify(resp.data)

# ---------- API: OPSLAAN ----------
@app.post("/api/opslaan/<tabel>")
def api_opslaan(tabel):
    data = request.json
    # UUID kolom heet altijd "id"
    if "id" in data and data["id"]:
        sb.table(tabel).update(data).eq("id", data["id"]).execute()
    else:
        resp = sb.table(tabel).insert(data).execute()
        data["id"] = resp.data[0]["id"]
    return jsonify(data)

# ---------- API: VERWIJDEREN ----------
@app.post("/api/verwijder/<tabel>")
def api_verwijder(tabel):
    data = request.json
    sb.table(tabel).delete().eq("id", data["id"]).execute()
    return jsonify({"status": "ok"})

# ---------- API: RECORDS + NAVIGATIE ----------
@app.get("/api/records/<tabel>")
def api_records(tabel):
    resp = sb.table(tabel).select("*").order("id").execute()
    return jsonify(resp.data)

@app.get("/api/record/<tabel>/<int:index>")
def api_record(tabel, index):
    resp = sb.table(tabel).select("*").order("id").execute()
    if 0 <= index < len(resp.data):
        return jsonify(resp.data[index])
    return jsonify({})

# ---------- START FLASK ----------
if __name__ == "__main__":
    app.run(debug=True)