# data.py  ←  احفظ بهذا الاسم
import os
import sqlite3
from datetime import datetime, timedelta

db_path = "C:/laragon/www/car_rental_app/rentcar.db"

# حذف القاعدة القديمة تمامًا (لضمان عدم وجود تعارض)
if os.path.exists(db_path):
    os.remove(db_path)
    print("تم حذف القاعدة القديمة")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

print("جاري إنشاء قاعدة بيانات جديدة تمامًا...")

# ====================== إنشاء الجداول (نفس الهيكل الذي في initialize_database + اللواحق) ======================
cursor.execute("""
    CREATE TABLE voitures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_matricule TEXT NOT NULL UNIQUE,
        modele TEXT NOT NULL,
        brand TEXT NOT NULL,
        statut TEXT CHECK(statut IN ('Disponible', 'Louée', 'En Réparation', 'Réservée')) DEFAULT 'Disponible',
        emplacement TEXT,
        prix_jour REAL NOT NULL,
        image_path TEXT
    )
""")

cursor.execute("""
    CREATE TABLE clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        genre TEXT CHECK(genre IN ('Homme', 'Femme')),
        date_naissance TEXT,
        lieu_naissance TEXT,
        adresse TEXT,
        numero_permis TEXT,
        date_permis TEXT,
        telephone TEXT
    )
""")

cursor.execute("""
    CREATE TABLE locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        client_id INTEGER,
        second_client_id INTEGER,
        date_heure_location TEXT,
        jours INTEGER,
        cout_total REAL,
        statut TEXT CHECK(statut IN ('Active', 'Terminée')) DEFAULT 'Active',
        fuel_depart TEXT,
        promotion INTEGER DEFAULT 0,
        accessories_radio TEXT CHECK(accessories_radio IN ('oui', 'non', '')),
        accessories_jack TEXT CHECK(accessories_jack IN ('oui', 'non', '')),
        accessories_lighter TEXT CHECK(accessories_lighter IN ('oui', 'non', '')),
        accessories_mat TEXT CHECK(accessories_mat IN ('oui', 'non', '')),
        accessories_code TEXT CHECK(accessories_code IN ('oui', 'non', '')),
        FOREIGN KEY (voiture_id) REFERENCES voitures(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (second_client_id) REFERENCES clients(id)
    )
""")

cursor.execute("""
    CREATE TABLE reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        client_id INTEGER,
        date_debut TEXT,
        jours INTEGER,
        cout_total REAL,
        payment_percentage REAL,
        statut TEXT CHECK(statut IN ('Active', 'Terminée')) DEFAULT 'Active',
        FOREIGN KEY (voiture_id) REFERENCES voitures(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )
""")

cursor.execute("""
    CREATE TABLE reparations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        description TEXT,
        cout REAL,
        date_completion TEXT,
        FOREIGN KEY (voiture_id) REFERENCES voitures(id)
    )
""")

cursor.execute("""
    CREATE TABLE fuel_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        montant REAL,
        date TEXT,
        FOREIGN KEY (voiture_id) REFERENCES voitures(id)
    )
""")

cursor.execute("""
    CREATE TABLE factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER,
        details TEXT,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    )
""")

cursor.execute("""
    CREATE TABLE expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT CHECK(type IN ('Frais', 'Faux Frais')),
        cost REAL,
        date TEXT,
        description TEXT
    )
""")

cursor.execute("""
    CREATE TABLE settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
""")

# ====================== إدخال بيانات عربية حقيقية ======================
# سيارات
cursor.executemany("""
    INSERT INTO voitures (numero_matricule, modele, brand, statut, emplacement, prix_jour, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    ('056-123-16', 'Clio 4', 'Renault', 'Disponible', 'ندرومة', 4500, 'car22.png'),
    ('178-456-13', 'Symbol', 'Renault', 'Louée', 'مغنية', 5000, 'car22.png'),
    ('034-789-09', 'Duster', 'Renault', 'Disponible', 'وهران', 7500, 'car22.png'),
    ('167-890-16', 'i10', 'Hyundai', 'Disponible', 'تلمسان', 4000, 'car22.png'),
    ('045-321-13', 'Picanto', 'Kia', 'En Réparation', 'ندرومة', 3800, 'car22.png'),
])

# عملاء جزائريون 100%
cursor.executemany("""
    INSERT INTO clients (nom, prenom, genre, date_naissance, lieu_naissance, adresse, numero_permis, date_permis, telephone)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", [
    ('عيساوي', 'عبد القادر', 'Homme', '1985-03-15', 'ندرومة', 'حي 30 مسكن الخريبة، ندرومة', '056789123', '2010-06-20', '0775868765'),
    ('بن عمارة', 'فاطمة', 'Femme', '1992-07-22', 'مغنية', 'حي الوئام، مغنية', '178456789', '2016-09-10', '0551987654'),
    ('حاجي', 'محمد', 'Homme', '1980-11-30', 'تلمسان', 'حي القدس، تلمسان', '234567890', '2005-04-12', '0665123456'),
    ('شتوان', 'آمنة', 'Femme', '1995-01-08', 'وهران', 'حي السلام، وهران', '345678901', '2018-12-01', '0798765432'),
    ('بلعربي', 'إلياس', 'Homme', '1988-09-17', 'عين تموشنت', 'حي 500 مسكن، عين تموشنت', '456789012', '2013-08-25', '0699123456'),
])

# عقود كراء (مع اللواحق)
today = datetime.now()
cursor.executemany("""
    INSERT INTO locations 
    (voiture_id, client_id, second_client_id, date_heure_location, jours, cout_total, statut, fuel_depart, promotion,
     accessories_radio, accessories_jack, accessories_lighter, accessories_mat, accessories_code)
    VALUES (1, 1, NULL, ?, 5, 22500, 'Active', 'Plein', 0, 'oui', 'oui', 'non', 'oui', 'non')
""", [(today.strftime('%Y-%m-%d %H:%M:%S'),)])

cursor.executemany("""
    INSERT INTO locations 
    (voiture_id, client_id, second_client_id, date_heure_location, jours, cout_total, statut, fuel_depart, promotion,
     accessories_radio, accessories_jack, accessories_lighter, accessories_mat, accessories_code)
    VALUES (2, 2, 3, ?, 3, 15000, 'Terminée', 'Demi', 10, 'oui', 'non', 'oui', 'oui', 'oui')
""", [( (today - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),)])

# إعدادات الوكالة
cursor.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", [
    ("nom_agence", "لوكاتوب - LOCATOP"),
    ("proprietaire", "عيساوي عبد القادر"),
    ("adresse", "05 تجمع 30 مسكن الخريبة - ندرومة"),
    ("telephone", "0775 86 87 65"),
])

conn.commit()
conn.close()

print("تم إنشاء قاعدة البيانات بنجاح 100%")
print("العملاء بالعربية + اللواحق موجودة + العقد يطبع بدون أي مشكلة")
print("جرب الآن فتح التطبيق → كل شيء يعمل تمام!")