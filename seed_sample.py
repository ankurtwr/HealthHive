"""
seed_sample.py  — run once to populate DB with test data
Usage: python seed_sample.py
"""
from app import create_app
from db import execute, query_all

MEDICINES = [
    ("Crocin 500mg",    "Paracetamol 500mg IP",                         "GSK",          "Analgesic / Antipyretic", "Tablet",  "500mg"),
    ("Dolo 650",        "Paracetamol 650mg IP",                         "Micro Labs",   "Analgesic / Antipyretic", "Tablet",  "650mg"),
    ("Calpol 500",      "Paracetamol 500mg IP",                         "GSK",          "Analgesic / Antipyretic", "Tablet",  "500mg"),
    ("Augmentin 625",   "Amoxicillin 500mg + Clavulanic Acid 125mg",    "GSK",          "Antibiotic",              "Tablet",  "625mg"),
    ("Ecosprin 75",     "Aspirin 75mg IP",                              "USV Ltd",      "Antiplatelet",            "Tablet",  "75mg"),
    ("Pantop 40",       "Pantoprazole 40mg IP",                         "Aristo Pharma","Proton Pump Inhibitor",   "Tablet",  "40mg"),
    ("Pan 40",          "Pantoprazole 40mg IP",                         "Alkem",        "Proton Pump Inhibitor",   "Tablet",  "40mg"),
    ("Lipitor 10",      "Atorvastatin 10mg IP",                         "Pfizer",       "Statin / Lipid Lowering", "Tablet",  "10mg"),
    ("Glycomet 500",    "Metformin Hydrochloride 500mg IP",             "USV Ltd",      "Antidiabetic",            "Tablet",  "500mg"),
    ("Azithral 500",    "Azithromycin 500mg IP",                        "Alembic",      "Antibiotic",              "Tablet",  "500mg"),
    ("Telma 40",        "Telmisartan 40mg IP",                          "Glenmark",     "Antihypertensive",        "Tablet",  "40mg"),
    ("Nexium 40",       "Esomeprazole 40mg IP",                         "AstraZeneca",  "Proton Pump Inhibitor",   "Tablet",  "40mg"),
]

GENERICS = [
    ("Paracetamol 500mg IP", "Paracetamol Tablet IP 500mg",  "PMBJP",       8.0,  "Strip of 10", "JanAushadhi", "PMBJP-001"),
    ("Paracetamol 500mg IP", "Paracetamol Tablet 500mg",     "Cipla",      10.0,  "Strip of 15", "CDSCO",       None),
    ("Paracetamol 500mg IP", "Paracetamol IP 500mg",         "Sun Pharma",  9.0,  "Strip of 10", "CDSCO",       None),
    ("Paracetamol 650mg IP", "Paracetamol Tablet IP 650mg",  "PMBJP",      10.0,  "Strip of 10", "JanAushadhi", "PMBJP-002"),
    ("Paracetamol 650mg IP", "Paracetamol 650mg",            "Cipla",      12.0,  "Strip of 10", "CDSCO",       None),
    ("Amoxicillin 500mg + Clavulanic Acid 125mg", "Amoxycillin + Clavulanate Tab", "PMBJP", 82.0, "Strip of 6", "JanAushadhi", "PMBJP-015"),
    ("Amoxicillin 500mg + Clavulanic Acid 125mg", "Amoxyclav 625",  "Cipla",  180.0, "Strip of 6", "CDSCO", None),
    ("Aspirin 75mg IP",      "Aspirin Tablet IP 75mg",       "PMBJP",       3.0,  "Strip of 14", "JanAushadhi", "PMBJP-010"),
    ("Aspirin 75mg IP",      "Aspirin 75mg",                 "Cipla",       7.0,  "Strip of 14", "CDSCO",       None),
    ("Pantoprazole 40mg IP", "Pantoprazole Tablet IP 40mg",  "PMBJP",      18.0,  "Strip of 10", "JanAushadhi", "PMBJP-030"),
    ("Pantoprazole 40mg IP", "Pantoprazole 40mg",            "Dr. Reddy's",45.0,  "Strip of 10", "CDSCO",       None),
    ("Atorvastatin 10mg IP", "Atorvastatin Tablet IP 10mg",  "PMBJP",      12.0,  "Strip of 10", "JanAushadhi", "PMBJP-040"),
    ("Atorvastatin 10mg IP", "Atorvastatin 10mg",            "Cipla",      28.0,  "Strip of 10", "CDSCO",       None),
    ("Metformin Hydrochloride 500mg IP", "Metformin Tablet IP 500mg", "PMBJP", 10.0, "Strip of 10", "JanAushadhi", "PMBJP-050"),
    ("Metformin Hydrochloride 500mg IP", "Metformin 500mg",  "Sun Pharma", 22.0,  "Strip of 10", "CDSCO",       None),
    ("Azithromycin 500mg IP","Azithromycin Tablet IP 500mg", "PMBJP",      35.0,  "Strip of 3",  "JanAushadhi", "PMBJP-020"),
    ("Azithromycin 500mg IP","Azithromycin 500mg",           "Cipla",      55.0,  "Strip of 3",  "CDSCO",       None),
    ("Telmisartan 40mg IP",  "Telmisartan Tablet IP 40mg",   "PMBJP",      14.0,  "Strip of 10", "JanAushadhi", "PMBJP-060"),
    ("Telmisartan 40mg IP",  "Telmisartan 40mg",             "Cipla",      30.0,  "Strip of 10", "CDSCO",       None),
    ("Esomeprazole 40mg IP", "Esomeprazole Tablet IP 40mg",  "PMBJP",      22.0,  "Strip of 10", "JanAushadhi", "PMBJP-031"),
    ("Esomeprazole 40mg IP", "Esomeprazole 40mg",            "Sun Pharma", 58.0,  "Strip of 10", "CDSCO",       None),
]

def seed():
    app = create_app()
    with app.app_context():
        print("Clearing old data...")
        execute("DELETE FROM price_cache")
        execute("DELETE FROM generics")
        execute("DELETE FROM medicines")

        print(f"Inserting {len(MEDICINES)} medicines...")
        for m in MEDICINES:
            execute("""
                INSERT INTO medicines
                (brand_name, salt_composition, manufacturer, category, dosage_form, strength, source)
                VALUES (%s,%s,%s,%s,%s,%s,'CDSCO')
            """, m)

        print(f"Inserting {len(GENERICS)} generics...")
        for g in GENERICS:
            execute("""
                INSERT INTO generics
                (salt_composition, generic_name, manufacturer, mrp, pack_size, source, jan_aushadhi_code)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, g)

        print("Done! DB seeded successfully.")

if __name__ == '__main__':
    seed()