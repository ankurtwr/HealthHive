import sys
import os

# Add parent directory to path so we can import app and db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from db import execute

# Mocked realistic dataset of Jan Aushadhi medicines
PMBJP_GENERICS = [
    # ── Pain relief / Fever (Paracetamol, Ibuprofen, Diclofenac, Tramadol)
    ("Paracetamol 500mg IP", "Paracetamol Tablet IP 500mg", "PMBJP", 8.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-001"),
    ("Paracetamol 650mg IP", "Paracetamol Tablet IP 650mg", "PMBJP", 10.0, "Strip of 15 Tablets", "JanAushadhi", "PMBJP-002"),
    ("Aspirin 75mg IP", "Aspirin Tablet IP 75mg", "PMBJP", 3.0, "Strip of 14 Tablets", "JanAushadhi", "PMBJP-010"),
    ("Ibuprofen 400mg IP", "Ibuprofen Tablet IP 400mg", "PMBJP", 9.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-080"),
    ("Diclofenac Sodium 50mg IP", "Diclofenac Tablet IP 50mg", "PMBJP", 6.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-120"),
    ("Aceclofenac 100mg + Paracetamol 325mg", "Aceclofenac + Paracetamol Tab", "PMBJP", 18.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-201"),
    ("Tramadol Hydrochloride 50mg", "Tramadol Capsule 50mg", "PMBJP", 22.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-202"),
    
    # ── Gastric / Acidity (Pantoprazole, Domperidone, Omeprazole, Rabeprazole, Ranitidine)
    ("Pantoprazole 40mg IP", "Pantoprazole Tablet IP 40mg", "PMBJP", 18.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-030"),
    ("Pantoprazole 40mg + Domperidone 30mg", "Pantoprazole + Domperidone SR Cap", "PMBJP", 32.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-032"),
    ("Omeprazole 20mg IP", "Omeprazole Capsule IP 20mg", "PMBJP", 15.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-090"),
    ("Omeprazole 20mg + Domperidone 10mg", "Omeprazole + Domperidone Capsule", "PMBJP", 18.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-091"),
    ("Esomeprazole 40mg IP", "Esomeprazole Tablet IP 40mg", "PMBJP", 22.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-031"),
    ("Esomeprazole 40mg + Domperidone 30mg", "Esomeprazole + Domperidone SR Cap", "PMBJP", 38.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-033"),
    ("Rabeprazole 20mg IP", "Rabeprazole Tablet IP 20mg", "PMBJP", 20.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-110"),
    ("Rabeprazole 20mg + Domperidone 30mg", "Rabeprazole + Domperidone SR Cap", "PMBJP", 34.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-111"),
    ("Ranitidine Hydrochloride 150mg", "Ranitidine Tablet IP 150mg", "PMBJP", 6.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-112"),
    
    # ── Allergy / Cough / Cold (Cetirizine, Levocetirizine, Montelukast)
    ("Cetirizine 10mg IP", "Cetirizine Tablet IP 10mg", "PMBJP", 4.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-070"),
    ("Levocetirizine 5mg IP", "Levocetirizine Tablet IP 5mg", "PMBJP", 12.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-100"),
    ("Montelukast Sodium 10mg + Levocetirizine 5mg", "Montelukast + Levocetirizine Tab", "PMBJP", 32.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-102"),
    ("Chlorpheniramine Maleate 4mg", "Chlorpheniramine Tablet IP 4mg", "PMBJP", 2.5, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-103"),
    
    # ── Antibiotics (Amoxicillin, Azithromycin, Ofloxacin, Ciprofloxacin, Cefixime)
    ("Amoxicillin 500mg + Clavulanic Acid 125mg", "Amoxycillin + Clavulanate Tab", "PMBJP", 82.0, "Strip of 6 Tablets", "JanAushadhi", "PMBJP-015"),
    ("Azithromycin 500mg IP", "Azithromycin Tablet IP 500mg", "PMBJP", 35.0, "Strip of 3 Tablets", "JanAushadhi", "PMBJP-020"),
    ("Ciprofloxacin 500mg IP", "Ciprofloxacin Tablet IP 500mg", "PMBJP", 25.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-160"),
    ("Ofloxacin 200mg IP", "Ofloxacin Tablet IP 200mg", "PMBJP", 22.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-170"),
    ("Cefixime 200mg IP", "Cefixime Tablet IP 200mg", "PMBJP", 38.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-171"),
    ("Amoxicillin 500mg IP", "Amoxycillin Capsule IP 500mg", "PMBJP", 32.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-172"),
    ("Doxycycline 100mg IP", "Doxycycline Capsule IP 100mg", "PMBJP", 15.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-173"),
    
    # ── Hypertension / Heart (Telmisartan, Amlodipine, Metoprolol, Losartan, Ramipril, Atorvastatin)
    ("Telmisartan 40mg IP", "Telmisartan Tablet IP 40mg", "PMBJP", 14.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-060"),
    ("Telmisartan 40mg + Amlodipine 5mg", "Telmisartan + Amlodipine Tablet", "PMBJP", 20.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-062"),
    ("Amlodipine 5mg IP", "Amlodipine Tablet IP 5mg", "PMBJP", 8.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-140"),
    ("Losartan Potassium 50mg IP", "Losartan Tablet IP 50mg", "PMBJP", 18.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-130"),
    ("Metoprolol Succinate 25mg ER", "Metoprolol PR Tablet IP 25mg", "PMBJP", 12.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-142"),
    ("Atorvastatin 10mg IP", "Atorvastatin Tablet IP 10mg", "PMBJP", 12.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-040"),
    ("Atorvastatin 20mg IP", "Atorvastatin Tablet IP 20mg", "PMBJP", 19.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-041"),
    ("Rosuvastatin 10mg IP", "Rosuvastatin Tablet IP 10mg", "PMBJP", 18.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-042"),
    ("Ramipril 5mg IP", "Ramipril Tablet IP 5mg", "PMBJP", 10.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-144"),
    
    # ── Diabetes (Metformin, Glimepiride, Gliclazide, Sitagliptin)
    ("Metformin Hydrochloride 500mg IP", "Metformin Tablet IP 500mg", "PMBJP", 10.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-050"),
    ("Metformin 500mg + Glimepiride 1mg", "Glimepiride + Metformin SR Tab", "PMBJP", 16.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-052"),
    ("Metformin 500mg + Glimepiride 2mg", "Glimepiride + Metformin SR Tab", "PMBJP", 22.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-053"),
    ("Glimepiride 1mg IP", "Glimepiride Tablet IP 1mg", "PMBJP", 10.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-150"),
    ("Glimepiride 2mg IP", "Glimepiride Tablet IP 2mg", "PMBJP", 12.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-151"),
    ("Gliclazide 80mg IP", "Gliclazide Tablet IP 80mg", "PMBJP", 24.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-152"),
    ("Sitagliptin 50mg", "Sitagliptin Tablet 50mg", "PMBJP", 35.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-153"),
    
    # ── Asthma / Respiratory
    ("Salbutamol 4mg IP", "Salbutamol Tablet IP 4mg", "PMBJP", 3.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-301"),
    ("Budesonide 200mcg Inhaler", "Budesonide Inhaler 200mcg", "PMBJP", 110.0, "1 Inhaler (200 MDI)", "JanAushadhi", "PMBJP-302"),
    ("Montelukast Sodium 10mg IP", "Montelukast Tablet IP 10mg", "PMBJP", 24.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-303"),
    
    # ── Vitamins / Minerals / Immunity
    ("Calcium Carbonate 500mg + Vitamin D3 250IU", "Calcium + Vitamin D3 Tablet", "PMBJP", 15.0, "Strip of 15 Tablets", "JanAushadhi", "PMBJP-401"),
    ("Vitamin D3 60000IU", "Cholecalciferol Capsule 60k IU", "PMBJP", 25.0, "Strip of 4 Capsules", "JanAushadhi", "PMBJP-402"),
    ("Vitamin C 500mg + Zinc 5mg", "Vitamin C + Zinc Chewable Tab", "PMBJP", 12.0, "Strip of 15 Tablets", "JanAushadhi", "PMBJP-403"),
    ("B-Complex with B12 + Zinc", "B-Complex + Zinc Capsule", "PMBJP", 14.0, "Strip of 15 Capsules", "JanAushadhi", "PMBJP-404"),
    ("Iron 100mg + Folic Acid 1.5mg", "Ferrous Ascorbate + Folic Acid Tab", "PMBJP", 28.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-405"),
    
    # ── Anti-fungal / Anti-viral / Others
    ("Fluconazole 150mg IP", "Fluconazole Tablet IP 150mg", "PMBJP", 12.0, "Strip of 3 Tablets", "JanAushadhi", "PMBJP-501"),
    ("Itraconazole 100mg", "Itraconazole Capsule 100mg", "PMBJP", 45.0, "Strip of 10 Capsules", "JanAushadhi", "PMBJP-502"),
    ("Acyclovir 400mg IP", "Acyclovir Tablet IP 400mg", "PMBJP", 38.0, "Strip of 10 Tablets", "JanAushadhi", "PMBJP-503"),
    ("Thyroxine Sodium 50mcg", "Thyroxine Sodium Tablet 50mcg", "PMBJP", 30.0, "Bottle of 100 Tablets", "JanAushadhi", "PMBJP-601"),
    ("Thyroxine Sodium 100mcg", "Thyroxine Sodium Tablet 100mcg", "PMBJP", 35.0, "Bottle of 100 Tablets", "JanAushadhi", "PMBJP-602")
]

def ingest_janaushadhi():
    app = create_app()
    with app.app_context():
        print("Ingesting Jan Aushadhi generic medicines...")
        # Clear existing PMBJP data
        execute("DELETE FROM generics WHERE source = 'JanAushadhi'")
        
        count = 0
        for g in PMBJP_GENERICS:
            execute("""
                INSERT INTO generics 
                (salt_composition, generic_name, manufacturer, mrp, pack_size, source, jan_aushadhi_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, g)
            count += 1
            
        print(f"Successfully ingested {count} Jan Aushadhi medicines into the database.")

if __name__ == '__main__':
    ingest_janaushadhi()
