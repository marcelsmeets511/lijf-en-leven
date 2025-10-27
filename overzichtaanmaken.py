# overzichtaanmaken.py
import os
from datetime import date, datetime
from decimal import Decimal
from supabase import create_client, Client
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

# ---------- CONFIG ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "facturen_templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# ---------- HELPERS ----------
def create_uniq_name_list(rows, col_name="naam"):
    seen = set()
    unique = []
    for r in rows:
        val = r[col_name].strip() if r[col_name] else ""
        if val and val not in seen:
            seen.add(val)
            unique.append(val)
    return unique

# ---------- PDF GENERATOR ----------
def generate_overzicht_pdf(overzicht_rows, totaal_ex, totaal_btw, totaal_inc):
    template = jinja_env.get_template("overzicht.html")
    html_out = template.render(
        overzicht=overzicht_rows,
        totaal_ex=totaal_ex,
        totaal_btw=totaal_btw,
        totaal_inc=totaal_inc,
        datum_vandaag=date.today().strftime("%d-%m-%Y")
    )

    os.makedirs("output", exist_ok=True)
    pdf_path = "output/overzicht_consulten.pdf"
    HTML(string=html_out).write_pdf(pdf_path)
    return pdf_path

# ---------- MAIN ROUTINE ----------
def overzichtaanmaken():
    reccounter = somcounter = 0
    overzichtrecord = []
    sommenlijst = []

    rows = sb.table("overzicht").select("*").order("datum_dienst").execute().data
    unamelist = create_uniq_name_list(rows, "naam")
    tarieven = {t["item"]: float(t["btw_incl_pct"]) for t in sb.table("tarieven").select("*").execute().data}

    for uname in unamelist:
        if not uname.strip():
            continue
        beginrij = reccounter + 6
        for r in rows:
            if r["naam"] != uname:
                continue
            datum = r["datum_dienst"]
            dag = f"{datum.day:02d}"
            maand = f"{datum.month:02d}"
            jaar = str(datum.year)

            record = {
                "datum": f"{dag}-{maand}-{jaar}",
                "naam_client": r["naam"],
                "tijd": str(r["tijd"]),
                "contant": "Ja" if r["contant"] else "Nee",
                "te_ontvangen": float(r["te_ontvangen"]),
                "opmerking": r["opmerking"] or "",
                "bedrag_exbtw": 0.0,
                "btw": 0.0,
                "factuurbedrag": 0.0,
                "factuurnummer": r["factuurnummer"] or "",
                "datum_ontvangst": r["datum_factuur"].strftime("%d-%m-%Y") if r["datum_factuur"] else ""
            }

            tarief_code = r["opmerking"] or ""
            btw_pct = tarieven.get(tarief_code, 21.0)
            bedrag_incl = float(r["bedrag"])
            bedrag_ex = bedrag_incl / (100 + btw_pct) * 100
            btw = bedrag_incl - bedrag_ex

            record["bedrag_exbtw"] = round(bedrag_ex, 2)
            record["btw"] = round(btw, 2)
            record["factuurbedrag"] = round(bedrag_incl, 2)

            overzichtrecord.append(record)
            reccounter += 1

        # SUBTOTAAL REGEL
        eindrij = reccounter + 6
        overzichtrecord.append({
            "datum": "",
            "naam_client": "",
            "tijd": "",
            "contant": "",
            "te_ontvangen": "",
            "opmerking": "",
            "bedrag_exbtw": round(sum(r["bedrag_exbtw"] for r in overzichtrecord[beginrij-6:eindrij-6]), 2),
            "btw": round(sum(r["btw"] for r in overzichtrecord[beginrij-6:eindrij-6]), 2),
            "factuurbedrag": round(sum(r["factuurbedrag"] for r in overzichtrecord[beginrij-6:eindrij-6]), 2),
            "factuurnummer": "",
            "datum_ontvangst": ""
        })
        sommenlijst.append(reccounter + 6)
        somcounter += 1
        reccounter += 1
        overzichtrecord.append({
            "datum": "",
            "naam_client": "",
            "tijd": "",
            "contant": "",
            "te_ontvangen": "",
            "opmerking": "",
            "bedrag_exbtw": "",
            "btw": "",
            "factuurbedrag": "",
            "factuurnummer": "",
            "datum_ontvangst": ""
        })
        reccounter += 1

    # TOTAAL REGEL
    totaal_ex = round(sum(r["bedrag_exbtw"] for r in overzichtrecord if isinstance(r["bedrag_exbtw"], float)), 2)
    totaal_btw = round(sum(r["btw"] for r in overzichtrecord if isinstance(r["btw"], float)), 2)
    totaal_inc = round(sum(r["factuurbedrag"] for r in overzichtrecord if isinstance(r["factuurbedrag"], float)), 2)

    overzichtrecord.append({
        "datum": "TOTAAL",
        "naam_client": "",
        "tijd": "",
        "contant": "",
        "te_ontvangen": "",
        "opmerking": "",
        "bedrag_exbtw": totaal_ex,
        "btw": totaal_btw,
        "factuurbedrag": totaal_inc,
        "factuurnummer": "",
        "datum_ontvangst": ""
    })

    # GENEREER PDF
    pdf_path = generate_overzicht_pdf(overzichtrecord, totaal_ex, totaal_btw, totaal_inc)
    print(f"Overzicht PDF gegenereerd: {pdf_path}")

# ---------- DIRECT UITVOEREN ----------
if __name__ == "__main__":
    overzichtaanmaken()