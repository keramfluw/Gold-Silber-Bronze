# Begehungs-App (Streamlit)

Eine leichte Field-App für die Aufnahme von Kundenanlagen und technischen Begehungen
– mit modularen Varianten (Bronze/Silber/Gold), CSV-Upload und Export.

## Features
- Kundendaten & Objektdaten aufnehmen
- Varianten beliebig kombinieren (Bronze / Silber / Gold)
- Dynamische Checkliste pro Begehung (editierbar per `st.data_editor`)
- CSV-Upload zum Import vorhandener Datensätze
- Export als CSV oder XLSX
- Bearbeitung der Vorlagen/Checklisten je Variante

## Start
```bash
pip install -r requirements.txt
streamlit run app.py
```