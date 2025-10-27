# facturenaanmaken.py
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from supabase import create_client, Client
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from flask_mail import Message
from flask import Flask, send_file

app = Flask(__name__)

# ---------- CONFIG ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Jinja2 omgeving voor templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "facturen_templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# ---------- STUBS ----------
def mail_pdf(pdflist: list, mailcount: int) -> None:
    pass

# ---------- HELPERS ----------
def get_tarieven():
    rows = sb.table("tarieven").select("*").execute().data
    return [[r["item"], float(r["bedrag"]), float(r["btw_incl_pct"]), r["omschrijving_op_factuur"]] for r in rows]

def get_naw_data(namen: list):
    adres_lijst = []
    for naam in namen:
        c = sb.table("clienten").select("*").ilike("naam_client", naam).execute().data
        if c:
            c = c[0]
            adres_lijst.append([
                c["naam_client"], c["straatnaam"], c["postcode"], c["woonplaats"], c["land"],
                c["geboorte_datum"], c["bsn_nr"], c["verzekeraar"], c["polis_nr"], "", "",
                c["emailadres"], c["klant_id"]
            ])
    return adres_lijst

def get_adres(naam: str, adres_lijst: list):
    for adr in adres_lijst:
        if adr[0] == naam:
            return adr
    return [""] * 30

def get_tarief_naam(tarief_code: str, tarieven: list):
    for t in tarieven:
        if t[0] == tarief_code:
            return t[3]
    return ""

def get_tarief_bedrag(tarief_code: str, tarieven: list):
    for t in tarieven:
        if t[0] == tarief_code:
            return float(t[1])
    return 0.0

def register_last_invoices(invoices: list):
    for inv in invoices:
        sb.table("clienten").update({"laatste_factuurnr": inv[1]}).eq("naam_client", inv[0]).execute()

def voornaam(naam: str):
    return naam.split()[0] if " " in naam else naam

# ---------- PDF GENERATOR ----------
def generate_invoice_pdf(client, regels, totaal_btw, totaal_bedrag, contant=0, logo_path="static/images/logo.png"):
    template = jinja_env.get_template("factuur.html")
    html_out = template.render(
        logo=logo_path,
        naam_client=client["naam"],
        straat=client["straat"],
        postcode=client["postcode"],
        woonplaats=client["woonplaats"],
        land=client["land"],
        factuurnummer=client["factuurnummer"],
        deb_nr=client["deb_nr"],
        datum_vandaag=date.today().strftime("%d-%m-%Y"),
        regels=regels,
        totaal_btw=totaal_btw,
        totaal_bedrag=totaal_bedrag,
        contant=contant,
        nog_te_voldoen=totaal_bedrag - contant,
        betaaldatum=(date.today() + timedelta(days=14)).strftime("%d-%m-%Y")
    )

    os.makedirs("output", exist_ok=True)
    pdf_path = f"output/factuur_{client['factuurnummer']}.pdf"
    HTML(string=html_out).write_pdf(pdf_path)
    return pdf_path

# ---------- MAIN ROUTINE ----------
def facturenaanmaken():
    PAGESIZE = 51
    som1 = som2 = som3 = som4 = 0.0
    reccounter = faccounter = 0
    overzichtrecord = []
    factuurnrlist = []

    tarieven = get_tarieven()
    rows = sb.table("overzicht").select("*").order("datum_dienst").execute().data
    namen = list({r["naam"] for r in rows})
    adreslist = get_naw_data(namen)

    for uname in namen:
        if not uname.strip():
            continue
        beginrij = reccounter + 6
        for r in rows:
            if r["naam"] != uname:
                continue
            record = {
                "datum": r["datum_dienst"],
                "naam": r["naam"],
                "tijd": r["tijd"],
                "contant": r["contant"],
                "te_ontvangen": float(r["te_ontvangen"]),
                "opmerking": r["opmerking"],
                "bedrag": float(r["bedrag"]),
                "ex_btw": float(r["ex_btw"]),
                "btw": float(r["btw_21_pct"]),
                "factuurnummer": r["factuurnummer"],
                "deb_nr": r["deb_nr"]
            }
            overzichtrecord.append(record)
            som1 += float(r["te_ontvangen"])
            som2 += float(r["ex_btw"])
            som3 += float(r["btw_21_pct"])
            som4 += float(r["bedrag"])
            reccounter += 1

        overzichtrecord.append({
            "naam": "totaal",
            "te_ontvangen": som1,
            "ex_btw": som2,
            "btw": som3,
            "bedrag": som4
        })
        som1 = som2 = som3 = som4 = 0.0
        reccounter += 1

    huidigenaam = huidigefacnr = huidigtarief = ""
    pagina = 0

    for rec in overzichtrecord:
        if rec.get("naam") == "totaal":
            continue
        if rec["naam"] == "":
            continue

        if (huidigtarief == "persoonlijke begeleiding" and huidigenaam != rec["naam"]) or huidigefacnr != rec["factuurnummer"]:
            huidigadres = get_adres(rec["naam"], adreslist)
            huidigefacnr = rec["factuurnummer"]
            huidigtarief = get_tarief_naam(rec["opmerking"], tarieven)

            client = {
                "naam": rec["naam"],
                "straat": huidigadres[1],
                "postcode": huidigadres[2],
                "woonplaats": huidigadres[3],
                "land": huidigadres[4],
                "factuurnummer": rec["factuurnummer"],
                "deb_nr": rec["deb_nr"]
            }

            regels = []
            totaal_btw = 0.0
            totaal_bedrag = 0.0
            for r in overzichtrecord:
                if r.get("naam") == rec["naam"] and r.get("naam") != "totaal":
                    aantaluren = 1
                    if huidigtarief == "persoonlijke begeleiding":
                        if r["opmerking"] == "PGB2":
                            aantaluren = 2
                        elif r["opmerking"] == "PGB3":
                            aantaluren = 3
                    regels.append({
                        "datum": r["datum"].strftime("%d-%m-%Y"),
                        "omschrijving": huidigtarief,
                        "uren": aantaluren,
                        "tarief": get_tarief_bedrag("PGB1", tarieven),
                        "bedrag": float(r["bedrag"])
                    })
                    totaal_btw += float(r["btw"])
                    totaal_bedrag += float(r["bedrag"])

            pdf_path = generate_invoice_pdf(
                client=client,
                regels=regels,
                totaal_btw=totaal_btw,
                totaal_bedrag=totaal_bedrag,
                contant=0
            )

            factuurnrlist.append({
                "naam": rec["naam"],
                "factuurnummer": rec["factuurnummer"],
                "email": huidigadres[11] if len(huidigadres) > 11 else "",
                "pdf_path": pdf_path
            })
            faccounter += 1
            huidigenaam = rec["naam"]

    register_last_invoices([[r["naam"], r["factuurnummer"]] for r in factuurnrlist])

    if factuurnrlist:
        mail_pdf(factuurnrlist, len(factuurnrlist))

    print("Facturenaanmaken klaar!")

# ---------- DIRECT UITVOEREN ----------
if __name__ == "__main__":
    facturenaanmaken()