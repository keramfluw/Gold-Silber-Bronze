import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Begehungs-App (PV/Technik)", layout="wide")

# ----------------------------
# Session state init
# ----------------------------
if "inspections" not in st.session_state:
    st.session_state.inspections = pd.DataFrame(columns=[
        "inspection_id","date","technician","customer_name","customer_email","customer_phone",
        "address","city","plz","bundesland","liegenschaftsnummer",
        "variant_combo","item_id","item_group","item_text","status","value","unit","notes"
    ])

if "templates" not in st.session_state:
    # Default checklist templates per variant
    st.session_state.templates = {
        "Bronze": [
            {"item_group":"Allgemein","item_text":"Zugang Dachflächen / Sicherheit (Geländer, Anschlagpunkte)","unit":"","default":"offen"},
            {"item_group":"PV/Elektrik","item_text":"Zählerschrank Zustand & Reserven","unit":"","default":"offen"},
            {"item_group":"PV/Elektrik","item_text":"Netzverknüpfungspunkt (Hausanschluss, NH, SLS)","unit":"","default":"offen"},
            {"item_group":"Gebäude","item_text":"Dachaufbau / Statik plausibel (Sichtprüfung)","unit":"","default":"offen"},
            {"item_group":"Dokumente","item_text":"Fotos/Skizze Dach (Ausrichtung, Hindernisse)","unit":"","default":"offen"},
        ],
        "Silber": [
            {"item_group":"PV/Elektrik","item_text":"Einspeisepunkt / Messkonzept (Vorprüfung)","unit":"","default":"offen"},
            {"item_group":"PV/Elektrik","item_text":"Leitungswege (Dach → Zählerschrank)","unit":"","default":"offen"},
            {"item_group":"Gebäude","item_text":"Dachhaut / Abdichtung (Material, Alter, Zustand)","unit":"","default":"offen"},
            {"item_group":"Gebäude","item_text":"Blitz-/Potenzialausgleich (Bestand)","unit":"","default":"offen"},
            {"item_group":"Dokumente","item_text":"Planauszüge, Fotos, Maße (Beleg)","unit":"","default":"offen"},
        ],
        "Gold": [
            {"item_group":"PV/Elektrik","item_text":"String-Layout & Wechselrichter-Standort (Vorplanung)","unit":"","default":"offen"},
            {"item_group":"PV/Elektrik","item_text":"Lastgänge / Verbrauchsstruktur (sofern vorhanden)","unit":"","default":"offen"},
            {"item_group":"Systeme","item_text":"Speicher / Ladeinfrastruktur / WP: Machbarkeit & Schnittstellen","unit":"","default":"offen"},
            {"item_group":"Regulatorik","item_text":"Messkonzept (GGV/Mieterstrom) – Detailaufnahme","unit":"","default":"offen"},
            {"item_group":"Risiken","item_text":"Sonderpunkte: Statik-Red Flags, Brandschutz, Denkmalschutz","unit":"","default":"offen"},
        ]
    }

# Helper to generate a new inspection id
def new_id(prefix="INS"):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{ts}"

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Ansicht wählen", [
    "Neue Begehung",
    "Bestand hochladen (CSV)",
    "Checklisten bearbeiten",
    "Datenexport / Reporting",
    "Hilfe"
])

# ----------------------------
# Page: Neue Begehung
# ----------------------------
if page == "Neue Begehung":
    st.title("📋 Neue Begehung aufnehmen")
    with st.form("form_begehung", clear_on_submit=False):
        st.subheader("Kundendaten & Objekt")
        cols = st.columns(3)
        customer_name = cols[0].text_input("Kunde / Ansprechpartner*in")
        customer_email = cols[1].text_input("E-Mail")
        customer_phone = cols[2].text_input("Telefon")

        colsa = st.columns(5)
        address = colsa[0].text_input("Adresse")
        city = colsa[1].text_input("Stadt")
        plz = colsa[2].text_input("PLZ")
        bundesland = colsa[3].text_input("Bundesland")
        liegenschaftsnummer = colsa[4].text_input("Liegenschaftsnummer")

        st.subheader("Begehung")
        cols2 = st.columns(3)
        date = cols2[0].date_input("Datum", value=datetime.today())
        technician = cols2[1].text_input("Techniker*in / Team")
        variants = cols2[2].multiselect("Variante(n) (frei kombinierbar)", ["Bronze","Silber","Gold"], default=["Bronze"])

        st.caption("Tipp: Varianten sind modular – wählen Sie beliebige Kombinationen (z. B. Bronze+Gold).")

        # Build the checklist from selected variants
        selected_templates = []
        for v in variants:
            selected_templates.extend(st.session_state.templates.get(v, []))

        # Deduplicate by item_text within same group
        seen = set()
        checklist_rows = []
        for idx, item in enumerate(selected_templates):
            key = (item["item_group"], item["item_text"])
            if key in seen:
                continue
            seen.add(key)
            checklist_rows.append({
                "item_group": item["item_group"],
                "item_text": item["item_text"],
                "status": item.get("default","offen"),
                "value": "",
                "unit": item.get("unit",""),
                "notes": ""
            })

        st.subheader("Checkliste")
        st.write("Markieren/ergänzen Sie die Punkte. Spalten sind editierbar.")
        edited_df = st.data_editor(
            pd.DataFrame(checklist_rows),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item_group": st.column_config.TextColumn("Gruppe"),
                "item_text": st.column_config.TextColumn("Prüfpunkt"),
                "status": st.column_config.SelectboxColumn("Status", options=["ok","offen","kritisch","n/a"]),
                "value": st.column_config.TextColumn("Wert/Messung"),
                "unit": st.column_config.TextColumn("Einheit"),
                "notes": st.column_config.TextColumn("Notizen"),
            },
            hide_index=True
        )

        submitted = st.form_submit_button("✅ Begehung speichern")
        if submitted:
            inspection_id = new_id()
            variant_combo = "+".join(variants) if variants else "keine"
            # Normalize into long rows
            records = []
            for i, row in edited_df.iterrows():
                records.append({
                    "inspection_id": inspection_id,
                    "date": pd.to_datetime(date),
                    "technician": technician,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "address": address, "city": city, "plz": plz, "bundesland": bundesland,
                    "liegenschaftsnummer": liegenschaftsnummer,
                    "variant_combo": variant_combo,
                    "item_id": f"ITM-{i+1:03d}",
                    "item_group": row["item_group"],
                    "item_text": row["item_text"],
                    "status": row["status"],
                    "value": row["value"],
                    "unit": row["unit"],
                    "notes": row["notes"],
                })
            if records:
                df_add = pd.DataFrame.from_records(records)
                st.session_state.inspections = pd.concat([st.session_state.inspections, df_add], ignore_index=True)
                st.success(f"Begehung **{inspection_id}** gespeichert ({len(records)} Zeilen).")

                # Offer export of this single inspection
                csv_bytes = df_add.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ CSV dieser Begehung", data=csv_bytes, file_name=f"{inspection_id}.csv", mime="text/csv")

# ----------------------------
# Page: Bestand hochladen (CSV)
# ----------------------------
elif page == "Bestand hochladen (CSV)":
    st.title("📤 CSV hochladen & zusammenführen")
    st.write("Erwartere Spalten (mindestens): inspection_id,date,technician,customer_name,address,city,plz,bundesland,liegenschaftsnummer,variant_combo,item_id,item_group,item_text,status,value,unit,notes")
    file = st.file_uploader("CSV-Datei wählen", type=["csv"])
    if file is not None:
        try:
            df_up = pd.read_csv(file)
            # Basic normalization
            if "date" in df_up.columns:
                df_up["date"] = pd.to_datetime(df_up["date"], errors="coerce")
            st.dataframe(df_up.head(), use_container_width=True)
            if st.button("🔗 In Bestand übernehmen"):
                st.session_state.inspections = pd.concat([st.session_state.inspections, df_up], ignore_index=True).drop_duplicates()
                st.success(f"{len(df_up)} Zeilen übernommen.")
        except Exception as e:
            st.error(f"Fehler beim Einlesen: {e}")

# ----------------------------
# Page: Checklisten bearbeiten
# ----------------------------
elif page == "Checklisten bearbeiten":
    st.title("🧩 Checklisten-Vorlagen je Variante")
    st.caption("Passen Sie die Vorlagen an. Diese steuern die generierte Checkliste für neue Begehungen.")
    variants_all = list(st.session_state.templates.keys())
    selected = st.selectbox("Variante wählen", variants_all, index=0)
    tmpl = st.session_state.templates[selected]

    df_tmpl = pd.DataFrame(tmpl)
    edited = st.data_editor(
        df_tmpl,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "item_group": st.column_config.TextColumn("Gruppe"),
            "item_text": st.column_config.TextColumn("Prüfpunkt"),
            "unit": st.column_config.TextColumn("Einheit"),
            "default": st.column_config.SelectboxColumn("Default-Status", options=["offen","ok","kritisch","n/a"]),
        },
        hide_index=True
    )
    colb = st.columns(3)
    if colb[0].button("💾 Vorlage speichern"):
        st.session_state.templates[selected] = edited.to_dict(orient="records")
        st.success("Vorlage aktualisiert.")
    csv_tmpl = edited.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Vorlage als CSV", data=csv_tmpl, file_name=f"vorlage_{selected.lower()}.csv", mime="text/csv")

# ----------------------------
# Page: Datenexport / Reporting
# ----------------------------
elif page == "Datenexport / Reporting":
    st.title("📦 Export & Reporting")
    df = st.session_state.inspections.copy()
    if df.empty:
        st.info("Noch keine Daten vorhanden.")
    else:
        colf = st.columns(4)
        tech_filter = colf[0].text_input("Filter Techniker*in enthält")
        city_filter = colf[1].text_input("Filter Stadt enthält")
        status_filter = colf[2].selectbox("Filter Status", ["(alle)","ok","offen","kritisch","n/a"], index=0)
        variant_filter = colf[3].text_input("Filter Varianten enthalten (z. B. Bronze+Gold)")

        mask = pd.Series([True]*len(df))
        if tech_filter:
            mask &= df["technician"].fillna("").str.contains(tech_filter, case=False, regex=False)
        if city_filter:
            mask &= df["city"].fillna("").str.contains(city_filter, case=False, regex=False)
        if status_filter != "(alle)":
            mask &= df["status"].fillna("") == status_filter
        if variant_filter:
            mask &= df["variant_combo"].fillna("").str.contains(variant_filter, case=False, regex=False)

        view = df.loc[mask].sort_values(["date","inspection_id","item_id"])
        st.write(f"**{len(view)}** Zeilen im Filter")
        st.dataframe(view, use_container_width=True, height=400)

        # Downloads
        csv_all = view.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Gefilterte Daten (CSV)", data=csv_all, file_name="begehungen_gefiltert.csv", mime="text/csv")

        # XLSX Export
        def to_xlsx_bytes(df_export: pd.DataFrame) -> bytes:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Begehungen")
            return output.getvalue()

        xlsx_bytes = to_xlsx_bytes(view)
        st.download_button("⬇️ Gefilterte Daten (XLSX)", data=xlsx_bytes, file_name="begehungen_gefiltert.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ----------------------------
# Page: Hilfe
# ----------------------------
elif page == "Hilfe":
    st.title("ℹ️ Hilfe & Struktur")
    st.markdown("""
Diese App erfasst Begehungen mit **modularen Varianten** (Bronze/Silber/Gold), die frei kombinierbar sind.
- **Neue Begehung:** Stammdaten eingeben, Varianten wählen, Checkliste im Editor ausfüllen, speichern & sofort als CSV exportieren.
- **Bestand hochladen (CSV):** Bereits erfasste Begehungen aus anderen Tools importieren.
- **Checklisten bearbeiten:** Vorlagen je Variante anpassen (Ihre Änderungen wirken sich auf neue Begehungen aus).
- **Datenexport/Reporting:** Filtern, CSV/XLSX exportieren.

**CSV-Felder (empfohlen):**
`inspection_id,date,technician,customer_name,customer_email,customer_phone,address,city,plz,bundesland,liegenschaftsnummer,variant_combo,item_id,item_group,item_text,status,value,unit,notes`

**Hinweise:**
- Die **Variante** steuert die initiale Checkliste – Sie können Punkte frei ergänzen/löschen.
- Statuswerte: `ok`, `offen`, `kritisch`, `n/a`.
- Export via „Datenexport/Reporting“ oder direkt nach dem Speichern.
    """)