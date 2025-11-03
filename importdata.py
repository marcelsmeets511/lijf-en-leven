#!/usr/bin/env python3
"""
Importeert clienten.csv en tarieven.csv naar Supabase.
Upsert = insert bij nieuw, update bij conflict (unique keys).
"""

import os
import csv
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------- ENV ----------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ---------- SUPABASE CLIENT ----------
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- PADEN ----------
CLIENTEN_CSV = Path("data/clienten.csv")
TARIEVEN_CSV = Path("data/tarieven.csv")

# ---------- HELPERS ----------
def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Converteer DataFrame naar lijst met dicts, NaN → None."""
    return df.where(pd.notnull(df), None).to_dict(orient="records")

def parse_date(d):
    if not d:
        return None
    try:
        return pd.to_datetime(d, dayfirst=True).date()
    except Exception:
        return None

# ---------- TARIEVEN ----------
def import_tarieven():
    print("Importeren tarieven...")
    df = pd.read_csv(TARIEVEN_CSV, delimiter=";", decimal=",")
    records = df_to_records(df)

    for rec in records:
        row = {
            "item": rec.get("item"),
            "bedrag": float(rec.get("bedrag", 0)),
            "btw_incl_pct": float(rec.get("BTW (incl) in %", 0)),
            "omschrijving_op_factuur": rec.get("omschrijving op factuur"),
        }
        sb.table("tarieven").upsert(row).execute()
    print("✅ Tarieven geïmporteerd")

# ---------- CLIENTEN ----------
def import_clienten():
    print("Importeren clienten...")

    resp = sb.table("clienten").select("klant_id").execute()
    bestaande_ids = {int(r["klant_id"]) for r in resp.data if str(r["klant_id"]).isdigit()}
    max_id = max(bestaande_ids, default=0)
    nieuw_id = max_id + 1

    df = pd.read_csv(CLIENTEN_CSV, delimiter=";", decimal=",")
    records = df_to_records(df)

    for rec in records:
        raw_klant_id = rec.get("Klant-ID")

        # 1. Zorg dat we een string hebben voor de check
        str_id = str(raw_klant_id) if raw_klant_id is not None else ""
        if not str_id or (str_id.isdigit() and int(str_id) in bestaande_ids):
            rec["Klant-ID"] = str(nieuw_id)
            nieuw_id += 1
            bestaande_ids.add(int(rec["Klant-ID"]))

        row = {
            "naam_client": rec.get("naam client"),
            "straatnaam": rec.get("Straatnaam"),
            "postcode": rec.get("Postcode"),
            "woonplaats": rec.get("Woonplaats"),
            "land": rec.get("Land") or "Nederland",
            "telefoonnr": rec.get("Telefoonnr."),
            "geboorte_datum": rec.get("Geb.datum"),
            "bsn_nr": rec.get("BSN.nr."),
            "verzekeraar": rec.get("verzekeraar"),
            "polis_nr": rec.get("polis.nr."),
            "standaard_tarief": rec.get("standaard-tarief"),
            "aanhef": rec.get("aanhef"),
            "klant_id": rec.get("Klant-ID"),
            "emailadres": rec.get("Emailadres"),
            "taal": rec.get("taal") or "NL",
            "intake_datum": rec.get("intake-datum"),
            "laatste_factuurnr": rec.get("laatste factuurnr"),
            "product": rec.get("product"),
            "specifiek": rec.get("specifiek"),
            "praktijknaam": rec.get("Praktijknaam"),
            "huisarts": rec.get("Huisarts "),
            "huisarts_adres": rec.get("adres"),
            "huisarts_postcode": rec.get("postcode.1"),
            "huisarts_woonplaats": rec.get("woonplaats.1"),
            "huisarts_tel_nr": rec.get("huisarts tel.nr."),
            "huisarts_email": rec.get("huisarts Email"),
            "hoe_terecht_gekomen": rec.get("hoe terecht gekomen?"),
            "inlichten_jn": rec.get("inlichten J/N"),
            "nieuwsbrief": rec.get("Nieuwsbrief"),
        }
        sb.table("clienten").upsert(row).execute()
    print("✅ Clienten geïmporteerd (dubbele klant_id’s automatisch vervangen)")

# ---------- MAIN ----------
if __name__ == "__main__":
    #import_tarieven()
    import_clienten()
    print("🎉 Klaar – alle data staat in Supabase!")