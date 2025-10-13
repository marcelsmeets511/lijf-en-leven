-- EXTENSIES
create extension if not exists "uuid-ossp";

-- 1. TARIEVEN
create table tarieven (
    id uuid primary key default gen_random_uuid(),
    item text unique,
    bedrag numeric(10,2),
    btw_incl_pct numeric(5,2),
    omschrijving_op_factuur text
);

-- 2. CLIENTEN
create table clienten (
    id uuid primary key default gen_random_uuid(),
    naam_client text,
    straatnaam text,
    postcode text,
    woonplaats text,
    land text default 'Nederland',
    telefoonnr text,
    geboorte_datum date,
    bsn_nr text unique,
    verzekeraar text,
    polis_nr text,
    standaard_tarief numeric(10,2),
    aanhef text,
    klant_id text unique,
    emailadres text,
    taal text default 'NL',
    intake_datum date,
    laatste_factuurnr text,
    product text,
    specifiek text,
    praktijknaam text,
    huisarts text,
    huisarts_adres text,
    huisarts_postcode text,
    huisarts_woonplaats text,
    huisarts_tel_nr text,
    huisarts_email text,
    hoe_terecht_gekomen text,
    inlichten_jn boolean,
    nieuwsbrief boolean default false
);

-- 3. OVERZICHT
create table overzicht (
    id uuid primary key default gen_random_uuid(),
    datum_dienst date,
    naam text,
    tijd time,
    contant boolean default false,
    te_ontvangen numeric(10,2),
    opmerking text,
    bedrag numeric(10,2),
    ex_btw numeric(10,2),
    btw_21_pct numeric(10,2),
    factuurbedrag numeric(10,2),
    factuurnummer text unique,
    datum_factuur date,
    ontvangst boolean default false,
    deb_nr text
);

-- INDEXES
create index idx_overzicht_factuurnummer on overzicht(factuurnummer);
create index idx_overzicht_datum_dienst on overzicht(datum_dienst);
create index idx_clienten_klant_id on clienten(klant_id);
create index idx_clienten_bsn on clienten(bsn_nr);
create index idx_tarieven_item on tarieven(item);
