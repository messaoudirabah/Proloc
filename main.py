import datetime
import functools
# ==================== PATCH REPORTLAB (OBLIGATOIRE) ====================
import hashlib
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta

_original_md5 = hashlib.md5
def _patched_md5(*args, **kwargs):
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = _patched_md5
# ====================================================================

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import (QDate, QDir, QSize, QStringListModel, Qt, QTime,
                          QTimer, QUrl)
from PyQt5.QtGui import (QColor, QFont, QGuiApplication, QIcon, QMovie,
                         QPainter, QPixmap, QTextCharFormat, QTextDocument)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QTabWidget  # ← AJOUTE ÇA ICI
from PyQt5.QtWidgets import QTimeEdit  # ← AJOUTEZ CETTE LIGNE
from PyQt5.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QAction,
                             QApplication, QButtonGroup, QCalendarWidget,
                             QCheckBox, QComboBox, QCompleter, QDateEdit,
                             QDialog, QFileDialog, QFormLayout, QFrame,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                             QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QMenu, QMessageBox, QProgressBar, QPushButton,
                             QRadioButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QSpinBox, QStackedWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QToolTip, QVBoxLayout, QWidget)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
# ========== AJOUT EN HAUT DU FICHIER (après les imports ReportLab) ==========
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle


# ========== FONCTION POUR ENREGISTRER UNE POLICE ARABE ==========
def register_arabic_font():
    """Enregistre une police qui supporte l'arabe"""
    try:
        # Essayer d'utiliser une police système Windows qui supporte l'arabe
        font_path = "C:\\Windows\\Fonts\\arial.ttf"  # Arial supporte l'arabe
        
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arabic', font_path))
            return True
        else:
            # Si Arial n'existe pas, essayer Tahoma
            font_path = "C:\\Windows\\Fonts\\tahoma.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Arabic', font_path))
                return True
    except Exception as e:
        print(f"Erreur lors du chargement de la police arabe : {e}")
        return False
    
    return False

# ========== FONCTION POUR INVERSER LE TEXTE ARABE ==========
def prepare_arabic_text(text):
    """Prépare le texte arabe pour l'affichage dans ReportLab"""
    try:
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display

        # Reshape Arabic text (connecte les lettres)
        reshaped_text = reshape(text)
        # Inverse pour l'affichage RTL
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except ImportError:
        # Si les modules ne sont pas installés, retourner le texte tel quel
        # (recommandé : pip install arabic-reshaper python-bidi)
        return text


def get_app_path():
    """تعمل سواء كان البرنامج .py أو .exe (PyInstaller)"""
    if getattr(sys, 'frozen', False):  # إذا كان مجمد (exe)
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_db_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "rentcar.db")
    else:
        return os.path.join(os.path.abspath("."), "rentcar.db")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def initialize_database(conn, cursor):
    # === TABLE VOITURES ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS voitures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_matricule TEXT NOT NULL UNIQUE,
        modele TEXT NOT NULL,
        brand TEXT NOT NULL,
        statut TEXT CHECK(statut IN ('Disponible', 'Louée', 'En Réparation', 'Réservée')) DEFAULT 'Disponible',
        emplacement TEXT,
        prix_jour REAL NOT NULL,
        image_path TEXT
    )
    ''')

    # === TABLE CLIENTS (avec date_expiration_permis et notes) ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        genre TEXT CHECK(genre IN ('Homme', 'Femme')),
        date_naissance TEXT,
        lieu_naissance TEXT,
        adresse TEXT,
        numero_permis TEXT,
        date_permis TEXT,
        date_expiration_permis TEXT,
        telephone TEXT,
        permis_recto_path TEXT,
        permis_verso_path TEXT,
        notes TEXT                     -- ← NOUVELLE COLONNE
    )
    ''')

    # Ajouter les colonnes si elles n'existent pas (pour les anciennes bases)
    cursor.execute("PRAGMA table_info(clients)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'date_expiration_permis' not in columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN date_expiration_permis TEXT")
    if 'notes' not in columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN notes TEXT")

    # === TABLE LOCATIONS ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        client_id INTEGER,
        second_client_id INTEGER,
        date_heure_location TEXT,
        jours INTEGER,
        cout_total REAL,
        statut TEXT CHECK(statut IN ('Active', 'Terminée')) DEFAULT 'Active',
        fuel_depart TEXT,
        promotion INTEGER,
        accessories_radio TEXT,
        accessories_jack TEXT,
        accessories_lighter TEXT,
        accessories_mat TEXT,
        accessories_code TEXT,
        FOREIGN KEY (voiture_id) REFERENCES voitures(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (second_client_id) REFERENCES clients(id)
    )
    ''')

    # === TABLE RÉSERVATIONS ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
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
    ''')

    # === AUTRES TABLES (inchangées) ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reparations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        description TEXT,
        cout REAL,
        date_completion TEXT,
        FOREIGN KEY (voiture_id) REFERENCES voitures(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fuel_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voiture_id INTEGER,
        montant REAL,
        date TEXT,
        type TEXT,
        FOREIGN KEY (voiture_id) REFERENCES voitures(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER,
        details TEXT,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT CHECK(type IN ('Frais', 'Faux Frais')),
        cost REAL,
        date TEXT,
        description TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signed_factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_location_id INTEGER,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        import_date TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_signed_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )
    ''')
        # Add ALTER for existing DBs (after the existing ALTERs for clients)
    cursor.execute("PRAGMA table_info(locations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'insurance_company' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN insurance_company TEXT")
    if 'insurance_policy' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN insurance_policy TEXT")
    if 'payment_method' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN payment_method TEXT CHECK(payment_method IN ('Cash', 'Check')) DEFAULT 'Cash'")
    if 'check_number' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN check_number TEXT")
    if 'check_date' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN check_date TEXT")
    if 'deposit_amount' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN deposit_amount REAL")
    if 'deposit_method' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN deposit_method TEXT CHECK(deposit_method IN ('Cash', 'Check')) DEFAULT 'Cash'")
    if 'bank' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN bank TEXT")
    cursor.execute("PRAGMA table_info(locations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'km_depart' not in columns:
        cursor.execute("ALTER TABLE locations ADD COLUMN km_depart INTEGER DEFAULT 0")
    # === PARAMÈTRES PAR DÉFAUT ===
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("nom_agence", "LOCATOP"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("proprietaire", "Aissaoui Abdelkader"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("telephone", "0775868765"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("adresse", "05 تجمع 30 الخريبة ندرومة"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('login_username', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('login_password', 'admin')")

    conn.commit()

# ========== CLASSE POUR LE SÉLECTEUR D'HEURE VISUEL ==========
class TimePickerDialog(QDialog):
    """Popup d'horloge visuelle pour sélectionner l'heure"""
    def __init__(self, current_time=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Sélectionner l'heure")
        
        # Use parent's scale function if available
        width = 300
        height = 350
        if self.parent_window and hasattr(self.parent_window, 'scale'):
            width = self.parent_window.scale(300)
            height = self.parent_window.scale(350)
            
        self.setFixedSize(width, height)
        self.setModal(True)
        
        # Heure sélectionnée
        self.selected_time = current_time or QTime.currentTime()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Titre
        title = QLabel("Choisir l'heure")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e40af;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Affichage de l'heure sélectionnée
        self.time_display = QLabel(self.selected_time.toString("HH:mm"))
        self.time_display.setStyleSheet("""
            font-size: 32px; 
            font-weight: bold; 
            color: #059669;
            background: #f0fdf4;
            padding: 15px;
            border-radius: 10px;
        """)
        self.time_display.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_display)
        
        # Sélecteurs avec spinbox
        time_layout = QHBoxLayout()
        time_layout.setSpacing(10)
        
        # Heures
        hour_layout = QVBoxLayout()
        hour_label = QLabel("Heures")
        hour_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        hour_label.setAlignment(Qt.AlignCenter)
        
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(self.selected_time.hour())
        self.hour_spin.setStyleSheet("""
            QSpinBox {
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                border: 2px solid #3b82f6;
                border-radius: 8px;
            }
        """)
        self.hour_spin.valueChanged.connect(self.update_time_display)
        
        hour_layout.addWidget(hour_label)
        hour_layout.addWidget(self.hour_spin)
        time_layout.addLayout(hour_layout)
        
        # Séparateur
        sep = QLabel(":")
        sep.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e40af;")
        sep.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(sep)
        
        # Minutes
        minute_layout = QVBoxLayout()
        minute_label = QLabel("Minutes")
        minute_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        minute_label.setAlignment(Qt.AlignCenter)
        
        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setValue(self.selected_time.minute())
        self.minute_spin.setStyleSheet(self.hour_spin.styleSheet())
        self.minute_spin.valueChanged.connect(self.update_time_display)
        
        minute_layout.addWidget(minute_label)
        minute_layout.addWidget(self.minute_spin)
        time_layout.addLayout(minute_layout)
        
        layout.addLayout(time_layout)
        
        # Boutons rapides (heures communes)
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(5)
        
        for h in [8, 9, 14, 17]:
            btn = QPushButton(f"{h}:00")
            btn.setStyleSheet("""
                background: #e0e7ff;
                color: #1e40af;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            """)
            btn.clicked.connect(lambda _, hour=h: self.set_quick_time(hour, 0))
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        
        # Boutons OK/Annuler
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        ok_btn = QPushButton("Valider")
        ok_btn.setStyleSheet("""
            background: #059669;
            color: white;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        """)
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("""
            background: #dc2626;
            color: white;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
    
    def update_time_display(self):
        """Met à jour l'affichage de l'heure"""
        hour = self.hour_spin.value()
        minute = self.minute_spin.value()
        self.selected_time = QTime(hour, minute)
        self.time_display.setText(self.selected_time.toString("HH:mm"))
    
    def set_quick_time(self, hour, minute):
        """Définit rapidement une heure"""
        self.hour_spin.setValue(hour)
        self.minute_spin.setValue(minute)
    
    def get_time(self):
        """Retourne l'heure sélectionnée"""
        return self.selected_time
# ========== CLASSE POUR LE SÉLECTEUR DE DATE VISUEL ==========
class DatePickerDialog(QDialog):
    """Popup de calendrier visuel pour sélectionner une date"""
    def __init__(self, current_date=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Sélectionner la date")
        
        # Use parent's scale function if available
        width = 400
        height = 450
        if self.parent_window and hasattr(self.parent_window, 'scale'):
            width = self.parent_window.scale(400)
            height = self.parent_window.scale(450)
            
        self.setFixedSize(width, height)
        self.setModal(True)
        
        # Date sélectionnée
        self.selected_date = current_date or QDate.currentDate()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Titre
        title = QLabel("Choisir la date")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e40af;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Affichage de la date sélectionnée
        self.date_display = QLabel(self.selected_date.toString("dd/MM/yyyy"))
        self.date_display.setStyleSheet("""
            font-size: 32px; 
            font-weight: bold; 
            color: #059669;
            background: #f0fdf4;
            padding: 15px;
            border-radius: 10px;
        """)
        self.date_display.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.date_display)
        
        # Calendrier
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(self.selected_date)
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background: white;
                border: 2px solid #3b82f6;
                border-radius: 10px;
            }
            QCalendarWidget QToolButton {
                color: #1e293b;
                font-weight: bold;
                padding: 8px;
                background: #e0e7ff;
                border-radius: 6px;
            }
            QCalendarWidget QToolButton:hover {
                background: #3b82f6;
                color: white;
            }
            QCalendarWidget QAbstractItemView {
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #f8fafc;
            }
        """)
        self.calendar.clicked.connect(self.update_date_display)
        layout.addWidget(self.calendar)
        
        # Boutons rapides (aujourd'hui, demain, dans 7 jours)
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(5)
        
        for label, days in [("Aujourd'hui", 0), ("Demain", 1), ("Dans 7j", 7)]:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                background: #e0e7ff;
                color: #1e40af;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            """)
            btn.clicked.connect(lambda _, d=days: self.set_quick_date(d))
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        
        # Boutons OK/Annuler
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        ok_btn = QPushButton("Valider")
        ok_btn.setStyleSheet("""
            background: #059669;
            color: white;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        """)
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("""
            background: #dc2626;
            color: white;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
    
    def update_date_display(self, date):
        """Met à jour l'affichage de la date"""
        self.selected_date = date
        self.date_display.setText(date.toString("dd/MM/yyyy"))
    
    def set_quick_date(self, days_offset):
        """Définit rapidement une date"""
        new_date = QDate.currentDate().addDays(days_offset)
        self.calendar.setSelectedDate(new_date)
        self.update_date_display(new_date)
    
    def get_date(self):
        """Retourne la date sélectionnée"""
        return self.selected_date


class RentCarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de Location de Voitures")
        self.resize(1024, 768)
        # ========== GLOBAL STYLESHEET FOR ALL COMBOBOXES ==========
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 20px;
                font-size: 18px;
                background: #ffffff;
                color: #000000;
            }
            QComboBox:focus {
                border: 2px solid #3b82f6;
            }
            
            /* Fix dropdown list styling */
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                border: 1px solid #d1d5db;
                padding: 4px;
            }
            
            QComboBox QAbstractItemView::item {
                padding: 8px;
                color: #000000;
            }
            
            QComboBox QAbstractItemView::item:hover {
                background-color: #dbeafe;
                color: #1e40af;
            }
            
            QComboBox QAbstractItemView::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
        """)
# ====== SCALE SYSTEM ======
        self.base_width = 1920
        self.base_height = 1080
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        self.scale_factor = min(screen_geo.width() / self.base_width, screen_geo.height() / self.base_height)
        
        # Ensure scale factor doesn't shrink too much
        self.scale_factor = max(0.5, self.scale_factor)

        self.resize(int(1400 * self.scale_factor), int(900 * self.scale_factor))
        # Use scaled minimum size based on a smaller reference (800x600) to ensure it fits 1024x768 screens
        self.setMinimumSize(self.scale(800), self.scale(600)) 

        def scale(value):
            return int(value * self.scale_factor)
        self.scale = scale

        def scale_font(value):
            return max(8, int(value * self.scale_factor))
        self.scale_font = scale_font
        # Initialiser la base de données SQLite
        db_path = get_db_path()
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        initialize_database(self.conn, self.cursor)
        
        # Add missing columns for driver's license scans if they don't exist
        try:
            self.cursor.execute("ALTER TABLE clients ADD COLUMN permis_recto_path TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            self.cursor.execute("ALTER TABLE clients ADD COLUMN permis_verso_path TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        self.update_car_statuses()
        # Initialiser les traductions (seulement français)
        self.translations = {
            "fr": {
                "app_title": "Gestion de Location de Voitures",
                "sidebar_title": "RentCarApp",
                "dashboard": "Tableau de Bord",
                "voitures": "Voitures",
                "clients": "Clients",
                "location": "Location de Voiture",
                "factures": "Factures",
                "reservations": "Réservations",
                "frais": "Frais",
                "parametres": "Paramètres",
                "nb_voitures": "Nombre de Voitures",
                "nb_clients": "Nombre de Clients",
                "nb_locations_recents": "Locations Récentes",
                "nb_reservations": "Réservations Actives",
                "revenus_totaux": "Revenus Totaux: {} DA",
                "duree_moyenne": "Durée Moyenne: {} jours",
                "a_propos": "À Propos de LOCATOP",
                "nom_agence": "Nom de l'Agence:",
                "proprietaire": "Propriétaire:",
                "telephone": "Téléphone:",
                "adresse": "Adresse:",
                "calendrier": "Calendrier des Retours",
                "calendrier_reservations": "Calendrier des Réservations",
                "aucune_voiture_retour": "Aucune voiture à retourner à cette date.",
                "aucune_reservation": "Aucune réservation à cette date.",
                "id_location": "ID Location",
                "id_reservation": "ID Réservation",
                "matricule": "Matricule",
                "modele": "Modèle",
                "client": "Client",
                "cout_total": "Coût Total (DA)",
                "payment_percentage": "Pourcentage Payé (%)",
                "fermer": "Fermer",
                "liste_voitures": "Liste des Voitures",
                "voitures_louees": "Voitures Louées",
                "voitures_disponibles": "Voitures Disponibles",
                "voitures_reparation": "Voitures en Réparation",
                "categorie": "Catégorie:",
                "type": "Type:",
                "statut": "Statut:",
                "emplacement": "Emplacement:",
                "prix_jour": "Prix/Jour (DA):",
                "ajouter": "Ajouter",
                "nouvelle_voiture": "Nouvelle Voiture",
                "nouvelle_reparation": "Nouvelle Réparation",
                "nouveau_carburant": "Nouveau Carburant",
                "nouvelle_reservation": "Nouvelle Réservation",
                "nouvelle_frais": "Nouveau Frais",
                "type_reparation": "Type de Réparation:",
                "montant_carburant": "Montant Carburant (DA):",
                "cout": "Coût (DA):",
                "date": "Date:",
                "date_fin": "Date de Fin:",
                "ajouter_reparation": "Ajouter Réparation",
                "ajouter_carburant": "Ajouter Carburant",
                "ajouter_reservation": "Ajouter Réservation",
                "ajouter_frais": "Ajouter Frais",
                "brand": "Marque",  # Added translation for brand
                "image": "Image",  # Added translation for brand
                "photo": "Photo",
                "type_carburant": "Type Carburant",  # Added for fuel type

                "details": "Détails",
                "editer": "Éditer",
                "supprimer": "Supprimer",
                "actions": "Actions",
                "revenus_nets": "Revenus Nets: {} DA",
                "historique_reparations": "Historique des Réparations",
                "historique_carburant": "Historique des Carburants",
                "liste_clients": "Liste des Clients",
                "clients_hommes": "Clients Hommes",
                "clients_femmes": "Clients Femmes",
                "nom": "Nom:",
                "prenom": "Prénom:",
                "genre": "Genre:",
                "date_naissance": "Date Naissance:",
                "lieu_naissance": "Lieu Naissance:",
                "adresse_client": "Adresse:",
                "numero_permis": "N° Permis:",
                "date_permis": "Date Permis:",
                "telephone_client": "Téléphone:",
                "nouveau_client": "Nouveau Client",
                "historique_locations": "Historique des Locations",
                "date_location": "Date Location",
                "jours": "Jours",
                "nouvelle_location": "Nouvelle Location",
                "liste_factures": "Liste des Factures",
                "voir": "Voir",
                "imprimer": "Imprimer",
                "settings_a_propos": "Modifier À Propos",
                "export_data": "Exporter Données",
                "export_clients": "Exporter Clients (PDF)",
                "export_voitures": "Exporter Voitures (PDF)",
                "export_factures": "Exporter Factures (PDF)",
                "export_reservations": "Exporter Réservations (PDF)",
                "error_prix_jour": "Le prix par jour doit être un nombre.",
                "error_voiture_id_cout": "ID voiture et coût doivent être des nombres.",
                "error_voiture_id_invalide": "ID voiture invalide.",
                "error_jours_positif": "Le nombre de jours doit être un entier positif.",
                "confirm_supprimer_voiture": "Voulez-vous supprimer cette voiture ?",
                "confirm_supprimer_client": "Voulez-vous supprimer ce client ?",
                "confirm_supprimer_reservation": "Voulez-vous supprimer cette réservation ?",
                "error_schema_clients": "Schéma de la table clients incorrect. Supprimez rentcar.db et redémarrez.",
                "fuel_depart": "Carburant Départ",
                "promotion": "Promotion",
                "client_2_optionnel": "Client 2 (Optionnel)",
                "supprimer_selectionnes": "Supprimer Sélectionnés",
                "confirm_supprimer_selection": "Voulez-vous supprimer les éléments sélectionnés ?",
                "backup_database": "Sauvegarder la Base de Données",
                "save_settings": "Enregistrer Paramètres",
                "search_placeholder": "Rechercher par nom...",
                "liste_frais": "Liste des Frais",
                "total_frais": "Total Frais",
                "total_faux_frais": "Total Faux Frais",
                "type_frais": "Type:",
                "description": "Description:",
                "error_fields_required": "Champs requis manquants."
            }
        }
        self.current_language = "fr"
        # Widget principal et layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # ================== SIDEBAR ULTRA-RESPONSIVE & MODERN 2025 ==================
        self.sidebar = QWidget()
        self.sidebar.setObjectName("modernSidebar")
        
        # Dynamic width based on screen size
        sidebar_width = max(200, min(280, int(self.width() * 0.18)))
        self.sidebar.setFixedWidth(sidebar_width)
        
        self.sidebar.setStyleSheet(f"""
            QWidget#modernSidebar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1e3a8a, stop:1 #1e40af);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ========== HEADER WITH ANIMATED LOGO ==========
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(self.scale(20), self.scale(30), self.scale(20), self.scale(25))
        header_layout.setSpacing(self.scale(8))

        # Logo container with image
        logo_container = QWidget()
        logo_container.setFixedSize(self.scale(60), self.scale(60))
        logo_container.setStyleSheet("background: transparent;")
        
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_label = QLabel()
        logo_path = resource_path("logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(
            self.scale(60), 
            self.scale(60), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback to text if image not found
            logo_label.setText("P")
            logo_label.setStyleSheet(f"""
            color: white; 
            font-size: {self.scale_font(32)}px; 
            font-weight: 900;
            """)
        
        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo_label)

        self.app_name = QLabel("ProLoc")
        self.app_name.setStyleSheet(f"""
            color: white; 
            font-size: {self.scale_font(22)}px; 
            font-weight: 800; 
            letter-spacing: 1px;
            background: transparent;
        """)
        self.app_name.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Gestion de Location")
        subtitle.setStyleSheet(f"""
            color: rgba(226, 232, 240, 0.7); 
            font-size: {self.scale_font(11)}px; 
            font-weight: 500;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(logo_container, alignment=Qt.AlignCenter)
        header_layout.addWidget(self.app_name)
        header_layout.addWidget(subtitle)
        sidebar_layout.addWidget(header_widget)

        # ========== MENU WITH SMOOTH ANIMATIONS ==========
        menu_scroll = QScrollArea()
        menu_scroll.setWidgetResizable(True)
        menu_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        menu_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        menu_scroll.setStyleSheet("""
            QScrollArea {
            background: transparent;
            border: none;
            }
            QScrollBar:vertical {
            background: rgba(255, 255, 255, 0.05);
            width: 6px;
            border-radius: 3px;
            }
            QScrollBar::handle:vertical {
            background: rgba(59, 130, 246, 0.5);
            border-radius: 3px;
            }
        """)

        menu_widget = QWidget()
        menu_widget.setStyleSheet("background: transparent;")
        menu_layout = QVBoxLayout(menu_widget)
        menu_layout.setContentsMargins(self.scale(12), self.scale(10), self.scale(12), self.scale(10))
        menu_layout.setSpacing(self.scale(6))

        self.sidebar_buttons = {}
        
        # Modern icons using Unicode symbols
        menu_items = [
            ("dashboard", "📊  Tableau de Bord", self.show_dashboard),
            ("voitures", "🚗  Véhicules", self.show_voitures),
            ("clients", "👥  Clients", self.show_clients),
            ("location", "🔑  Locations", self.show_location),
            ("reservations", "📅  Réservations", self.show_reservations),
            ("frais", "💰  Frais", self.show_frais),
            ("factures", "🧾  Factures", self.show_factures),
            ("stats", "📈  Statistiques", self.show_stats),
            ("parametres", "⚙️  Paramètres", self.show_parametres),
        ]

        for key, text, func in menu_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(self.scale(48))
            btn.setCursor(Qt.PointingHandCursor)
            
            btn.setStyleSheet(f"""
            QPushButton {{
                color: rgba(226, 232, 240, 0.8);
                background: transparent;
                text-align: left;
                padding-left: {self.scale(20)}px;
                font-size: {self.scale_font(14)}px;
                font-weight: 500;
                border: none;
                border-radius: {self.scale(10)}px;
                margin: 0 {self.scale(4)}px;
            }}
            QPushButton:hover {{
                background: rgba(59, 130, 246, 0.15);
                color: white;
                padding-left: {self.scale(24)}px;
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(59, 130, 246, 0.3), 
                stop:1 rgba(37, 99, 235, 0.2));
                color: white;
                font-weight: 700;
                border-left: {self.scale(4)}px solid #3b82f6;
                padding-left: {self.scale(20)}px;
            }}
            """)
            
            # Add hover effect
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(self.scale(15))
            effect.setColor(QColor(59, 130, 246, 50))
            effect.setOffset(0, 0)
            btn.setGraphicsEffect(effect)
            
            btn.clicked.connect(func)
            menu_layout.addWidget(btn)
            self.sidebar_buttons[key] = btn

        menu_layout.addStretch()
        menu_scroll.setWidget(menu_widget)
        sidebar_layout.addWidget(menu_scroll, 1)

        # ========== MODERN FOOTER ==========
        footer_widget = QWidget()
        footer_widget.setStyleSheet("""
            background: rgba(0, 0, 0, 0.2);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        """)
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(self.scale(15), self.scale(15), self.scale(15), self.scale(15))
        footer_layout.setSpacing(self.scale(5))

        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet(f"""
            color: rgba(226, 232, 240, 0.5);
            font-size: {self.scale_font(10)}px;
            font-weight: 500;
            background: transparent;
        """)
        version_label.setAlignment(Qt.AlignCenter)

        copyright_label = QLabel("© 2025 MSD")
        copyright_label.setStyleSheet(f"""
            color: rgba(226, 232, 240, 0.4);
            font-size: {self.scale_font(9)}px;
            background: transparent;
        """)
        copyright_label.setAlignment(Qt.AlignCenter)

        footer_layout.addWidget(version_label)
        footer_layout.addWidget(copyright_label)
        sidebar_layout.addWidget(footer_widget)

        main_layout.addWidget(self.sidebar, 0)
        # Zone de contenu avec stacked widget
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)
        # Charger les informations À Propos depuis la base de données
        self.load_settings()
        self.signed_dir = os.path.join(get_app_path(), "signed_factures")
        os.makedirs(self.signed_dir, exist_ok=True)
        self.facture_mode = "normal"  # par défaut
        self.setup_dashboard_page()
        self.setup_voitures_page()
        self.setup_clients_page()
        self.setup_location_page()
        self.setup_reservations_page()
        self.setup_frais_page()
        self.setup_factures_page()
        self.setup_parametres_page()
        self.setup_stats_page()
        # Charger les données initiales
        self.load_voitures()
        self.load_clients()
        self.load_locations()
        self.load_reservations()
        self.load_frais()
        self.load_factures()
        # Afficher le tableau de bord par défaut
        self.show_dashboard()
        
        # Run background migration
        self.migrate_existing_files()

    def scale(self, value):
            w = self.width()
            h = self.height()
            factor = min(w / self.base_width, h / self.base_height)
            return int(value * factor)

    def scale_font(self, value):
            return max(8, int(value * (self.width() / self.base_width)))

    def save_upload(self, source_path, category):
        """Copies a file to the internal uploads folder and returns the new path."""
        if not source_path:
            return ""
        
        # Check if already in uploads (to avoid double copying)
        if "data/uploads" in source_path.replace("\\", "/"):
            return source_path

        if not os.path.exists(source_path):
            return ""

        try:
            # Create base uploads dir
            base_dir = get_app_path()
            upload_dir = os.path.join(base_dir, "data", "uploads", category)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            ext = os.path.splitext(source_path)[1]
            new_filename = f"{uuid.uuid4().hex}{ext}"
            target_path = os.path.join(upload_dir, new_filename)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Return absolute path
            return os.path.normpath(target_path).replace("\\", "/")
        except Exception as e:
            print(f"Error saving file: {e}")
            return "" # Safe fallback

    def migrate_existing_files(self):
        """Scans database for external files and moves them to internal storage."""
        print("🚀 Starting file migration to internal storage...")
        
        # 1. Migrate Car Images
        self.cursor.execute("SELECT id, image_path FROM voitures WHERE image_path IS NOT NULL AND image_path != ''")
        voitures = self.cursor.fetchall()
        for vid, path in voitures:
            if path and os.path.exists(path) and "data/uploads" not in path.replace("\\", "/"):
                new_path = self.save_upload(path, "cars")
                if new_path:
                    self.cursor.execute("UPDATE voitures SET image_path = ? WHERE id = ?", (new_path, vid))
        
        # 2. Migrate Client Licenses
        self.cursor.execute("SELECT id, permis_recto_path, permis_verso_path FROM clients")
        clients = self.cursor.fetchall()
        for cid, recto, verso in clients:
            if recto and os.path.exists(recto) and "data/uploads" not in recto.replace("\\", "/"):
                new_recto = self.save_upload(recto, "licenses")
                self.cursor.execute("UPDATE clients SET permis_recto_path = ? WHERE id = ?", (new_recto, cid))
            if verso and os.path.exists(verso) and "data/uploads" not in verso.replace("\\", "/"):
                new_verso = self.save_upload(verso, "licenses")
                self.cursor.execute("UPDATE clients SET permis_verso_path = ? WHERE id = ?", (new_verso, cid))
                
        # 3. Migrate Signed Contracts
        try:
            self.cursor.execute("SELECT id, file_path FROM client_signed_contracts")
            contracts = self.cursor.fetchall()
            for con_id, path in contracts:
                if path and os.path.exists(path) and "data/uploads" not in path.replace("\\", "/"):
                    new_path = self.save_upload(path, "contracts")
                    if new_path:
                        self.cursor.execute("UPDATE client_signed_contracts SET file_path = ? WHERE id = ?", (new_path, con_id))
        except:
            pass # Table might not exist yet in some edge cases
            
        self.conn.commit()
        print("✅ Migration completed.")
    
    def resizeEvent(self, event):
        try:
            # Example: scale sidebar
            if hasattr(self, "sidebar"):
                self.sidebar.setFixedWidth(self.scale(260))

            # Example: scale table column width
            if hasattr(self, "voiture_table"):
                self.voiture_table.setColumnWidth(6, self.scale(300))

            # Example: scale fonts
            if hasattr(self, "app_name"):
                f = self.app_name.font()
                f.setPointSize(self.scale_font(18))
                self.app_name.setFont(f)

        except:
            pass

        return super().resizeEvent(event)

    def load_settings(self):
        self.settings = {}
        self.cursor.execute("SELECT key, value FROM settings")
        for key, value in self.cursor.fetchall():
            self.settings[key] = value

    def update_car_statuses(self):
        today = date.today().isoformat()

        try:
            # 1. Terminer les locations expirées (inclusif avec <=)
            self.cursor.execute("""
                UPDATE locations SET statut = 'Terminée' 
                WHERE statut = 'Active' 
                AND date(date_heure_location, '+' || jours || ' days') <= ?
            """, (today,))

            # 2. Terminer les réservations expirées (inclusif avec <=)
            self.cursor.execute("""
                UPDATE reservations SET statut = 'Terminée' 
                WHERE statut = 'Active' 
                AND date(date_debut, '+' || jours || ' days') <= ?
            """, (today,))

            # 3. Libérer les voitures sans locations/réservations actives
            self.cursor.execute("""
                UPDATE voitures SET statut = 'Disponible' 
                WHERE statut IN ('Louée', 'Réservée')
                AND id NOT IN (
                    SELECT voiture_id FROM locations WHERE statut = 'Active'
                    UNION
                    SELECT voiture_id FROM reservations WHERE statut = 'Active'
                )
            """)
            
            self.conn.commit()
            print(f"Statuts mis à jour avec succès le {today}")

        except Exception as e:
            print(f"Erreur dans update_car_statuses: {e}")
            self.conn.rollback()

    def setup_dashboard_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(30))
        layout.setSpacing(self.scale(20))

        # ================== TITLE ==================
        title = QLabel(f"Tableau de bord — {self.settings.get('nom_agence', 'LOCATOP')}")
        title.setStyleSheet(f"font-size:{self.scale_font(24)}px; font-weight:800; color:#111827;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== STATS CARDS (2 columns on small screen) ==================
        stats_widget = QWidget()
        stats_grid = QGridLayout(stats_widget)
        stats_grid.setSpacing(16)

        self.nb_voitures_label = QLabel("0")
        self.nb_clients_label = QLabel("0")
        self.nb_locations_recents_label = QLabel("0")
        self.nb_reservations_label = QLabel("0")
        self.total_revenue_label = QLabel("0.00 DA")
        self.avg_duration_label = QLabel("0 jours")

        cards = [
            ("Véhicules", self.nb_voitures_label, "#1d4ed8"),
            ("Clients", self.nb_clients_label, "#7c3aed"),
            ("Locations (30j)", self.nb_locations_recents_label, "#059669"),
            ("Réservations", self.nb_reservations_label, "#d97706"),
            ("Revenus nets", self.total_revenue_label, "#dc2626"),
            ("Durée moy.", self.avg_duration_label, "#0891b2"),
        ]

        for i, (text, label, color) in enumerate(cards):
            card = QWidget()
            card.setFixedHeight(self.scale(110))
            card.setStyleSheet(f"""
                background:#ffffff;
                border-radius:{self.scale(14)}px;
                border-left:{self.scale(4)}px solid {color};
                box-shadow: 0 {self.scale(4)}px {self.scale(12)}px rgba(0,0,0,0.05);
            """)

            vbox = QVBoxLayout(card)
            vbox.setContentsMargins(16,16,16,16)

            # Header Layout (Title + Optional Button)
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0,0,0,0)
            
            t = QLabel(text)
            t.setStyleSheet(f"color:#4b5563; font-size:{self.scale_font(13)}px; font-weight:600;")
            header_layout.addWidget(t)
            header_layout.addStretch()

            # Special case for "Revenus nets"
            if text == "Revenus nets":
                self.revenue_hidden = False
                self.toggle_revenue_btn = QPushButton("👁️")
                self.toggle_revenue_btn.setFixedSize(self.scale(30), self.scale(20))
                self.toggle_revenue_btn.setCursor(Qt.PointingHandCursor)
                self.toggle_revenue_btn.setStyleSheet(f"""
                    QPushButton {{ border:none; background:transparent; font-size:{self.scale_font(14)}px; }}
                    QPushButton:hover {{ background:#f3f4f6; border-radius:{self.scale(4)}px; }}
                """)
                self.toggle_revenue_btn.clicked.connect(self.toggle_revenue_visibility)
                header_layout.addWidget(self.toggle_revenue_btn)

            vbox.addLayout(header_layout)
            
            label.setStyleSheet(f"color:{color}; font-size:{self.scale_font(32)}px; font-weight:800;")
            label.setAlignment(Qt.AlignCenter)

            vbox.addStretch()
            vbox.addWidget(label)

            # 2 columns on small screens, 3 on big
            row = i // 2
            col = i % 2
            if self.width() > 1000:
                col = i % 3
                row = i // 3
            stats_grid.addWidget(card, row, col)

        layout.addWidget(stats_widget)


        # ================== ROW 1: Agency + Slideshow (Stack on small screens) ==================
        row1 = QWidget()
        row1_layout = QVBoxLayout(row1)
        row1_layout.setSpacing(20)

        if self.width() > 900:
            row1_layout = QHBoxLayout(row1)
            row1_layout.setSpacing(20)

        # Agency Card
        agency = QWidget()
        agency.setStyleSheet("background:white; border-radius:14px; padding:20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);")
        form = QFormLayout(agency)
        form.setLabelAlignment(Qt.AlignRight)
        form.setVerticalSpacing(10)

        infos = [
            ("Agence", self.settings.get("nom_agence", "LOCATOP")),
            ("Propriétaire", self.settings.get("proprietaire", "Aissaoui Abdelkader")),
            ("Téléphone", self.settings.get("telephone", "0775868765")),
            ("Adresse", self.settings.get("adresse", "Nedroma, Algérie")),
        ]
        for k, v in infos:
            form.addRow(QLabel(f"<b>{k}:</b>"), QLabel(f"<span style='color:#1e40af; font-weight:600;'>{v}</span>"))



        # ================== ROW 2: Chart + Top 3 ==================
        row2 = QVBoxLayout() if self.width() < 1000 else QHBoxLayout()
        row2.setSpacing(20)

        # Chart
        chart_box = QWidget()
        chart_box.setStyleSheet("background:white; border-radius:14px; padding:20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);")
        cv = QVBoxLayout(chart_box)
        cv.addWidget(QLabel("Réparations par mois", styleSheet="font-size:16px; font-weight:700; color:#111827;"))
        self.reparations_chart = FigureCanvas(Figure(figsize=(8,5)))
        self.reparations_chart.figure.patch.set_facecolor('white')
        cv.addWidget(self.reparations_chart)
        row2.addWidget(chart_box)

        # Top 3 — Clean & Professional
        self.top3_widget = QWidget()
        self.top3_widget.setStyleSheet("background:white; border-radius:14px; padding:20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);")
        tv = QVBoxLayout(self.top3_widget)
        tv.addWidget(QLabel("Top 3 véhicules loués", styleSheet="font-size:16px; font-weight:700; color:#111827; margin-bottom:10px;"))
        self.top3_cards_layout = QHBoxLayout()
        self.top3_cards_layout.setSpacing(12)
        tv.addLayout(self.top3_cards_layout)
        tv.addStretch()
        row2.addWidget(self.top3_widget)

        row2_widget = QWidget()
        row2_widget.setLayout(row2)
        layout.addWidget(row2_widget)

        # ================== CALENDAR ==================
        cal = QWidget()
        cal.setStyleSheet("background:white; border-radius:14px ; box-shadow: 0 4px 12px rgba(0,0,0,0.05);")
        cv = QVBoxLayout(cal)
        cv.addWidget(QLabel("Calendrier des retours", styleSheet="font-size:16px; font-weight:700; color:#111827; margin:10px;"))
        self.calendar_current = QCalendarWidget()
        self.calendar_current.setGridVisible(True)
        self.calendar_current.clicked.connect(self.show_return_cars)
        self.calendar_current.setStyleSheet("""
            QCalendarWidget QToolButton { color: #000000; font-weight: bold; font-size: 15px; }
            QCalendarWidget { background: white; border-radius: 12px; margin-top:50px;}
        """)
        cv.addWidget(self.calendar_current)
        layout.addWidget(cal)

        layout.addStretch()

        # ================== FINAL SETUP ==================
        self.setMinimumSize(self.scale(800), self.scale(600))
        if self.content_stack.count() > 0:
            old = self.content_stack.widget(0)
            self.content_stack.removeWidget(old)
            old.deleteLater()
        self.content_stack.insertWidget(0, scroll)


        self.update_dashboard_stats()

        # Auto-resize fix
        scroll.resizeEvent = lambda e: page.setMinimumWidth(scroll.width() - 20)

    def toggle_revenue_visibility(self):
        self.revenue_hidden = not self.revenue_hidden
        if self.revenue_hidden:
            self.toggle_revenue_btn.setText("🔒")
            self.total_revenue_label.setText("●●●●●")
        else:
            self.toggle_revenue_btn.setText("👁️")
            self.update_dashboard_stats()  # Defines logic to restore text

    def update_reparations_chart(self):
        self.cursor.execute("""
            SELECT strftime('%Y-%m', date_completion) as month, COUNT(*)
            FROM reparations
            GROUP BY month
            ORDER BY month
        """)
        data = self.cursor.fetchall()
        self.reparations_chart.figure.clear()
        ax = self.reparations_chart.figure.add_subplot(111)
        if data:
            months, counts = zip(*data)
            ax.bar(months, counts, color='#3498DB')
            ax.set_title("Réparations par Mois", fontsize=16)
            ax.set_xlabel("Mois")
            ax.set_ylabel("Nombre de Réparations")
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, "Aucune donnée disponible", horizontalalignment='center', verticalalignment='center')
        self.reparations_chart.figure.tight_layout()
        self.reparations_chart.draw()

    def update_top3_rentals(self):
        for i in reversed(range(self.top3_cards_layout.count())):
            widget = self.top3_cards_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.cursor.execute("""
            SELECT v.modele, COUNT(l.id) as count, v.image_path
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            GROUP BY v.id
            ORDER BY count DESC
            LIMIT 3
        """)
        rows = self.cursor.fetchall()
        for index, (modele, count, image_path) in enumerate(rows):
            card = QWidget()
            card.setStyleSheet(f"""
                background-color: #333;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 70px 63px -60px #000000;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                position: relative;
                transition: background 0.8s;
            """)
            card.setProperty("hover", True)
            card.setProperty("card_index", str(index))
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignCenter)
            card_layout.setContentsMargins(0, 0, 0, 0)
            border_widget = QWidget()
            border_widget.setStyleSheet("""
                background: transparent;
                border-radius: 10px;
                position: absolute;
                z-index: 2;
                transition: border 1s;
            """)
            border_layout = QVBoxLayout(border_widget)
            border_layout.setAlignment(Qt.AlignCenter)
            border_layout.setContentsMargins(0, 0, 0, 0)
            image_label = QLabel()
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path).scaled(300, 379, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(pixmap)
            else:
                image_label.setText("Aucune image")
                image_label.setStyleSheet("""
                    color: #FFFFFF;
                    font-size: 18px;
                    font-weight: bold;
                    text-align: center;
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 5px;
                    padding: 10px;
                """)
            border_layout.addWidget(image_label)
            model_label = QLabel(modele)
            model_label.setStyleSheet("""
                color: #3498DB;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                text-align: center;
                opacity: 0;
                transition: opacity 1s;
                margin-top: 20px;
            """)
            count_label = QLabel(f"{count} Locations")
            count_label.setStyleSheet("""
                color: #FFFFFF;
                font-size: 28px;
                font-weight: bold;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                text-align: center;
                opacity: 0;
                transition: opacity 1s;
                margin-top: 10px;
            """)
            border_layout.addWidget(model_label)
            border_layout.addWidget(count_label)
            card_layout.addWidget(border_widget)
            self.top3_cards_layout.addWidget(card)
        self.top3_cards_layout.addStretch()
        self.top3_widget.setStyleSheet(self.top3_widget.styleSheet() + """
            QWidget[hover="true"]:hover {
                background-size: 600px 379px;
                transition: background-size 0.8s;
            }
            QWidget[hover="true"]:hover .border {
                border: 1px solid #FFFFFF;
            }
            QWidget[hover="true"]:hover h2,
            QWidget[hover="true"]:hover .fa {
                opacity: 1;
            }
        """)

    def show_return_cars(self, date):
        selected_date = date.toString("yyyy-MM-dd")
        self.cursor.execute("""
            SELECT l.id, v.numero_matricule, v.modele, c.nom || ' ' || c.prenom, l.cout_total
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
            WHERE date(l.date_heure_location) <= ?
            AND date(l.date_heure_location, '+' || l.jours || ' days') = ?
            AND l.statut = 'Active'
        """, (selected_date, selected_date))
        rows = self.cursor.fetchall()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.translations['fr']['calendrier']} {selected_date}")
        dialog.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(dialog)
        if not rows:
            layout.addWidget(QLabel(self.translations['fr']["aucune_voiture_retour"], styleSheet="color: #2C3E50; font-size: 14px;"))
        else:
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels([
                self.translations['fr']["id_location"],
                self.translations['fr']["matricule"],
                self.translations['fr']["modele"],
                self.translations['fr']["client"],
                self.translations['fr']["cout_total"]
            ])
            table.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 5px; font-size: 14px;")
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.horizontalHeader().setStretchLastSection(True)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            table.verticalHeader().setDefaultSectionSize(50)
            table.setRowCount(len(rows))
            for i, (loc_id, matricule, modele, client, cout_total) in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(loc_id)))
                table.setItem(i, 1, QTableWidgetItem(matricule))
                table.setItem(i, 2, QTableWidgetItem(modele))
                table.setItem(i, 3, QTableWidgetItem(client))
                table.setItem(i, 4, QTableWidgetItem(f"{cout_total:.2f}"))
            layout.addWidget(table)
        close_btn = QPushButton(self.translations['fr']["fermer"])
        close_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; border-radius: 5px;")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.resize(600, 400)  # Adjustable
        dialog.exec_()

    def update_dashboard_stats(self):
        self.update_car_statuses()

        self.cursor.execute("SELECT COUNT(*) FROM voitures")
        nb_voitures = self.cursor.fetchone()[0]
        self.nb_voitures_label.setText(str(nb_voitures))

        self.cursor.execute("SELECT COUNT(*) FROM clients")
        nb_clients = self.cursor.fetchone()[0]
        self.nb_clients_label.setText(str(nb_clients))

        date_30_days_ago = (date.today() - timedelta(days=30)).isoformat()

        self.cursor.execute("SELECT COUNT(*) FROM locations WHERE date_heure_location >= ?", (date_30_days_ago,))
        nb_locations = self.cursor.fetchone()[0]
        self.nb_locations_recents_label.setText(str(nb_locations))

        # Calculate Net Revenue
        self.cursor.execute("SELECT SUM(cout_total) FROM locations")
        loc_rev = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute("SELECT SUM(cout_total * payment_percentage / 100) FROM reservations WHERE statut = 'Active'")
        res_rev = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute("SELECT SUM(cost) FROM expenses")
        total_frais = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute("SELECT SUM(cout) FROM reparations")
        rep_total = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute("SELECT SUM(montant) FROM fuel_costs")
        fuel_total = self.cursor.fetchone()[0] or 0.0

        total_revenue = loc_rev + res_rev - total_frais - rep_total - fuel_total

        # Update Reservations Label
        self.cursor.execute("SELECT COUNT(*) FROM reservations WHERE statut = 'Active'")
        nb_reservations = self.cursor.fetchone()[0]
        self.nb_reservations_label.setText(str(nb_reservations))

        # Check privacy toggle and update revenue label
        if hasattr(self, 'revenue_hidden') and self.revenue_hidden:
            self.total_revenue_label.setText("●●●●●")
        else:
            self.total_revenue_label.setText(f"{total_revenue:,.2f} DA")

        self.cursor.execute("SELECT AVG(jours) FROM locations")
        avg_duration = self.cursor.fetchone()[0] or 0
        self.avg_duration_label.setText(f"{avg_duration:.1f} jours")

        self.update_reparations_chart()
        self.update_top3_rentals()

    def setup_voitures_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(18)

        # ================== TITRE ==================
        title = QLabel("Gestion des Véhicules")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#111827; margin-bottom:10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== CARTES RÉSUMÉ (3 cartes propres) ==================
        # ================== CRÉATION DES LABELS DE COMPTEUR (OBLIGATOIRE) ==================
        self.nb_louee_label = QLabel("0")
        self.nb_disponible_label = QLabel("0")
        self.nb_reparation_label = QLabel("0")

        # ================== CARTES RÉSUMÉ (3 cartes propres) ==================
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(16)

        for text, label, color in [
            ("Véhicules Louées", self.nb_louee_label, "#dc2626"),
            ("Disponibles", self.nb_disponible_label, "#059669"),
            ("En Réparation", self.nb_reparation_label, "#d97706")
        ]:
            card = QWidget()
            card.setFixedHeight(self.scale(100))
            card.setStyleSheet(f"""
                background:white; 
                border-radius:{self.scale(16)}px; 
                border-left:{self.scale(5)}px solid {color};
                box-shadow: 0 {self.scale(6)}px {self.scale(16)}px rgba(0,0,0,0.07);
            """)
            v = QVBoxLayout(card)
            v.setContentsMargins(self.scale(18), self.scale(16), self.scale(18), self.scale(16))
            v.addWidget(QLabel(text, styleSheet=f"color:#374151; font-size:{self.scale_font(14)}px; font-weight:600;"))
            label.setStyleSheet(f"color:{color}; font-size:{self.scale_font(32)}px; font-weight:900;")
            label.setAlignment(Qt.AlignCenter)
            v.addWidget(label)
            cards_layout.addWidget(card)

        layout.addWidget(cards_widget)

        # ================== RECHERCHE ==================
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Rechercher par matricule, modèle ou marque...")
        search_bar.setStyleSheet("""
            QLineEdit {
                padding:12px 16px;
                font-size:15px;
                border:1px solid #d1d5db;
                border-radius:12px;
                background:#f9fafb;
            }
            QLineEdit:focus { border:2px solid #3b82f6; }
        """)
        search_bar.textChanged.connect(self.search_voitures)
        self.voiture_search_input = search_bar
        layout.addWidget(search_bar)

        # ================== TABLEAU MODERNE (Scroll horizontal + Actions fixes) ==================
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.voiture_table = QTableWidget()
        self.voiture_table.setColumnCount(7)
        self.voiture_table.setHorizontalHeaderLabels([
            "Matricule", "Modèle", "Marque", "Photo", "Statut", "Prix/Jour", "Actions"
        ])

        # Style ultra-pro
        self.voiture_table.setStyleSheet("""
            QTableWidget {
                background:white;
                border:1px solid #e5e7eb;
                border-radius:16px;
                gridline-color:#f3f4f6;
                font-size:18px;
            }
            QHeaderView::section {
                background:#1e40af;
                color:white;
                padding:14px;
                font-weight:bold;
                font-size:18px;
            }
        """)

        # Scroll horizontal activé + fixe la largeur des colonnes
        self.voiture_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.voiture_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        header = self.voiture_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)      # Matricule
        header.setSectionResizeMode(1, QHeaderView.Stretch)      # Modèle
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)        # Actions = largeur fixe

        # Largeur fixe pour les colonnes qui ne doivent pas s'étirer
        self.voiture_table.setColumnWidth(2, 140)   # Marque
        self.voiture_table.setColumnWidth(3, 130)   # Photo
        self.voiture_table.setColumnWidth(4, 180)   # Statut
        self.voiture_table.setColumnWidth(5, 180)   # Prix
        self.voiture_table.setColumnWidth(6, 300)   # Actions = LARGE ET FIXE

        self.voiture_table.verticalHeader().setDefaultSectionSize(110)
        self.voiture_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.voiture_table.setAlternatingRowColors(True)

        table_layout.addWidget(self.voiture_table)
        layout.addWidget(table_container, 1)

        # ================== BOUTONS BAS ==================
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()



        # ...existing code in setup_voitures_page...

        add_btn = QPushButton("Nouvelle Voiture")
        add_btn.setStyleSheet("background:#1e40af; color:white; padding:12px 28px; border-radius:12px; font-weight:bold; font-size:18px;")

        # ← FIX: Reset button to add mode when clicked
        def open_add_form():
            self.clear_voiture_form()
            self.voiture_form.setVisible(not self.voiture_form.isVisible())
            self.voiture_add_btn.setText("Enregistrer la Voiture")
            try:
                self.voiture_add_btn.clicked.disconnect()
            except TypeError:
                pass
            self.voiture_add_btn.clicked.connect(self.add_voiture)

        add_btn.clicked.connect(open_add_form)
        btn_layout.addWidget(add_btn)

        layout.addLayout(btn_layout)

        # ================== FORMULAIRE AJOUT (caché par défaut) ==================
        self.voiture_form = QWidget()
        self.voiture_form.setVisible(False)
        form_card = QWidget()
        form_card.setStyleSheet("background:white; border-radius:16px; padding:24px; box-shadow: 0 8px 25px rgba(0,0,0,0.08);")
        form_layout = QGridLayout(form_card)

        # create widgets first (avoid walrus operator for compatibility)
        self.matricule_input = QLineEdit()
        self.modele_input = QLineEdit()
        self.brand_input = QLineEdit()
        self.statut_combo = QComboBox()
        self.emplacement_input = QLineEdit()
        self.prix_jour_input = QLineEdit()
        self.image_input = QLineEdit()

        fields = [
            ("Matricule", self.matricule_input),
            ("Modèle", self.modele_input),
            ("Marque", self.brand_input),
            ("Statut", self.statut_combo),
            ("Emplacement", self.emplacement_input),
            ("Prix/Jour (DA)", self.prix_jour_input),
            ("Image", self.image_input),
        ]

        self.statut_combo.addItems(["Disponible", "Louée", "En Réparation"])

        for i, (label_text, widget) in enumerate(fields):
            lbl = QLabel(label_text + " :")
            lbl.setStyleSheet("font-weight:600; color:#374151;")
            form_layout.addWidget(lbl, i, 0)
            if widget is self.image_input:
                h = QHBoxLayout()
                h.addWidget(widget)
                browse_btn = QPushButton("Parcourir")
                browse_btn.setStyleSheet("background:#4b5563; color:white; padding:8px 16px; border-radius:8px;")
                browse_btn.clicked.connect(self.browse_image)
                h.addWidget(browse_btn)
                form_layout.addLayout(h, i, 1)
            else:
                widget.setStyleSheet("padding:10px; border:1px solid #d1d5db; border-radius:8px;")
                form_layout.addWidget(widget, i, 1)

        save_btn = QPushButton("Enregistrer la Voiture")
        save_btn.setStyleSheet("background:#059669; color:white; padding:14px; border-radius:12px; font-weight:bold; font-size:15px;")
        save_btn.clicked.connect(self.add_voiture)
        self.voiture_add_btn = save_btn

        form_layout.addWidget(save_btn, len(fields), 0, 1, 2)
        self.voiture_form.setLayout(QVBoxLayout())
        self.voiture_form.layout().addWidget(form_card)
        layout.addWidget(self.voiture_form)

        # ================== FINAL ==================
        scroll.setWidget(page)
        self.setMinimumSize(self.scale(800), self.scale(600))

        if self.content_stack.count() > 1:
            old = self.content_stack.widget(1)
            self.content_stack.removeWidget(old)
            old.deleteLater()
        self.content_stack.insertWidget(1, scroll)

        # Charger les données
        self.load_voitures()

    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Sélectionner une image", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.image_input.setText(file_path)
    
    def load_voitures(self):
        self.cursor.execute("SELECT id, numero_matricule, modele, brand, statut, prix_jour, image_path FROM voitures")
        rows = self.cursor.fetchall()
        self.voiture_table.setRowCount(len(rows))

        for row_idx, (vid, matricule, modele, brand, statut, prix_jour, image_path) in enumerate(rows):
            self.voiture_table.setItem(row_idx, 0, QTableWidgetItem(matricule))
            self.voiture_table.setItem(row_idx, 1, QTableWidgetItem(modele))
            self.voiture_table.setItem(row_idx, 2, QTableWidgetItem(brand))

            # Photo
            photo_lbl = QLabel()
            photo_lbl.setAlignment(Qt.AlignCenter)
            if image_path and os.path.exists(image_path):
                pix = QPixmap(image_path).scaled(110, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                photo_lbl.setPixmap(pix)
            else:
                photo_lbl.setText("Pas d'image")
                photo_lbl.setStyleSheet("color:#9ca3af;")
            photo_cell = QWidget()
            photo_cell.setLayout(QVBoxLayout())
            photo_cell.layout().addWidget(photo_lbl)
            photo_cell.layout().setAlignment(Qt.AlignCenter)
            self.voiture_table.setCellWidget(row_idx, 3, photo_cell)

            # Statut avec couleur
            statut_item = QTableWidgetItem(statut)
            color = {"Disponible": "#059669", "Louée": "#dc2626", "En Réparation": "#d97706"}.get(statut, "#6b7280")
            statut_item.setForeground(QColor(color))
            statut_item.setFont(QFont("Segoe UI", 18, QFont.Bold))
            self.voiture_table.setItem(row_idx, 4, statut_item)

            self.voiture_table.setItem(row_idx, 5, QTableWidgetItem(f"{prix_jour:.2f} DA"))

            # ACTIONS — GROS BOUTONS
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(8, 4, 8, 4)
            actions_layout.setSpacing(8)


            details_btn = QPushButton("Détails")
            details_btn.setStyleSheet("background:#3b82f6; color:white;")
            details_btn.clicked.connect(lambda _, v=vid: self.show_voiture_details(v))

            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet( "background:#06b6d4; color:white;")
            edit_btn.clicked.connect(lambda _, v=vid: self.edit_voiture(v))

            delete_btn = QPushButton("Supp")
            delete_btn.setStyleSheet( "background:#dc2626; color:white;")
            delete_btn.clicked.connect(lambda _, v=vid: self.delete_voiture(v))

            actions_layout.addWidget(details_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)

            self.voiture_table.setCellWidget(row_idx, 6, actions)

        # Mise à jour des compteurs
        self.cursor.execute("SELECT COUNT(*) FROM voitures WHERE statut='Louée'"); self.nb_louee_label.setText(str(self.cursor.fetchone()[0]))
        self.cursor.execute("SELECT COUNT(*) FROM voitures WHERE statut='Disponible'"); self.nb_disponible_label.setText(str(self.cursor.fetchone()[0]))
        self.cursor.execute("SELECT COUNT(*) FROM voitures WHERE statut='En Réparation'"); self.nb_reparation_label.setText(str(self.cursor.fetchone()[0]))
    
    def delete_selected_voitures(self):
        selected_rows = self.voiture_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Erreur", "Aucune voiture sélectionnée.")
            return

        reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_selection"], QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for row in selected_rows:
                vid = int(self.voiture_table.item(row.row(), 0).text())  # Assume ID in hidden or get from DB
                self.cursor.execute("DELETE FROM voitures WHERE id = ?", (vid,))
            self.conn.commit()
            self.load_voitures()

    def add_voiture(self):
        matricule = self.matricule_input.text()
        modele = self.modele_input.text()
        brand = self.brand_input.text()
        statut = self.statut_combo.currentText()
        emplacement = self.emplacement_input.text()
        prix_jour = self.prix_jour_input.text()
        image_path = self.image_input.text()

        if not all([matricule, modele, brand, prix_jour]):
            QMessageBox.warning(self, "Erreur", self.translations["fr"]["error_fields_required"])
            return

        try:
            prix_jour = float(prix_jour)
        except ValueError:
            QMessageBox.warning(self, "Erreur", self.translations["fr"]["error_prix_jour"])
            return

        # NEW: Save image to uploads folder
        final_image_path = self.save_upload(image_path, "cars")

        try:
            self.cursor.execute("""
                INSERT INTO voitures (numero_matricule, modele, brand, statut, emplacement, prix_jour, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (matricule, modele, brand, statut, emplacement, prix_jour, final_image_path))
            self.conn.commit()
            self.load_voitures()
            self.matricule_input.clear()
            self.modele_input.clear()
            self.brand_input.clear()
            self.emplacement_input.clear()
            self.prix_jour_input.clear()
            self.image_input.clear()
            self.voiture_form.setVisible(False)
                # ← AFTER SUCCESSFUL ADD
            self.load_voitures()
            self.clear_voiture_form()
            self.voiture_form.setVisible(False)
            QMessageBox.information(self, "Succès", "Voiture ajoutée avec succès.")
        
        
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Matricule déjà existant.")

    def edit_voiture(self, voiture_id):
        self.cursor.execute("SELECT numero_matricule, modele, brand, statut, emplacement, prix_jour, image_path FROM voitures WHERE id = ?", (voiture_id,))
        data = self.cursor.fetchone()
        if data:
            matricule, modele, brand, statut, emplacement, prix_jour, image_path = data
            self.matricule_input.setText(matricule)
            self.modele_input.setText(modele)
            self.brand_input.setText(brand)
            self.statut_combo.setCurrentText(statut)
            self.emplacement_input.setText(emplacement or "")
            self.prix_jour_input.setText(str(prix_jour))
            self.image_input.setText(image_path or "")
            self.voiture_form.setVisible(True)
            self.voiture_add_btn.setText("Mettre à jour la Voiture")
            
            # ← DISCONNECT ALL PREVIOUS CONNECTIONS
            try:
                self.voiture_add_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            
            # ← CONNECT TO update_voiture
            self.voiture_add_btn.clicked.connect(lambda: self.update_voiture(voiture_id))


    def update_voiture(self, voiture_id):
        matricule = self.matricule_input.text().strip()
        modele = self.modele_input.text().strip()
        brand = self.brand_input.text().strip()
        statut = self.statut_combo.currentText()
        emplacement = self.emplacement_input.text().strip()
        prix_jour = self.prix_jour_input.text().strip()
        image_path = self.image_input.text().strip()
        if not (matricule and modele and brand and prix_jour):
            QMessageBox.warning(self, "Erreur", self.translations["fr"]["error_fields_required"])
            return
        try:
            prix_jour = float(prix_jour)
            if prix_jour <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erreur", self.translations["fr"]["error_prix_jour"])
            return

        # NEW: Save image to uploads folder
        final_image_path = self.save_upload(image_path, "cars")

        try:
            self.cursor.execute("""
                UPDATE voitures SET numero_matricule = ?, modele = ?, brand = ?, statut = ?, emplacement = ?, prix_jour = ?, image_path = ?
                WHERE id = ?
            """, (matricule, modele, brand, statut, emplacement, prix_jour, final_image_path, voiture_id))
            self.conn.commit()
            self.load_voitures()
            self.clear_voiture_form()
            self.voiture_form.setVisible(False)
            self.refresh_voiture_combos()
            self.refresh_client_completers()
            
            # ← RESET BUTTON TO ADD MODE
            self.voiture_add_btn.setText("Enregistrer la Voiture")
            try:
                self.voiture_add_btn.clicked.disconnect()
            except TypeError:
                pass
            self.voiture_add_btn.clicked.connect(self.add_voiture)
            
            self.car_images = [(row[7], row[2]) for row in self.cursor.execute("SELECT * FROM voitures").fetchall() if row[7]]

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Matricule doit être unique.")
        
    def clear_voiture_form(self):
        self.matricule_input.clear()
        self.modele_input.clear()
        self.brand_input.clear()
        self.statut_combo.setCurrentIndex(0)
        self.emplacement_input.clear()
        self.prix_jour_input.clear()
        self.image_input.clear()        
    def delete_voiture(self, voiture_id):
        reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_voiture"], QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM voitures WHERE id = ?", (voiture_id,))
            self.conn.commit()
            self.load_voitures()

    def search_voitures(self, text):
        for row in range(self.voiture_table.rowCount()):
            hidden = True
            for col in [0, 1, 2]:  # Matricule, Modèle, Marque
                item = self.voiture_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    hidden = False
                    break
            self.voiture_table.setRowHidden(row, hidden)

    def show_voiture_details(self, voiture_id):
        # Fetch voiture data
        self.cursor.execute("""
            SELECT numero_matricule, modele, brand, statut, emplacement, prix_jour, image_path
            FROM voitures WHERE id = ?
        """, (voiture_id,))
        row = self.cursor.fetchone()
        if not row:
            return

        matricule, modele, brand, statut, emplacement, prix_jour, image_path = row

        # Calcul des revenus nets
        self.cursor.execute("""
            SELECT SUM(cout_total) FROM locations WHERE voiture_id = ?
        """, (voiture_id,))
        revenus = self.cursor.fetchone()[0] or 0

        self.cursor.execute("""
            SELECT SUM(cout) FROM reparations WHERE voiture_id = ?
        """, (voiture_id,))
        depenses_reparations = self.cursor.fetchone()[0] or 0

        self.cursor.execute("""
            SELECT SUM(montant) FROM fuel_costs WHERE voiture_id = ?
        """, (voiture_id,))
        depenses_carburant = self.cursor.fetchone()[0] or 0

        revenus_nets = revenus - depenses_reparations - depenses_carburant

        # Dialog setup (mimic client details structure)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Détails de la Voiture - {matricule}")
        dialog.setStyleSheet("background-color: white;")
        dialog.setMinimumSize(self.scale(800), self.scale(600))

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
        main_layout.setSpacing(self.scale(15))

        # Top section: Voiture info form + image + revenus
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(self.scale(20))

        # Form layout for info
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(self.scale(10))
        form_layout.setContentsMargins(0, 0, 0, 0)

        fields = [
            ("Matricule", matricule),
            ("Modèle", modele),
            ("Marque", brand),
            ("Statut", statut),
            ("Emplacement", emplacement or "N/A"),
            ("Prix/Jour", f"{prix_jour:.2f} DA"),
        ]

        for label_text, value in fields:
            lbl = QLabel(label_text + ":")
            lbl.setStyleSheet(f"font-weight: bold; color: #374151; font-size: {self.scale_font(18)}px;")
            val = QLabel(str(value))
            val.setStyleSheet(f"color: #1e40af; font-size: {self.scale_font(18)}px;")
            form_layout.addRow(lbl, val)

        top_layout.addWidget(form_widget, stretch=1)

        # Image
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet(f"border: 1px solid #e5e7eb; border-radius: {self.scale(10)}px; background: #f9fafb;")
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(self.scale(300), self.scale(300), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(pixmap)
        else:
            image_label.setText("Aucune image disponible")
            image_label.setStyleSheet(f"color: #9ca3af; font-size: {self.scale_font(16)}px;")
        top_layout.addWidget(image_label)

        # Revenus nets
        revenus_widget = QWidget()
        revenus_layout = QVBoxLayout(revenus_widget)
        revenus_layout.setAlignment(Qt.AlignCenter)
        revenus_layout.setSpacing(self.scale(10))

        revenus_title = QLabel("Revenus Nets")
        revenus_title.setStyleSheet(f"font-size: {self.scale_font(18)}px; font-weight: bold; color: #059669;")
        revenus_layout.addWidget(revenus_title)

        self.revenus_value_label = QLabel(f"{revenus_nets:.2f} DA")   # ← Ajouter self. pour pouvoir le rafraîchir
        self.revenus_value_label.setStyleSheet(f"font-size: {self.scale_font(28)}px; font-weight: bold; color: #059669;")
        revenus_layout.addWidget(self.revenus_value_label)


        top_layout.addWidget(revenus_widget)
        main_layout.addWidget(top_widget)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("color: #e5e7eb;")
        main_layout.addWidget(divider)

        # Tabs for history (reparations and carburant)
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #e5e7eb; border-radius: {self.scale(10)}px; background: white; }}
            QTabBar::tab {{ background: #f3f4f6; color: #4b5563; padding: {self.scale(12)}px {self.scale(30)}px;  font-weight: 14px; }}
            QTabBar::tab:selected {{ background: #1e40af; color: white; }}
        """)
        main_layout.addWidget(tabs, stretch=1)

        # Tab 1: Historique Réparations
        rep_tab = QWidget()
        rep_layout = QVBoxLayout(rep_tab)
        rep_layout.setContentsMargins(self.scale(10), self.scale(10), self.scale(10), self.scale(10))
        rep_layout.setSpacing(self.scale(10))

        rep_title = QLabel("Historique des Réparations")
        rep_title.setStyleSheet(f"font-size: {self.scale_font(18)}px; font-weight: bold; color: #111827;")
        rep_layout.addWidget(rep_title)

        # === BARRE DE RECHERCHE RÉPARATIONS ===
        rep_search = QLineEdit()
        rep_search.setPlaceholderText("Rechercher par description...")
        rep_search.setStyleSheet(f"""
            QLineEdit {{
                padding: {self.scale(10)}px;
                border: 1px solid #d1d5db;
                border-radius: {self.scale(8)}px;
                font-size: {self.scale_font(14)}px;
            }}
        """)
        rep_search.textChanged.connect(lambda text: self.filter_reparations(voiture_id, text))
        rep_layout.addWidget(rep_search)

        self.rep_table = QTableWidget()
        self.rep_table.setColumnCount(5)
        self.rep_table.setHorizontalHeaderLabels(["ID", "Description", "Coût (DA)", "Date", "Actions"])
        self.rep_table.setStyleSheet(f"""
            QTableWidget {{ border: 1px solid #e5e7eb; border-radius: {self.scale(8)}px; gridline-color: #f3f4f6; font-size: {self.scale_font(13)}px; }}
            QHeaderView::section {{ background: #1e40af; color: white; padding: {self.scale(8)}px; font-weight: bold; }}
        """)
        self.rep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rep_table.setColumnWidth(0, self.scale(60))
        self.rep_table.setColumnWidth(2, self.scale(100))
        self.rep_table.setColumnWidth(3, self.scale(120))
        self.rep_table.setColumnWidth(4, self.scale(200))
        self.rep_table.setAlternatingRowColors(True)
        self.rep_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        rep_layout.addWidget(self.rep_table, stretch=1)

        # Add button
        add_rep_btn = QPushButton("Ajouter Réparation")
        add_rep_btn.setStyleSheet(f"background: #059669; color: white; padding: {self.scale(12)}px; border-radius: {self.scale(8)}px; font-weight: bold;")
        add_rep_btn.clicked.connect(lambda: self.add_reparation_popup(voiture_id))
        rep_layout.addWidget(add_rep_btn, alignment=Qt.AlignRight)

        tabs.addTab(rep_tab, "Réparations")

        # ================== Tab 2: Historique Carburant (AMÉLIORÉ) ==================
        fuel_tab = QWidget()
        fuel_layout = QVBoxLayout(fuel_tab)
        fuel_layout.setContentsMargins(self.scale(10), self.scale(10), self.scale(10), self.scale(10))
        fuel_layout.setSpacing(self.scale(10))

        fuel_title = QLabel("Historique des Carburants")
        fuel_title.setStyleSheet(f"font-size: {self.scale_font(18)}px; font-weight: bold; color: #111827;")
        fuel_layout.addWidget(fuel_title)

        # === BARRE DE RECHERCHE CARBURANT ===
        fuel_search = QLineEdit()
        fuel_search.setPlaceholderText("Rechercher par type...")
        fuel_search.setStyleSheet(rep_search.styleSheet())
        fuel_search.textChanged.connect(lambda text: self.filter_carburants(voiture_id, text))
        fuel_layout.addWidget(fuel_search)

        self.fuel_table = QTableWidget()
        self.fuel_table.setColumnCount(5)
        self.fuel_table.setHorizontalHeaderLabels(["ID", "Montant (DA)", "Date", "Type", "Actions"])
        self.fuel_table.setStyleSheet(self.rep_table.styleSheet())
        self.fuel_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.fuel_table.setColumnWidth(0, self.scale(60))
        self.fuel_table.setColumnWidth(1, self.scale(100))
        self.fuel_table.setColumnWidth(2, self.scale(120))
        self.fuel_table.setColumnWidth(4, self.scale(200))
        self.fuel_table.setAlternatingRowColors(True)
        self.fuel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        fuel_layout.addWidget(self.fuel_table, stretch=1)

        # Add button
        add_fuel_btn = QPushButton("Ajouter Carburant")
        add_fuel_btn.setStyleSheet(f"background: #d97706; color: white; padding: {self.scale(12)}px; border-radius: {self.scale(8)}px; font-weight: bold;")
        add_fuel_btn.clicked.connect(lambda: self.add_carburant_popup(voiture_id))
        fuel_layout.addWidget(add_fuel_btn, alignment=Qt.AlignRight)

        tabs.addTab(fuel_tab, "Carburant")

        # Load data
        self.load_reparations(voiture_id)
        self.load_carburants(voiture_id)

        # Close button
        close_btn = QPushButton("Fermer")
        close_btn.setStyleSheet(f"background: #3b82f6; color: white; padding: {self.scale(12)}px; border-radius: {self.scale(8)}px; font-weight: bold;")
        close_btn.clicked.connect(dialog.close)
        main_layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        
        dialog.exec_()

    def add_reparation_popup(self, voiture_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter Réparation")
        dialog.setStyleSheet("background-color: white;")
        dialog.setFixedSize(self.scale(420), self.scale(280))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
        layout.setSpacing(self.scale(15))

        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Description de la réparation")
        layout.addWidget(desc_input)

        cout_input = QLineEdit()
        cout_input.setPlaceholderText("Coût (DA)")
        layout.addWidget(cout_input)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.currentDate())
        layout.addWidget(date_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet(f"background:#059669; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px; font-weight:bold;")
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"background:#6b7280; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px;")
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def save_and_refresh():
            try:
                cout = float(cout_input.text().strip() or "0")
                if cout < 0:
                    raise ValueError
                desc = desc_input.text().strip()
                if not desc:
                    QMessageBox.warning(dialog, "Erreur", "La description est obligatoire.")
                    return

                self.cursor.execute("""
                    INSERT INTO reparations (voiture_id, description, cout, date_completion)
                    VALUES (?, ?, ?, ?)
                """, (voiture_id, desc, cout, date_input.date().toString("yyyy-MM-dd")))
                self.conn.commit()

                QMessageBox.information(dialog, "Succès", "Réparation ajoutée avec succès.")
                
                # Rafraîchir les deux tableaux + revenus nets dans le popup principal
                self.load_reparations(voiture_id)
                self.load_carburants(voiture_id)
                self.refresh_voiture_revenus_net(voiture_id)  # Nouvelle fonction ci-dessous
                
                dialog.accept()

            except ValueError:
                QMessageBox.warning(dialog, "Erreur", "Veuillez entrer un coût valide.")

        save_btn.clicked.connect(save_and_refresh)
        dialog.exec_()


    def add_carburant_popup(self, voiture_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter Carburant")
        dialog.setStyleSheet("background-color: white;")
        dialog.setFixedSize(self.scale(420), self.scale(280))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
        layout.setSpacing(self.scale(15))

        montant_input = QLineEdit()
        montant_input.setPlaceholderText("Montant (DA)")
        layout.addWidget(montant_input)

        type_input = QLineEdit()
        type_input.setPlaceholderText("Type (ex: Essence, Gasoil)")
        layout.addWidget(type_input)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.currentDate())
        layout.addWidget(date_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet(f"background:#d97706; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px; font-weight:bold;")
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"background:#6b7280; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px;")
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def save_and_refresh():
            try:
                montant = float(montant_input.text().strip() or "0")
                if montant < 0:
                    raise ValueError

                self.cursor.execute("""
                    INSERT INTO fuel_costs (voiture_id, montant, date, type)
                    VALUES (?, ?, ?, ?)
                """, (voiture_id, montant, date_input.date().toString("yyyy-MM-dd"), type_input.text().strip()))
                self.conn.commit()

                QMessageBox.information(dialog, "Succès", "Carburant ajouté avec succès.")
                
                # Rafraîchir les tableaux + revenus nets
                self.load_reparations(voiture_id)
                self.load_carburants(voiture_id)
                self.refresh_voiture_revenus_net(voiture_id)
                
                dialog.accept()

            except ValueError:
                QMessageBox.warning(dialog, "Erreur", "Veuillez entrer un montant valide.")

        save_btn.clicked.connect(save_and_refresh)
        dialog.exec_()


    # Nouvelle fonction pour rafraîchir uniquement le label "Revenus Nets"
    def refresh_voiture_revenus_net(self, voiture_id):
        # Recalculer les revenus nets
        self.cursor.execute("SELECT SUM(cout_total) FROM locations WHERE voiture_id = ?", (voiture_id,))
        revenus = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT SUM(cout) FROM reparations WHERE voiture_id = ?", (voiture_id,))
        rep = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT SUM(montant) FROM fuel_costs WHERE voiture_id = ?", (voiture_id,))
        fuel = self.cursor.fetchone()[0] or 0

        revenus_nets = revenus - rep - fuel

        # Mettre à jour le QLabel des revenus nets (doit être stocké comme attribut dans show_voiture_details)
        if hasattr(self, "revenus_value_label"):
            self.revenus_value_label.setText(f"{revenus_nets:.2f} DA")
    # ================== NOUVELLES FONCTIONS DE FILTRAGE ==================

    def filter_reparations(self, voiture_id, search_text):
        """Filtre les réparations selon le texte de recherche"""
        search = search_text.lower().strip()
        
        self.cursor.execute("""
            SELECT id, description, cout, date_completion
            FROM reparations 
            WHERE voiture_id = ?
            AND (lower(description) LIKE ? OR date_completion LIKE ?)
            ORDER BY date_completion DESC
        """, (voiture_id, f"%{search}%", f"%{search}%"))
        
        rows = self.cursor.fetchall()
        self.rep_table.setRowCount(len(rows))
        
        for i, (rid, desc, cout, date_comp) in enumerate(rows):
            self.rep_table.setItem(i, 0, QTableWidgetItem(str(rid)))
            self.rep_table.setItem(i, 1, QTableWidgetItem(desc))
            self.rep_table.setItem(i, 2, QTableWidgetItem(f"{cout:.2f}"))
            self.rep_table.setItem(i, 3, QTableWidgetItem(date_comp))
            
            # === BOUTONS ACTIONS ===
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet("background:#06b6d4; color:white; padding:4px 8px;")
            edit_btn.clicked.connect(lambda _, r=rid: self.edit_reparation(voiture_id, r))
            
            del_btn = QPushButton("Suppr")
            del_btn.setStyleSheet("background:#dc2626; color:white; padding:4px 8px;")
            del_btn.clicked.connect(lambda _, r=rid: self.delete_reparation(voiture_id, r))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)
            self.rep_table.setCellWidget(i, 4, actions)


    def filter_carburants(self, voiture_id, search_text):
        """Filtre les carburants selon le texte de recherche"""
        search = search_text.lower().strip()
        
        self.cursor.execute("""
            SELECT id, montant, date, type
            FROM fuel_costs 
            WHERE voiture_id = ?
            AND (lower(type) LIKE ? OR date LIKE ?)
            ORDER BY date DESC
        """, (voiture_id, f"%{search}%", f"%{search}%"))
        
        rows = self.cursor.fetchall()
        self.fuel_table.setRowCount(len(rows))
        
        for i, (fid, montant, date, typ) in enumerate(rows):
            self.fuel_table.setItem(i, 0, QTableWidgetItem(str(fid)))
            self.fuel_table.setItem(i, 1, QTableWidgetItem(f"{montant:.2f}"))
            self.fuel_table.setItem(i, 2, QTableWidgetItem(date))
            self.fuel_table.setItem(i, 3, QTableWidgetItem(typ))
            
            # === BOUTONS ACTIONS ===
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet("background:#06b6d4; color:white; padding:4px 8px;")
            edit_btn.clicked.connect(lambda _, f=fid: self.edit_carburant(voiture_id, f))
            
            del_btn = QPushButton("Suppr")
            del_btn.setStyleSheet("background:#dc2626; color:white; padding:4px 8px;")
            del_btn.clicked.connect(lambda _, f=fid: self.delete_carburant(voiture_id, f))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)
            self.fuel_table.setCellWidget(i, 4, actions)


    # ================== FONCTIONS D'ÉDITION ==================

    def edit_reparation(self, voiture_id, rep_id):
        """Édite une réparation existante"""
        self.cursor.execute("SELECT description, cout, date_completion FROM reparations WHERE id = ?", (rep_id,))
        desc, cout, date_comp = self.cursor.fetchone()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier Réparation")
        dialog.setStyleSheet("background-color: white;")
        dialog.setFixedSize(self.scale(420), self.scale(280))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
        layout.setSpacing(self.scale(15))

        desc_input = QLineEdit(desc)
        desc_input.setPlaceholderText("Description")
        layout.addWidget(desc_input)

        cout_input = QLineEdit(str(cout))
        cout_input.setPlaceholderText("Coût (DA)")
        layout.addWidget(cout_input)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.fromString(date_comp, "yyyy-MM-dd"))
        layout.addWidget(date_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet(f"background:#059669; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px; font-weight:bold;")
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"background:#6b7280; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px;")
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def update():
            try:
                new_cout = float(cout_input.text().strip())
                new_desc = desc_input.text().strip()
                
                if not new_desc:
                    QMessageBox.warning(dialog, "Erreur", "La description est obligatoire.")
                    return

                self.cursor.execute("""
                    UPDATE reparations SET description = ?, cout = ?, date_completion = ?
                    WHERE id = ?
                """, (new_desc, new_cout, date_input.date().toString("yyyy-MM-dd"), rep_id))
                self.conn.commit()

                self.filter_reparations(voiture_id, "")
                self.refresh_voiture_revenus_net(voiture_id)
                dialog.accept()
            except ValueError:
                QMessageBox.warning(dialog, "Erreur", "Coût invalide.")

        save_btn.clicked.connect(update)
        dialog.exec_()


    def edit_carburant(self, voiture_id, fuel_id):
        """Édite un carburant existant"""
        self.cursor.execute("SELECT montant, date, type FROM fuel_costs WHERE id = ?", (fuel_id,))
        montant, date_fuel, typ = self.cursor.fetchone()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier Carburant")
        dialog.setStyleSheet("background-color: white;")
        dialog.setFixedSize(self.scale(420), self.scale(280))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
        layout.setSpacing(self.scale(15))

        montant_input = QLineEdit(str(montant))
        montant_input.setPlaceholderText("Montant (DA)")
        layout.addWidget(montant_input)

        type_input = QLineEdit(typ)
        type_input.setPlaceholderText("Type (ex: Essence, Gasoil)")
        layout.addWidget(type_input)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.fromString(date_fuel, "yyyy-MM-dd"))
        layout.addWidget(date_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet(f"background:#d97706; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px; font-weight:bold;")
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"background:#6b7280; color:white; padding:{self.scale(12)}px {self.scale(24)}px; border-radius:{self.scale(8)}px;")
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def update():
            try:
                new_montant = float(montant_input.text().strip())
                
                self.cursor.execute("""
                    UPDATE fuel_costs SET montant = ?, date = ?, type = ?
                    WHERE id = ?
                """, (new_montant, date_input.date().toString("yyyy-MM-dd"), type_input.text().strip(), fuel_id))
                self.conn.commit()

                self.filter_carburants(voiture_id, "")
                self.refresh_voiture_revenus_net(voiture_id)
                dialog.accept()
            except ValueError:
                QMessageBox.warning(dialog, "Erreur", "Montant invalide.")

        save_btn.clicked.connect(update)
        dialog.exec_()


    # ================== FONCTIONS DE SUPPRESSION ==================

    def delete_reparation(self, voiture_id, rep_id):
        """Supprime une réparation"""
        reply = QMessageBox.question(self, "Confirmer", 
            "Voulez-vous vraiment supprimer cette réparation ?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM reparations WHERE id = ?", (rep_id,))
            self.conn.commit()
            self.filter_reparations(voiture_id, "")
            self.refresh_voiture_revenus_net(voiture_id)
            QMessageBox.information(self, "Succès", "Réparation supprimée.")


    def delete_carburant(self, voiture_id, fuel_id):
        """Supprime un carburant"""
        reply = QMessageBox.question(self, "Confirmer", 
            "Voulez-vous vraiment supprimer ce carburant ?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM fuel_costs WHERE id = ?", (fuel_id,))
            self.conn.commit()
            self.filter_carburants(voiture_id, "")
            self.refresh_voiture_revenus_net(voiture_id)
            QMessageBox.information(self, "Succès", "Carburant supprimé.")


    # ================== MISE À JOUR DES FONCTIONS LOAD ==================




    def load_reparations(self, voiture_id):
        self.cursor.execute("""
            SELECT id, description, cout, date_completion
            FROM reparations WHERE voiture_id = ?
        """, (voiture_id,))
        rows = self.cursor.fetchall()
        self.rep_table.setRowCount(len(rows))
        for i, (rid, desc, cout, date_comp) in enumerate(rows):
            self.rep_table.setItem(i, 0, QTableWidgetItem(str(rid)))
            self.rep_table.setItem(i, 1, QTableWidgetItem(desc))
            self.rep_table.setItem(i, 2, QTableWidgetItem(f"{cout:.2f}"))
            self.rep_table.setItem(i, 3, QTableWidgetItem(date_comp))

        self.filter_reparations(voiture_id, "")  # Utilise la fonction de filtrage


    def load_carburants(self, voiture_id):
        self.cursor.execute("""
            SELECT id, montant, date, type
            FROM fuel_costs WHERE voiture_id = ?
        """, (voiture_id,))
        rows = self.cursor.fetchall()
        self.fuel_table.setRowCount(len(rows))
        for i, (fid, montant, date, typ) in enumerate(rows):
            self.fuel_table.setItem(i, 0, QTableWidgetItem(str(fid)))
            self.fuel_table.setItem(i, 1, QTableWidgetItem(f"{montant:.2f}"))
            self.fuel_table.setItem(i, 2, QTableWidgetItem(date))
            self.fuel_table.setItem(i, 3, QTableWidgetItem(typ))

        self.filter_carburants(voiture_id, "")  # Utilise la fonction de filtrage





    
    
    
    
    def setup_clients_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(18)

        # ================== TITRE ==================
        title = QLabel("Gestion des Clients")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#111827; margin-bottom:10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== CARTES RÉSUMÉ ==================
        self.nb_homme_label = QLabel("0")
        self.nb_femme_label = QLabel("0")

        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(16)

        for text, label, color in [
            ("Clients Hommes", self.nb_homme_label, "#1d4ed8"),
            ("Clients Femmes", self.nb_femme_label, "#d946ef")
        ]:
            card = QWidget()
            card.setFixedHeight(100)
            card.setStyleSheet(f"""
                background:white; border-radius:16px; border-left:5px solid {color};
                box-shadow: 0 6px 16px rgba(0,0,0,0.07);
            """)
            v = QVBoxLayout(card)
            v.setContentsMargins(18,16,18,16)
            v.addWidget(QLabel(text, styleSheet="color:#374151; font-size:14px; font-weight:600;"))
            label.setStyleSheet(f"color:{color}; font-size:32px; font-weight:900;")
            label.setAlignment(Qt.AlignCenter)
            v.addWidget(label)
            cards_layout.addWidget(card)

        layout.addWidget(cards_widget)

        # ================== RECHERCHE ==================
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Rechercher par nom ou prénom...")
        search_bar.setStyleSheet("padding:12px 16px; font-size:15px; border:1px solid #d1d5db; border-radius:12px; background:#f9fafb;")
        search_bar.textChanged.connect(self.search_clients)
        self.client_search_input = search_bar
        layout.addWidget(search_bar)

        # ================== TABLEAU CLIENTS ==================
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(10)
        self.client_table.setHorizontalHeaderLabels([
            "Nom", "Prénom", "Genre", "Date Naiss.", "Lieu Naiss.", "Adresse", "N° Permis", "Date Permis", "Téléphone", "Actions"
        ])
        self.client_table.setStyleSheet("""
            QTableWidget { background:white; border:1px solid #e5e7eb; border-radius:16px; gridline-color:#f3f4f6; font-size:18px; }
            QHeaderView::section { background:#1e40af; color:white; padding:14px; font-weight:bold; font-size:18px; }
        """)
        self.client_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.client_table.verticalHeader().setDefaultSectionSize(60)
        self.client_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.client_table.setAlternatingRowColors(True)

        header = self.client_table.horizontalHeader()
        # Colonnes qui s'étirent (Nom & Prénom)
        header.setSectionResizeMode(0, QHeaderView.Stretch)   # Nom
        header.setSectionResizeMode(1, QHeaderView.Stretch)   # Prénom

        # Toutes les autres colonnes = taille fixe (plus beau !)
        header.setSectionResizeMode(2, QHeaderView.Fixed)     # Genre
        header.setSectionResizeMode(3, QHeaderView.Fixed)     # Date Naiss.
        header.setSectionResizeMode(4, QHeaderView.Fixed)     # Lieu Naiss.
        header.setSectionResizeMode(5, QHeaderView.Fixed)     # Adresse
        header.setSectionResizeMode(6, QHeaderView.Fixed)     # N° Permis
        header.setSectionResizeMode(7, QHeaderView.Fixed)     # Date Permis
        header.setSectionResizeMode(8, QHeaderView.Fixed)     # Téléphone
        header.setSectionResizeMode(9, QHeaderView.Fixed)     # Actions (fixe)

        # Largeurs idéales (testées et validées)
        self.client_table.setColumnWidth(2, 90)     # Genre
        self.client_table.setColumnWidth(3, 130)    # Date Naiss.
        self.client_table.setColumnWidth(4, 160)    # Lieu Naiss.
        self.client_table.setColumnWidth(5, 200)    # Adresse (un peu plus large)
        self.client_table.setColumnWidth(6, 140)    # N° Permis
        self.client_table.setColumnWidth(7, 130)    # Date Permis
        self.client_table.setColumnWidth(8, 130)    # Téléphone
        self.client_table.setColumnWidth(9, 280)    # Actions → boutons bien visibles
        layout.addWidget(self.client_table, 1)

        # ================== BOUTON NOUVEAU CLIENT ==================
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        add_btn = QPushButton("Nouveau Client")
        add_btn.setStyleSheet("background:#1e40af; color:white; padding:12px 28px; border-radius:12px; font-weight:bold; font-size:15px;")
        
        # ← FIX: Reset to add mode when clicking "Nouveau Client"
        def open_add_client_form():
            self.clear_client_form()
            self.client_form.setVisible(not self.client_form.isVisible())
            self.client_add_btn.setText("Enregistrer le Client")
            try:
                self.client_add_btn.clicked.disconnect()
            except TypeError:
                pass
            self.client_add_btn.clicked.connect(self.add_client)
        
        add_btn.clicked.connect(open_add_client_form)
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)

        # ================== FORMULAIRE AJOUT/MODIF CLIENT ==================
        self.client_form = QWidget()
        self.client_form.setVisible(False)
        form_card = QWidget()
        form_card.setStyleSheet("background:white; border-radius:16px; padding:24px; box-shadow: 0 8px 25px rgba(0,0,0,0.08);")
        form_layout = QGridLayout(form_card)

        self.client_nom_input = QLineEdit()
        self.client_prenom_input = QLineEdit()
        self.client_genre_combo = QComboBox()
        self.client_genre_combo.addItems(["Homme", "Femme"])
        self.client_date_naissance_input = QDateEdit()
        self.client_date_naissance_input.setCalendarPopup(True)
        self.client_date_naissance_input.setDate(QDate.currentDate().addYears(-25))
        self.client_lieu_naissance_input = QLineEdit()
        self.client_adresse_input = QLineEdit()
        self.client_numero_permis_input = QLineEdit()
        self.client_date_permis_input = QDateEdit()
        self.client_date_permis_input.setCalendarPopup(True)
        self.client_date_permis_input.setDate(QDate.currentDate().addYears(-2))
        self.client_date_expiration_permis_input = QDateEdit()
        self.client_date_expiration_permis_input.setCalendarPopup(True)
        self.client_date_expiration_permis_input.setDate(QDate.currentDate().addYears(5))
        self.client_telephone_input = QLineEdit()


# === SCANS PERMIS ===
        self.permis_recto_input = QLineEdit()
        recto_browse = QPushButton("Parcourir Recto")
        recto_browse.setStyleSheet("background:#3b82f6; color:white; padding:8px; border-radius:8px;")
        recto_browse.clicked.connect(lambda: self.permis_recto_input.setText(
            QFileDialog.getOpenFileName(self, "Recto du Permis", "", "Images (*.png *.jpg *.jpeg)")[0]))

        self.permis_verso_input = QLineEdit()
        verso_browse = QPushButton("Parcourir Verso")
        verso_browse.setStyleSheet("background:#8b5cf6; color:white; padding:8px; border-radius:8px;")
        verso_browse.clicked.connect(lambda: self.permis_verso_input.setText(
            QFileDialog.getOpenFileName(self, "Verso du Permis", "", "Images (*.png *.jpg *.jpeg)")[0]))

        # Liste des champs (ajout du nouveau)
        fields = [
                ("Nom", self.client_nom_input),
                ("Prénom", self.client_prenom_input),
                ("Genre", self.client_genre_combo),
                ("Date Naissance", self.client_date_naissance_input),
                ("Lieu Naissance", self.client_lieu_naissance_input),
                ("Adresse", self.client_adresse_input),
                ("N° Permis", self.client_numero_permis_input),
                ("Date Permis", self.client_date_permis_input),
                ("Date Expiration Permis", self.client_date_expiration_permis_input),
                ("Téléphone", self.client_telephone_input),
            ]

        for i, (label_text, widget) in enumerate(fields):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight:600; color:#374151;")
            form_layout.addWidget(lbl, i//2, (i%2)*2)
            widget.setStyleSheet("padding:10px; border:1px solid #d1d5db; border-radius:8px;")
            form_layout.addWidget(widget, i//2, (i%2)*2 + 1)

        # Scans Recto/Verso
        form_layout.addWidget(QLabel("Permis Recto :"), len(fields)//2, 0)
        recto_row = QHBoxLayout()
        recto_row.addWidget(self.permis_recto_input)
        recto_row.addWidget(recto_browse)
        form_layout.addLayout(recto_row, len(fields)//2, 1, 1, 3)

        form_layout.addWidget(QLabel("Permis Verso :"), len(fields)//2 + 1, 0)
        verso_row = QHBoxLayout()
        verso_row.addWidget(self.permis_verso_input)
        verso_row.addWidget(verso_browse)
        form_layout.addLayout(verso_row, len(fields)//2 + 1, 1, 1, 3)

        # Bouton enregistrer
        save_btn = QPushButton("Enregistrer le Client")
        save_btn.setStyleSheet("background:#059669; color:white; padding:14px; border-radius:12px; font-weight:bold; font-size:15px;")
        save_btn.clicked.connect(self.add_client)
        self.client_add_btn = save_btn
        form_layout.addWidget(save_btn, len(fields)//2 + 2, 0, 1, 4, alignment=Qt.AlignCenter)
        
        self.client_form.setLayout(QVBoxLayout())
        self.client_form.layout().addWidget(form_card)
        layout.addWidget(self.client_form)

        # Finalisation
        scroll.setWidget(page)
        if self.content_stack.count() > 2:
            old = self.content_stack.widget(2)
            self.content_stack.removeWidget(old)
            old.deleteLater()
        self.content_stack.insertWidget(2, scroll)
        self.load_clients()

    # 1. load_clients – on récupère la colonne notes et on colore la ligne si besoin
    def load_clients(self, search_text=""):
        query = "SELECT id, nom, prenom, genre, date_naissance, lieu_naissance, adresse, numero_permis, date_permis, telephone, notes FROM clients"
        params = ()

        if search_text:
            s_text = search_text.lower().strip()
            query += " WHERE lower(nom) LIKE ? OR lower(prenom) LIKE ?"
            params = (f"%{s_text}%", f"%{s_text}%")

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        self.client_table.setRowCount(len(rows))

        for row_idx, (cid, nom, prenom, genre, date_naissance, lieu_naissance,
                    adresse, numero_permis, date_permis, telephone, notes) in enumerate(rows):

            self.client_table.setItem(row_idx, 0, QTableWidgetItem(nom))
            self.client_table.setItem(row_idx, 1, QTableWidgetItem(prenom))

            # Genre avec couleur
            genre_item = QTableWidgetItem(genre)
            color = {"Homme": "#1d4ed8", "Femme": "#d946ef"}.get(genre, "#6b7280")
            genre_item.setForeground(QColor(color))
            genre_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.client_table.setItem(row_idx, 2, genre_item)

            self.client_table.setItem(row_idx, 3, QTableWidgetItem(date_naissance or ""))
            self.client_table.setItem(row_idx, 4, QTableWidgetItem(lieu_naissance or ""))
            self.client_table.setItem(row_idx, 5, QTableWidgetItem(adresse or ""))
            self.client_table.setItem(row_idx, 6, QTableWidgetItem(numero_permis or ""))
            self.client_table.setItem(row_idx, 7, QTableWidgetItem(date_permis or ""))
            self.client_table.setItem(row_idx, 8, QTableWidgetItem(telephone or ""))

            # === COLORATION DE LA LIGNE SI NOTES PRESENTES ===
            if notes and notes.strip():
                for col in range(self.client_table.columnCount() - 1):  # -1 pour ne pas colorer la colonne Actions
                    item = self.client_table.item(row_idx, col)
                    if item:
                        item.setBackground(QColor("#e66962"))   # jaune très clair (Tailwind amber-50)

            # === ACTIONS ===
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(8, 4, 8, 4)
            actions_layout.setSpacing(8)

            details_btn = QPushButton("Détails")
            details_btn.setStyleSheet("background:#3b82f6; color:white;")
            details_btn.clicked.connect(lambda _, c=cid: self.show_client_details(c))

            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet("background:#06b6d4; color:white;")
            edit_btn.clicked.connect(lambda _, c=cid: self.edit_client(c))

            delete_btn = QPushButton("Supp")
            delete_btn.setStyleSheet("background:#dc2626; color:white;")
            delete_btn.clicked.connect(lambda _, c=cid: self.delete_client(c))

            actions_layout.addWidget(details_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)

            self.client_table.setCellWidget(row_idx, 9, actions)

        # Mise à jour compteurs
        self.cursor.execute("SELECT COUNT(*) FROM clients WHERE genre='Homme'")
        self.nb_homme_label.setText(str(self.cursor.fetchone()[0]))
        self.cursor.execute("SELECT COUNT(*) FROM clients WHERE genre='Femme'")
        self.nb_femme_label.setText(str(self.cursor.fetchone()[0]))

    def delete_selected_clients(self):
        selected_ids = []
        for i in range(self.client_table.rowCount()):
            check_widget = self.client_table.cellWidget(i, 0)
            check = check_widget.layout().itemAt(0).widget()
            if check.isChecked():
                cid = int(self.client_table.item(i, 1).text())
                selected_ids.append(cid)
        if selected_ids:
            reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_selection"],
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for cid in selected_ids:
                    self.cursor.execute("DELETE FROM clients WHERE id = ?", (cid,))
                    self.cursor.execute("DELETE FROM locations WHERE client_id = ? OR second_client_id = ?", (cid, cid))
                    self.cursor.execute("DELETE FROM reservations WHERE client_id = ?", (cid,))
                    self.cursor.execute("DELETE FROM factures WHERE location_id IN (SELECT id FROM locations WHERE client_id = ? OR second_client_id = ?)", (cid, cid))
                self.conn.commit()
                self.load_clients()
                self.load_locations()
                self.load_reservations()
                self.load_factures()


    def show_client_details(self, client_id):
        self.cursor.execute("""
            SELECT nom, prenom, genre, date_naissance, lieu_naissance, adresse,
                numero_permis, date_permis, date_expiration_permis, telephone,
                permis_recto_path, permis_verso_path, notes
            FROM clients WHERE id = ?
        """, (client_id,))
        client = self.cursor.fetchone()
        if not client:
            QMessageBox.information(self, "Info", "Client non trouvé.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Détails Client - {client[0]} {client[1]}")
        dialog.resize(1400, 950)
        dialog.setModal(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)

        # === EN-TÊTE + NOTES SUR LA MÊME LIGNE ===
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # --- Colonne gauche : Informations Personnelles ---
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setSpacing(8)
        
        title_perso = QLabel("Informations Personnelles")
        title_perso.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e40af;")
        left_layout.addWidget(title_perso)

        grid_perso = QGridLayout()
        grid_perso.setVerticalSpacing(6)
        grid_perso.setHorizontalSpacing(12)

        labels = [
            "Nom", "Prénom", "Genre", "Date Naissance", "Lieu Naissance",
            "Adresse", "N° Permis", "Date Permis", "Date Expiration Permis", "Téléphone"
        ]

        for i, (label_text, value) in enumerate(zip(labels, client[:10])):
            row = i // 2
            col = (i % 2) * 2

            label = QLabel(f"<b>{label_text} :</b>")
            label.setStyleSheet("color: #374151; font-size: 12px;")
            grid_perso.addWidget(label, row, col)

            value_label = QLabel(str(value) if value else "-")
            value_label.setStyleSheet("color: #1f2937; font-size: 12px;")

            if label_text == "Date Expiration Permis" and value:
                try:
                    exp_date = QDate.fromString(str(value), "yyyy-MM-dd")
                    if exp_date < QDate.currentDate():
                        value_label.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
                        value_label.setText(f"{value} (EXPIRÉ !)")
                except:
                    pass

            grid_perso.addWidget(value_label, row, col + 1)

        left_layout.addLayout(grid_perso)
        top_row.addWidget(left_col, 3)

        # --- Colonne droite : Notes compactes ---
        right_col = QWidget()
        right_col.setFixedWidth(300)
        right_col.setStyleSheet("""
            background: #fef3c7; 
            border: 2px solid #fbbf24; 
            border-radius: 10px; 
            padding: 10px;
        """)
        right_layout = QVBoxLayout(right_col)
        right_layout.setSpacing(6)

        notes_title = QLabel("📌 Notes")
        notes_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #92400e;")
        right_layout.addWidget(notes_title)

        notes_edit = QTextEdit()
        notes_edit.setPlainText(client[12] or "Aucune note...")
        notes_edit.setFixedHeight(100)
        notes_edit.setStyleSheet("""
            QTextEdit { 
                border: 1px solid #fbbf24; 
                border-radius: 6px; 
                padding: 6px; 
                font-size: 11px; 
                background: white;
            }
        """)
        right_layout.addWidget(notes_edit)

        save_notes_btn = QPushButton("💾 Enregistrer")
        save_notes_btn.setStyleSheet("""
            background: #f59e0b; 
            color: white; 
            padding: 6px 14px; 
            border-radius: 6px; 
            font-weight: bold; 
            font-size: 11px;
        """)
        save_notes_btn.clicked.connect(lambda: self.save_client_notes(client_id, notes_edit.toPlainText()))
        right_layout.addWidget(save_notes_btn)

        top_row.addWidget(right_col, 1)
        layout.addLayout(top_row)

        # === SCANS DU PERMIS ===
        title_scans = QLabel("Scans du Permis de Conduire")
        title_scans.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e40af; margin-top: 8px;")
        layout.addWidget(title_scans)

        scans_row = QHBoxLayout()
        scans_row.setSpacing(12)

        for side, path_idx in [("Recto", 10), ("Verso", 11)]:
            box = QGroupBox(f"{side} du Permis")
            box.setFixedHeight(220)
            box.setStyleSheet(f"""
                QGroupBox {{ 
                    font-weight: bold; 
                    font-size: 12px;
                    border: 2px solid {'#3b82f6' if side == 'Recto' else '#8b5cf6'}; 
                    border-radius: 8px; 
                    padding: 6px; 
                }}
            """)
            img_layout = QVBoxLayout(box)
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("background: #f8fafc; border-radius: 6px;")
            img_label.setMinimumSize(self.scale(340), self.scale(180))

            if client[path_idx] and os.path.exists(client[path_idx]):
                pixmap = QPixmap(client[path_idx]).scaled(380, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(pixmap)
            else:
                img_label.setText(f"Aucun scan {side.lower()} disponible")
                img_label.setStyleSheet(img_label.styleSheet() + "color: #94a3b8; font-size: 13px;")

            img_layout.addWidget(img_label)
            scans_row.addWidget(box)

        layout.addLayout(scans_row)

        # === SYSTÈME D'ONGLETS ===
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #e5e7eb;  background: white; }}
            QTabBar::tab {{ background: #f3f4f6; color: #4b5563; padding: 8px 20px; font-weight: 600; font-size: 12px;
                            width:200px;  }}
            QTabBar::tab:selected {{ background: #1e40af; color: white; }}
        """)
        tabs.setMinimumHeight(450)
        layout.addWidget(tabs, stretch=3)

        # ========== TAB 1 : LOCATIONS CONDUCTEUR 1 (avec recherche) ==========
        loc1_tab = QWidget()
        loc1_layout = QVBoxLayout(loc1_tab)
        loc1_layout.setContentsMargins(8, 8, 8, 8)
        loc1_layout.setSpacing(8)

        loc1_title = QLabel("Locations en tant que Conducteur Principal")
        loc1_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827;")
        loc1_layout.addWidget(loc1_title)

        # === BARRE DE RECHERCHE ===
        loc1_search = QLineEdit()
        loc1_search.setPlaceholderText("Rechercher par véhicule, date ou montant...")
        loc1_search.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 12px;
                background: #f9fafb;
            }
            QLineEdit:focus { border: 2px solid #3b82f6; }
        """)
        loc1_search.textChanged.connect(lambda text: self.filter_client_locations1(client_id, text))
        loc1_layout.addWidget(loc1_search)

        self.loc1_table = QTableWidget()
        self.loc1_table.setColumnCount(6)
        self.loc1_table.setHorizontalHeaderLabels(["ID", "Véhicule", "Date", "Jours", "Coût", "Actions"])
        self.loc1_table.setStyleSheet("""
            QTableWidget { border: 1px solid #e5e7eb; border-radius: 6px; gridline-color: #f3f4f6; font-size: 12px; }
            QHeaderView::section { background: #1e40af; color: white; padding: 6px; font-weight: bold; font-size: 12px; }
        """)
        self.loc1_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loc1_table.setColumnWidth(0, 45)
        self.loc1_table.setColumnWidth(2, 85)
        self.loc1_table.setColumnWidth(3, 50)
        self.loc1_table.setColumnWidth(4, 85)
        self.loc1_table.setColumnWidth(5, 210)
        self.loc1_table.setMinimumHeight(400)
        
        loc1_layout.addWidget(self.loc1_table, stretch=1)
        tabs.addTab(loc1_tab, "Conducteur Principal")

        # ========== TAB 2 : LOCATIONS CONDUCTEUR 2 (avec recherche) ==========
        loc2_tab = QWidget()
        loc2_layout = QVBoxLayout(loc2_tab)
        loc2_layout.setContentsMargins(8, 8, 8, 8)
        loc2_layout.setSpacing(8)

        loc2_title = QLabel("Locations en tant que Conducteur Secondaire")
        loc2_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827;")
        loc2_layout.addWidget(loc2_title)

        # === BARRE DE RECHERCHE ===
        loc2_search = QLineEdit()
        loc2_search.setPlaceholderText("Rechercher par véhicule, date ou montant...")
        loc2_search.setStyleSheet(loc1_search.styleSheet())
        loc2_search.textChanged.connect(lambda text: self.filter_client_locations2(client_id, text))
        loc2_layout.addWidget(loc2_search)

        self.loc2_table = QTableWidget()
        self.loc2_table.setColumnCount(6)
        self.loc2_table.setHorizontalHeaderLabels(["ID", "Véhicule", "Date", "Jours", "Coût", "Actions"])
        self.loc2_table.setStyleSheet(self.loc1_table.styleSheet())
        self.loc2_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loc2_table.setColumnWidth(0, 45)
        self.loc2_table.setColumnWidth(2, 85)
        self.loc2_table.setColumnWidth(3, 50)
        self.loc2_table.setColumnWidth(4, 85)
        self.loc2_table.setColumnWidth(5, 210)
        self.loc2_table.setMinimumHeight(400)
        
        loc2_layout.addWidget(self.loc2_table, stretch=1)
        tabs.addTab(loc2_tab, "Conducteur Secondaire")

        # ========== TAB 3 : CONTRATS SIGNÉS (avec recherche) ==========
        signed_tab = QWidget()
        signed_layout = QVBoxLayout(signed_tab)
        signed_layout.setContentsMargins(8, 8, 8, 8)
        signed_layout.setSpacing(8)

        signed_title = QLabel("Contrats Signés (Versions PDF)")
        signed_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827;")
        signed_layout.addWidget(signed_title)

        # === BARRE DE RECHERCHE ===
        signed_search = QLineEdit()
        signed_search.setPlaceholderText("Rechercher par nom de fichier...")
        signed_search.setStyleSheet(loc1_search.styleSheet())
        signed_search.textChanged.connect(lambda text: self.filter_client_signed_contracts(client_id, text))
        signed_layout.addWidget(signed_search)

        add_signed_btn = QPushButton("Ajouter un contrat signé (PDF)")
        add_signed_btn.setStyleSheet("background: #059669; color: white; padding: 8px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        add_signed_btn.clicked.connect(lambda: self.add_signed_contract(client_id))
        signed_layout.addWidget(add_signed_btn, alignment=Qt.AlignRight)

        self.signed_table = QTableWidget()
        self.signed_table.setColumnCount(4)
        self.signed_table.setHorizontalHeaderLabels(["ID", "Nom du fichier", "Date d'ajout", "Actions"])
        self.signed_table.setStyleSheet(self.loc1_table.styleSheet())
        self.signed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.signed_table.setColumnWidth(0, 45)
        self.signed_table.setColumnWidth(2, 95)
        self.signed_table.setColumnWidth(3, 210)
        self.signed_table.setMinimumHeight(400)
        
        signed_layout.addWidget(self.signed_table, stretch=1)
        tabs.addTab(signed_tab, "Contrats Signés")

        # === CHARGER LES DONNÉES ===
        self.load_client_locations1(client_id)
        self.load_client_locations2(client_id)
        self.load_client_signed_contracts(client_id)

        # === BOUTON FERMER ===
        btn_close = QPushButton("Fermer")
        btn_close.setStyleSheet("""
            QPushButton { 
                background: #dc2626; 
                color: white; 
                padding: 10px 40px; 
                border-radius: 8px; 
                font-size: 13px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        dialog.exec_()


    # ========== NOUVELLES FONCTIONS DE FILTRAGE ==========

    def filter_client_locations1(self, client_id, search_text):
        """Filtre les locations du conducteur principal"""
        search = search_text.lower().strip()
        
        self.cursor.execute("""
            SELECT l.id, v.modele || ' (' || v.numero_matricule || ')', 
                substr(l.date_heure_location, 1, 10), l.jours, l.cout_total
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            WHERE l.client_id = ?
            AND (
                lower(v.modele) LIKE ? OR 
                lower(v.numero_matricule) LIKE ? OR 
                substr(l.date_heure_location, 1, 10) LIKE ? OR
                CAST(l.cout_total AS TEXT) LIKE ?
            )
            ORDER BY l.date_heure_location DESC
        """, (client_id, f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
        
        rows = self.cursor.fetchall()
        self.loc1_table.setRowCount(len(rows))
        
        for i, (loc_id, vehicule, date_loc, jours, cout) in enumerate(rows):
            self.loc1_table.setItem(i, 0, QTableWidgetItem(str(loc_id)))
            self.loc1_table.setItem(i, 1, QTableWidgetItem(vehicule))
            self.loc1_table.setItem(i, 2, QTableWidgetItem(date_loc))
            self.loc1_table.setItem(i, 3, QTableWidgetItem(str(jours)))
            
            cout_item = QTableWidgetItem(f"{cout:,.2f} DA")
            cout_item.setForeground(QColor("#16a34a"))
            cout_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.loc1_table.setItem(i, 4, cout_item)
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, lid=loc_id: self.view_facture(self.get_facture_id_by_location(lid)))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, lid=loc_id: self.print_facture(self.get_facture_id_by_location(lid)))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            self.loc1_table.setCellWidget(i, 5, actions)


    def filter_client_locations2(self, client_id, search_text):
        """Filtre les locations du conducteur secondaire"""
        search = search_text.lower().strip()
        
        self.cursor.execute("""
            SELECT l.id, v.modele || ' (' || v.numero_matricule || ')', 
                substr(l.date_heure_location, 1, 10), l.jours, l.cout_total
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            WHERE l.second_client_id = ?
            AND (
                lower(v.modele) LIKE ? OR 
                lower(v.numero_matricule) LIKE ? OR 
                substr(l.date_heure_location, 1, 10) LIKE ? OR
                CAST(l.cout_total AS TEXT) LIKE ?
            )
            ORDER BY l.date_heure_location DESC
        """, (client_id, f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
        
        rows = self.cursor.fetchall()
        self.loc2_table.setRowCount(len(rows))
        
        for i, (loc_id, vehicule, date_loc, jours, cout) in enumerate(rows):
            self.loc2_table.setItem(i, 0, QTableWidgetItem(str(loc_id)))
            self.loc2_table.setItem(i, 1, QTableWidgetItem(vehicule))
            self.loc2_table.setItem(i, 2, QTableWidgetItem(date_loc))
            self.loc2_table.setItem(i, 3, QTableWidgetItem(str(jours)))
            
            cout_item = QTableWidgetItem(f"{cout:,.2f} DA")
            cout_item.setForeground(QColor("#16a34a"))
            cout_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.loc2_table.setItem(i, 4, cout_item)
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, lid=loc_id: self.view_facture(self.get_facture_id_by_location(lid)))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, lid=loc_id: self.print_facture(self.get_facture_id_by_location(lid)))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            self.loc2_table.setCellWidget(i, 5, actions)


    def filter_client_signed_contracts(self, client_id, search_text):
        """Filtre les contrats signés"""
        search = search_text.lower().strip()
        
        self.cursor.execute("""
            SELECT id, file_name, upload_date, file_path
            FROM client_signed_contracts
            WHERE client_id = ?
            AND lower(file_name) LIKE ?
            ORDER BY upload_date DESC
        """, (client_id, f"%{search}%"))
        
        rows = self.cursor.fetchall()
        self.signed_table.setRowCount(len(rows))
        
        for i, (contract_id, file_name, upload_date, file_path) in enumerate(rows):
            self.signed_table.setItem(i, 0, QTableWidgetItem(str(contract_id)))
            self.signed_table.setItem(i, 1, QTableWidgetItem(file_name))
            self.signed_table.setItem(i, 2, QTableWidgetItem(upload_date[:10]))
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, fp=file_path: self.view_signed_pdf(fp))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, fp=file_path: self.print_signed_pdf(fp))
            
            delete_btn = QPushButton("Suppr")
            delete_btn.setStyleSheet("background:#dc2626; color:white; padding:4px 8px;")
            delete_btn.clicked.connect(lambda _, cid=contract_id, clt=client_id: self.delete_signed_contract(cid, clt))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            actions_layout.addWidget(delete_btn)
            self.signed_table.setCellWidget(i, 3, actions)


    # ========== MISE À JOUR DES FONCTIONS LOAD (utilisent maintenant le filtrage) ==========

    def load_client_locations1(self, client_id):
        """Charge toutes les locations du conducteur principal (sans filtre)"""
        self.filter_client_locations1(client_id, "")


    def load_client_locations2(self, client_id):
        """Charge toutes les locations du conducteur secondaire (sans filtre)"""
        self.filter_client_locations2(client_id, "")


    def load_client_signed_contracts(self, client_id):
        """Charge tous les contrats signés (sans filtre)"""
        # Créer la table si elle n'existe pas
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_signed_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)
        
        self.filter_client_signed_contracts(client_id, "")


    # ========== FONCTIONS DE CHARGEMENT DES TABLEAUX ==========

    def load_client_locations1(self, client_id):
        """Charge les locations où le client est conducteur principal"""
        self.cursor.execute("""
            SELECT l.id, v.modele || ' (' || v.numero_matricule || ')', 
                substr(l.date_heure_location, 1, 10), l.jours, l.cout_total
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            WHERE l.client_id = ?
            ORDER BY l.date_heure_location DESC
        """, (client_id,))
        
        rows = self.cursor.fetchall()
        self.loc1_table.setRowCount(len(rows))
        
        for i, (loc_id, vehicule, date_loc, jours, cout) in enumerate(rows):
            self.loc1_table.setItem(i, 0, QTableWidgetItem(str(loc_id)))
            self.loc1_table.setItem(i, 1, QTableWidgetItem(vehicule))
            self.loc1_table.setItem(i, 2, QTableWidgetItem(date_loc))
            self.loc1_table.setItem(i, 3, QTableWidgetItem(str(jours)))
            
            cout_item = QTableWidgetItem(f"{cout:,.2f} DA")
            cout_item.setForeground(QColor("#16a34a"))
            cout_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.loc1_table.setItem(i, 4, cout_item)
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, lid=loc_id: self.view_facture(self.get_facture_id_by_location(lid)))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, lid=loc_id: self.print_facture(self.get_facture_id_by_location(lid)))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            self.loc1_table.setCellWidget(i, 5, actions)


    def load_client_locations2(self, client_id):
        """Charge les locations où le client est conducteur secondaire"""
        self.cursor.execute("""
            SELECT l.id, v.modele || ' (' || v.numero_matricule || ')', 
                substr(l.date_heure_location, 1, 10), l.jours, l.cout_total
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            WHERE l.second_client_id = ?
            ORDER BY l.date_heure_location DESC
        """, (client_id,))
        
        rows = self.cursor.fetchall()
        self.loc2_table.setRowCount(len(rows))
        
        for i, (loc_id, vehicule, date_loc, jours, cout) in enumerate(rows):
            self.loc2_table.setItem(i, 0, QTableWidgetItem(str(loc_id)))
            self.loc2_table.setItem(i, 1, QTableWidgetItem(vehicule))
            self.loc2_table.setItem(i, 2, QTableWidgetItem(date_loc))
            self.loc2_table.setItem(i, 3, QTableWidgetItem(str(jours)))
            
            cout_item = QTableWidgetItem(f"{cout:,.2f} DA")
            cout_item.setForeground(QColor("#16a34a"))
            cout_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.loc2_table.setItem(i, 4, cout_item)
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, lid=loc_id: self.view_facture(self.get_facture_id_by_location(lid)))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, lid=loc_id: self.print_facture(self.get_facture_id_by_location(lid)))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            self.loc2_table.setCellWidget(i, 5, actions)


    def get_facture_id_by_location(self, location_id):
        """Récupère l'ID de la facture pour une location donnée"""
        self.cursor.execute("SELECT id FROM factures WHERE location_id = ?", (location_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None


    def load_client_signed_contracts(self, client_id):
        """Charge les contrats signés (PDF) du client"""
        self.cursor.execute("""
            SELECT id, file_name, upload_date, file_path
            FROM client_signed_contracts
            WHERE client_id = ?
            ORDER BY upload_date DESC
        """, (client_id,))
        
        rows = self.cursor.fetchall()
        self.signed_table.setRowCount(len(rows))
        
        for i, (contract_id, file_name, upload_date, file_path) in enumerate(rows):
            self.signed_table.setItem(i, 0, QTableWidgetItem(str(contract_id)))
            self.signed_table.setItem(i, 1, QTableWidgetItem(file_name))
            self.signed_table.setItem(i, 2, QTableWidgetItem(upload_date[:10]))
            
            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            voir_btn = QPushButton("Voir")
            voir_btn.setStyleSheet("background:#3b82f6; color:white; padding:4px 8px;")
            voir_btn.clicked.connect(lambda _, fp=file_path: self.view_signed_pdf(fp))
            
            imprimer_btn = QPushButton("Imprimer")
            imprimer_btn.setStyleSheet("background:#16a34a; color:white; padding:4px 8px;")
            imprimer_btn.clicked.connect(lambda _, fp=file_path: self.print_signed_pdf(fp))
            
            delete_btn = QPushButton("Suppr")
            delete_btn.setStyleSheet("background:#dc2626; color:white; padding:4px 8px;")
            delete_btn.clicked.connect(lambda _, cid=contract_id, clt=client_id: self.delete_signed_contract(cid, clt))
            
            actions_layout.addWidget(voir_btn)
            actions_layout.addWidget(imprimer_btn)
            actions_layout.addWidget(delete_btn)
            self.signed_table.setCellWidget(i, 3, actions)


    def add_signed_contract(self, client_id):
        """Ajoute un PDF signé pour un client"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner le contrat signé (PDF)", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        
        # NEW: Save file to uploads folder
        dest_path = self.save_upload(file_path, "contracts")
        file_name = os.path.basename(file_path)
        
        try:
            self.cursor.execute("""
                INSERT INTO client_signed_contracts (client_id, file_name, file_path, upload_date)
                VALUES (?, ?, ?, ?)
            """, (client_id, file_name, dest_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            self.conn.commit()
            self.load_client_signed_contracts(client_id)
            QMessageBox.information(self, "Succès", "Contrat signé ajouté avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le contrat : {str(e)}")


    def view_signed_pdf(self, file_path):
        """Ouvre le PDF signé dans le visualiseur système"""
        if os.path.exists(file_path):
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    os.system(f"open '{file_path}'")
                else:
                    os.system(f"xdg-open '{file_path}'")
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible d'ouvrir le fichier : {str(e)}")
        else:
            QMessageBox.warning(self, "Erreur", "Le fichier n'existe plus.")


    def print_signed_pdf(self, file_path):
        """Imprime le PDF signé"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Erreur", "Le fichier n'existe plus.")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(file_path, "print")
            else:
                QMessageBox.information(self, "Info", f"Veuillez imprimer manuellement le fichier :\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'imprimer : {str(e)}")


    def delete_signed_contract(self, contract_id, client_id):
        """Supprime un contrat signé"""
        reply = QMessageBox.question(self, "Confirmer", 
            "Voulez-vous vraiment supprimer ce contrat signé ?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("SELECT file_path FROM client_signed_contracts WHERE id = ?", (contract_id,))
            result = self.cursor.fetchone()
            
            if result:
                file_path = result[0]
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
            self.cursor.execute("DELETE FROM client_signed_contracts WHERE id = ?", (contract_id,))
            self.conn.commit()
            self.load_client_signed_contracts(client_id)
            QMessageBox.information(self, "Succès", "Contrat signé supprimé.")


    
    def save_client_notes(self, client_id, notes_text):
        notes = notes_text.strip()
        self.cursor.execute("UPDATE clients SET notes = ? WHERE id = ?", (notes, client_id))
        self.conn.commit()
        self.load_clients()                     # pour rafraîchir la couleur de la ligne
        QMessageBox.information(self, "Succès", "Notes enregistrées avec succès.")

    def add_client(self):
        try:
            nom = self.client_nom_input.text().strip()
            prenom = self.client_prenom_input.text().strip()
            genre = self.client_genre_combo.currentText()
            date_naissance = self.client_date_naissance_input.date().toString("yyyy-MM-dd")
            lieu_naissance = self.client_lieu_naissance_input.text().strip()
            adresse = self.client_adresse_input.text().strip()
            numero_permis = self.client_numero_permis_input.text().strip()
            date_permis = self.client_date_permis_input.date().toString("yyyy-MM-dd")
            date_expiration_permis = self.client_date_expiration_permis_input.date().toString("yyyy-MM-dd")
            telephone = self.client_telephone_input.text().strip()

            # Scans permis
            recto_path = self.save_upload(self.permis_recto_input.text().strip(), "licenses")
            verso_path = self.save_upload(self.permis_verso_input.text().strip(), "licenses")

            # Correct — NE PAS ajouter de champ notes ici
            self.cursor.execute('''
                INSERT INTO clients (
                    nom, prenom, genre, date_naissance, lieu_naissance, adresse,
                    numero_permis, date_permis, date_expiration_permis, telephone,
                    permis_recto_path, permis_verso_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nom, prenom, genre, date_naissance, lieu_naissance, adresse,
                numero_permis, date_permis, date_expiration_permis, telephone,
                recto_path, verso_path))

            self.conn.commit()
            self.clear_client_form()
            self.load_clients()
            self.update_dashboard_stats()
            self.refresh_client_completers()

            QMessageBox.information(self, "Succès", "Client ajouté avec succès.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout : {str(e)}")

    def refresh_client_completers(self):
        """Met à jour les completers des champs client (dans location, réservation, etc.)"""
        # Recharge les deux completers de la page location
        if hasattr(self, 'location_client_completer'):
            self.load_clients_completer(self.location_client_completer)
        if hasattr(self, 'location_client2_completer'):
            self.load_clients_completer(self.location_client2_completer)
        
        # Recharge le completer de la page réservation
        if hasattr(self, 'res_client_completer'):
            self.load_clients_completer(self.res_client_completer)


    def refresh_voiture_combos(self):
        """Met à jour tous les combobox de voitures (location, réservation, etc.)"""
        if hasattr(self, 'location_voiture_combo'):
            current_id = self.location_voiture_combo.currentData()  # on garde la voiture sélectionnée si possible
            self.load_voitures_combo(self.location_voiture_combo)
            # Réessayer de resélectionner la même voiture après refresh
            if current_id:
                index = self.location_voiture_combo.findData(current_id)
                if index != -1:
                    self.location_voiture_combo.setCurrentIndex(index)
        
        # Si tu as d'autres combos ailleurs (réservation, etc.), ajoute ici aussi
        # Exemple :
        # if hasattr(self, 'reservation_voiture_combo'):
        #     self.load_voitures_combo(self.reservation_voiture_combo)

    def edit_client(self, client_id):
        self.cursor.execute("""
            SELECT nom, prenom, genre, date_naissance, lieu_naissance, adresse,
                numero_permis, date_permis, date_expiration_permis, telephone,
                permis_recto_path, permis_verso_path, notes
            FROM clients WHERE id = ?
        """, (client_id,))
        data = self.cursor.fetchone()
        if data:
            (nom, prenom, genre, date_n, lieu_n, adresse, num_p, date_p,
            date_exp, tel, recto, verso, notes) = data

            # Fill form fields
            self.client_nom_input.setText(nom)
            self.client_prenom_input.setText(prenom)
            self.client_genre_combo.setCurrentText(genre)
            self.client_date_naissance_input.setDate(QDate.fromString(date_n, "yyyy-MM-dd"))
            self.client_lieu_naissance_input.setText(lieu_n or "")
            self.client_adresse_input.setText(adresse or "")
            self.client_numero_permis_input.setText(num_p or "")
            self.client_date_permis_input.setDate(QDate.fromString(date_p, "yyyy-MM-dd"))
            self.client_date_expiration_permis_input.setDate(QDate.fromString(date_exp, "yyyy-MM-dd"))
            self.client_telephone_input.setText(tel or "")
            self.permis_recto_input.setText(recto or "")
            self.permis_verso_input.setText(verso or "")

            # Show form and switch to edit mode
            self.client_form.setVisible(True)
            self.client_add_btn.setText("Mettre à jour le client")
            
            # ← DISCONNECT AND RECONNECT
            try:
                self.client_add_btn.clicked.disconnect()
            except TypeError:
                pass
            self.client_add_btn.clicked.connect(lambda: self.update_client(client_id))


    def update_client(self, client_id):
        nom = self.client_nom_input.text().strip()
        prenom = self.client_prenom_input.text().strip()
        genre = self.client_genre_combo.currentText()
        date_n = self.client_date_naissance_input.date().toString("yyyy-MM-dd")
        lieu_n = self.client_lieu_naissance_input.text().strip()
        adresse = self.client_adresse_input.text().strip()
        num_p = self.client_numero_permis_input.text().strip()
        date_p = self.client_date_permis_input.date().toString("yyyy-MM-dd")
        date_exp = self.client_date_expiration_permis_input.date().toString("yyyy-MM-dd")
        tel = self.client_telephone_input.text().strip()
        recto = self.save_upload(self.permis_recto_input.text().strip(), "licenses")
        verso = self.save_upload(self.permis_verso_input.text().strip(), "licenses")

        self.cursor.execute("""
            UPDATE clients SET
                nom=?, prenom=?, genre=?, date_naissance=?, lieu_naissance=?, adresse=?,
                numero_permis=?, date_permis=?, date_expiration_permis=?, telephone=?,
                permis_recto_path=?, permis_verso_path=?
            WHERE id=?
        """, (nom, prenom, genre, date_n, lieu_n, adresse,
            num_p, date_p, date_exp, tel,
            recto or None, verso or None, client_id))

        self.conn.commit()
        self.load_clients()
        self.clear_client_form()
        self.client_form.setVisible(False)
        
        # ← RESET TO ADD MODE
        self.client_add_btn.setText("Enregistrer le Client")
        try:
            self.client_add_btn.clicked.disconnect()
        except TypeError:
            pass
        self.client_add_btn.clicked.connect(self.add_client)
        
        self.refresh_client_completers()  # Update completers in location/reservation
        QMessageBox.information(self, "Succès", "Client mis à jour.")


    def delete_client(self, client_id):
        reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_client"],
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            self.cursor.execute("DELETE FROM locations WHERE client_id = ? OR second_client_id = ?", (client_id, client_id))
            self.cursor.execute("DELETE FROM reservations WHERE client_id = ?", (client_id,))
            self.cursor.execute("DELETE FROM factures WHERE location_id IN (SELECT id FROM locations WHERE client_id = ? OR second_client_id = ?)", (client_id, client_id))
            self.conn.commit()
            self.load_clients()
            self.load_locations()
            self.load_reservations()
            self.load_factures()

    def search_clients(self):
        self.load_clients(self.client_search_input.text())

    def clear_client_form(self):
        self.client_nom_input.clear()
        self.client_prenom_input.clear()
        self.client_genre_combo.setCurrentIndex(0)
        self.client_date_naissance_input.setDate(QDate.currentDate().addYears(-25))
        self.client_lieu_naissance_input.clear()
        self.client_adresse_input.clear()
        self.client_numero_permis_input.clear()
        self.client_date_permis_input.setDate(QDate.currentDate().addYears(-2))
        self.client_date_expiration_permis_input.setDate(QDate.currentDate().addYears(5))
        self.client_telephone_input.clear()
        self.permis_recto_input.clear()
        self.permis_verso_input.clear()

    def setup_location_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(20)

        # ================== TITRE ==================
        title = QLabel("Nouvelle Location")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#111827; margin-bottom:10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== SECTION HAUT – FORMULAIRE + ACCESSOIRES (40% HEIGHT) ==================
        top_section = QWidget()
        top_section.setStyleSheet("""
            background:white; 
            border-radius:16px; 
            padding:20px; 
            box-shadow: 0 6px 16px rgba(0,0,0,0.07);
        """)
        top_section.setMaximumHeight(int(self.height() * 0.40))

        top_layout = QHBoxLayout(top_section)
        top_layout.setSpacing(20)

        # --- FORMULAIRE GAUCHE (COMPACT) ---
        form_widget = QWidget()
        form_widget.setStyleSheet("background:transparent;")
        form_layout = QGridLayout(form_widget)
        form_layout.setColumnStretch(1, 1)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(12)

        labels = [
            "Voiture :", "Client principal :", "Client secondaire (opt.) :",
            "Date location :", "Heure location :",
            "Jours :", "Promo (DZ) :", "Carburant départ :",
            "Kilométrage départ :"
        ]

        # ← FIX CRITIQUE : CRÉER LES WIDGETS AVANT DE LES UTILISER
        self.location_voiture_combo = QComboBox()
        self.location_client_input = QLineEdit()
        self.location_client2_input = QLineEdit()

            # === DATE (LECTURE SEULE + BOUTON POPUP) ===
        self.location_date_input = QDateEdit()
        self.location_date_input.setDate(QDate.currentDate())
        self.location_date_input.setVisible(False)  # ← MASQUÉ COMPLÈTEMENT

        # Bouton pour ouvrir le calendrier
        date_btn = QPushButton("📅")
        date_btn.setFixedSize(self.scale(25), self.scale(25))
        date_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 14px;
                margin-bottom:2px;
            }
        """)
        date_btn.clicked.connect(self.open_date_picker_location)

        self.location_date_label = QLabel(QDate.currentDate().toString("dd/MM/yyyy"))
        self.location_date_label.setStyleSheet("""
            font-weight:600;
            font-size:15px; 
            color:#1e40af; 
            background:#f0f9ff;
            border:2px solid #3b82f6;
            border-radius:12px;
            padding:16px 24px;
        """)
        self.location_date_label.setAlignment(Qt.AlignCenter)

        date_widget = QWidget()
        date_widget.setStyleSheet("background:transparent;")
        date_h = QHBoxLayout(date_widget)
        date_h.setContentsMargins(0, 0, 0, 0)
        date_h.setSpacing(12)
        date_h.addWidget(self.location_date_label)  # ← LABEL EN PREMIER
        date_h.addWidget(date_btn)                  # ← BOUTON À DROITE

        # === HEURE (COMPLÈTEMENT MASQUÉ - UNIQUEMENT LABEL + BOUTON) ===
        self.location_time_input = QTimeEdit()
        self.location_time_input.setTime(QTime.currentTime())
        self.location_time_input.setVisible(False)  # ← MASQUÉ COMPLÈTEMENT

        # Bouton pour ouvrir l'horloge
        time_btn = QPushButton("🕐")
        time_btn.setFixedSize(self.scale(25), self.scale(25))
        time_btn.setStyleSheet(date_btn.styleSheet())
        time_btn.clicked.connect(self.open_time_picker_location)

        self.location_time_label = QLabel(QTime.currentTime().toString("HH:mm"))
        self.location_time_label.setStyleSheet("""
            font-weight:600;
            font-size:15px; 
            color:#059669; 
            background:#f0fdf4;
            border:2px solid #059669;
            border-radius:12px;
            padding:16px 24px;
        """)
        self.location_time_label.setAlignment(Qt.AlignCenter)

        time_widget = QWidget()
        time_widget.setStyleSheet("background:transparent;")
        time_h = QHBoxLayout(time_widget)
        time_h.setContentsMargins(0, 0, 0, 0)
        time_h.setSpacing(12)
        time_h.addWidget(self.location_time_label)  # ← LABEL EN PREMIER
        time_h.addWidget(time_btn)

        # Reste des widgets
        self.location_jours_input = QLineEdit()
        self.location_jours_input.setPlaceholderText("ex: 7")
        self.location_promotion_input = QLineEdit()
        self.location_promotion_input.setPlaceholderText("ex: 100")
        self.location_km_depart = QLineEdit()
        self.location_km_depart.setPlaceholderText("ex: 12345")
        self.location_fuel_combo = QComboBox()

        widgets = [
            self.location_voiture_combo,
            self.location_client_input,
            self.location_client2_input,
            date_widget,
            time_widget,
            self.location_jours_input,
            self.location_promotion_input,
            self.location_fuel_combo,
            self.location_km_depart
        ]

        # Initialisation
        self.load_voitures_combo(self.location_voiture_combo)
        self.location_fuel_combo.addItems(["8/8", "7/8", "6/8", "5/8", "4/8","3/8", "2/8", "1/8", "4/4","3,5/4","3/4","2,5/4","2/4","1,5/4","1/4"])
        
        self.location_client_completer = QCompleter()
        self.location_client_input.setCompleter(self.location_client_completer)
        self.location_client2_completer = QCompleter()
        self.location_client2_input.setCompleter(self.location_client2_completer)
        self.load_clients_completer(self.location_client_completer)
        self.load_clients_completer(self.location_client2_completer)
            # STYLE DES CHAMPS (COMPACT)
    # STYLE DES CHAMPS
        input_style = """
            QLineEdit, QComboBox {
                border:1px solid #d1d5db;
                border-radius:6px;
                padding: 20px;
                font-size:18px;
                background:#ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border:2px solid #3b82f6;
            }
        """
        
        for w in widgets:
            if w not in [date_widget, time_widget]:
                w.setStyleSheet(input_style)

        self.location_date_input.setStyleSheet("""
            QDateEdit {
                color:#1e293b;
                background:#ffffff;
                border:1px solid #d1d5db;
                padding:20px;
                font-size:18px;
                border-radius:6px;
            }
            QDateEdit:focus { border:2px solid #3b82f6; }
            QCalendarWidget {
                background-color: white;
            }
            QCalendarWidget QWidget {
                background-color: white;
            }
            QCalendarWidget QAbstractItemView {
                background-color: white;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QCalendarWidget QToolButton {
                background-color: white;
                color: #1e293b;
            }
        """)

            # LABELS (COMPACT)
        for i, (lbl_text, widget) in enumerate(zip(labels, widgets)):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("font-weight:600; color:#374151; font-size:18px;")
            form_layout.addWidget(lbl, i, 0)
            form_layout.addWidget(widget, i, 1)
        # ================== BOUTONS (COMPACT) ==================
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addStretch()

        # ← BOUTON ASSURANCE (toujours visible)
        self.insurance_btn = QPushButton("Ajouter Assurance")
        self.insurance_btn.setStyleSheet("""
            background:#059669; color:white; font-weight:bold;
            padding: 20px; border-radius:8px; font-size:14px;
        """)
        self.insurance_btn.setCursor(Qt.PointingHandCursor)
        self.insurance_btn.clicked.connect(self.open_insurance_dialog)

        # ← BOUTON CRÉER (visible par défaut, comme dans réservations)
        self.location_add_btn = QPushButton("CRÉER LA LOCATION")
        self.location_add_btn.setStyleSheet("""
            background:#059669; color:white; font-weight:bold;
            padding: 20px; border-radius:8px; font-size:14px;
        """)
        self.location_add_btn.setCursor(Qt.PointingHandCursor)
        self.location_add_btn.clicked.connect(self.add_location)

        # ← BOUTON ANNULER (caché par défaut, comme dans réservations)
        self.location_cancel_btn = QPushButton("ANNULER")
        self.location_cancel_btn.setStyleSheet("""
            background:#ef4444; color:white; font-weight:bold;
            padding: 20px; border-radius:8px; font-size:14px;
        """)
        self.location_cancel_btn.setCursor(Qt.PointingHandCursor)
        self.location_cancel_btn.clicked.connect(self.cancel_edit_location)
        self.location_cancel_btn.setVisible(False)  # ← Caché au démarrage

        # ← AJOUTER TOUS LES BOUTONS AU LAYOUT
        self.buttons_layout.addWidget(self.insurance_btn)
        self.buttons_layout.addSpacing(10)
        self.buttons_layout.addWidget(self.location_add_btn)
        self.buttons_layout.addSpacing(10)
        self.buttons_layout.addWidget(self.location_cancel_btn)
        self.buttons_layout.addStretch()

        form_layout.addLayout(self.buttons_layout, len(widgets) + 1, 0, 1, 2)
        top_layout.addWidget(form_widget, 3)
        # --- CHECKLIST ACCESSOIRES (COMPACT) ---
        acc_box = QWidget()
        acc_box.setStyleSheet("background:#f9fafb; border-radius:10px; padding:1px; border:1px solid #e5e7eb;")
        acc_layout = QVBoxLayout(acc_box)
        acc_layout.setSpacing(6)
        
        title_acc = QLabel("Accessoires")
        title_acc.setStyleSheet("font-size:18px; font-weight:700; color:#1e40af;")
        acc_layout.addWidget(title_acc)

        self.accessories_groups = {}
        items = [
            ("Radio", "radio"),
            ("Jack + Roue", "jack"),
            ("Allume-cigare", "lighter"),
            ("Tapis", "mat"),
            ("Code", "code")
        ]

        for text, key in items:
            h = QHBoxLayout()
            h.setSpacing(8)
            
            label = QLabel(text)
            label.setStyleSheet("font-size:18px; font-weight:500; color:#374151;")
            h.addWidget(label)
            h.addStretch()
            
            group = QButtonGroup(self)
            yes = QRadioButton("Oui")
            no = QRadioButton("Non")
            yes.setStyleSheet("font-size:18px; color:#059669;")
            no.setStyleSheet("font-size:18px; color:#dc2626;")
            
            group.addButton(yes, 1)
            group.addButton(no, 0)
            h.addWidget(yes)
            h.addWidget(no)
            acc_layout.addLayout(h)
            
            self.accessories_groups[key] = group

        top_layout.addWidget(acc_box, 2)
        layout.addWidget(top_section)
        
        # ================== HISTORIQUE (TABLE TAKES REMAINING 60%) ==================
        layout.addWidget(QLabel("Historique des Locations Actives", 
            styleSheet="font-size:18px; font-weight:700; color:#111827; margin:15px 0 8px 0;"))

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.location_table = QTableWidget()
        self.location_table.setColumnCount(8)
        self.location_table.setHorizontalHeaderLabels([
            "Matricule", "Modèle", "Client", "Date", "Jours", "Coût", "Statut", "Actions"
        ])

        self.location_table.setStyleSheet("""
            QTableWidget {
                background:white; border:1px solid #e2e8f0; border-radius:16px; font-size:18px;
                gridline-color:#f1f5f9;
            }
            QHeaderView::section {
                background:#1e40af; color:white; padding:12px; font-weight:bold; font-size:18px;
            }
        """)

        self.location_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.location_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.location_table.verticalHeader().setDefaultSectionSize(60)
        self.location_table.setAlternatingRowColors(True)
        self.location_table.setSelectionBehavior(QTableWidget.SelectRows)

        header = self.location_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed); self.location_table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.Fixed); self.location_table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed); self.location_table.setColumnWidth(5, 110)
        header.setSectionResizeMode(6, QHeaderView.Fixed); self.location_table.setColumnWidth(6, 100)
        header.setSectionResizeMode(7, QHeaderView.Fixed); self.location_table.setColumnWidth(7, 300)

        table_layout.addWidget(self.location_table)
        layout.addWidget(table_container, 1)  # ← This will take remaining space (60%)

        # ================== FINAL ==================
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        
        self.setMinimumSize(self.scale(800), self.scale(600))

        if self.content_stack.count() > 3:
            old = self.content_stack.widget(3)
            self.content_stack.removeWidget(old)
            old.deleteLater()
        
        self.content_stack.insertWidget(3, scroll)
        self.content_stack.setCurrentIndex(3)

        self.load_locations()


    # ========== NOUVELLES FONCTIONS POUR OUVRIR LES POPUPS ==========
    def open_date_picker_location(self):
        """Ouvre le sélecteur de date pour la location"""
        current = self.location_date_input.date()
        
        dialog = DatePickerDialog(current, self)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_date()
            self.location_date_input.setDate(selected)
            self.location_date_label.setText(selected.toString("dd/MM/yyyy"))
            self.load_voitures_combo(self.location_voiture_combo)  # Recharger les voitures disponibles
            print(f"✅ Date selected: {selected.toString('dd/MM/yyyy')}")


    def open_time_picker_location(self):
        """Ouvre le sélecteur d'heure pour la location"""
        current = self.location_time_input.time()
        
        dialog = TimePickerDialog(current, self)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_time()
            self.location_time_input.setTime(selected)
            self.location_time_label.setText(selected.toString("HH:mm"))
            print(f"✅ Time selected: {selected.toString('HH:mm')}")


    def edit_location(self, location_id):
        print(f"🔍 Editing location ID: {location_id}")
        
        self.current_edit_id = location_id
        
        self.cursor.execute("""
            SELECT voiture_id, client_id, second_client_id, date_heure_location, jours, 
                promotion, fuel_depart, accessories_radio, accessories_jack, 
                accessories_lighter, accessories_mat, accessories_code, km_depart 
            FROM locations WHERE id = ?
        """, (location_id,))
        data = self.cursor.fetchone()
        
        if not data:
            print("❌ Location not found")
            return

        voiture_id, client_id, second_client_id, date_location, jours, promotion, \
        fuel_depart, acc_radio, acc_jack, acc_lighter, acc_mat, acc_code, km_depart = data

        # Recharger toutes les voitures
        self.cursor.execute("SELECT id, modele FROM voitures ORDER BY modele")
        self.location_voiture_combo.clear()
        for vid, modele in self.cursor.fetchall():
            self.location_voiture_combo.addItem(modele, vid)

        # Sélectionner la voiture actuelle
        index = self.location_voiture_combo.findData(voiture_id)
        if index >= 0:
            self.location_voiture_combo.setCurrentIndex(index)

        # Remplir les champs clients
        self.cursor.execute("SELECT nom || ' ' || prenom FROM clients WHERE id = ?", (client_id,))
        self.location_client_input.setText(self.cursor.fetchone()[0])

        if second_client_id:
            self.cursor.execute("SELECT nom || ' ' || prenom FROM clients WHERE id = ?", (second_client_id,))
            self.location_client2_input.setText(self.cursor.fetchone()[0])
        else:
            self.location_client2_input.clear()

        # Autres champs
        self.location_date_input.setDate(QDate.fromString(date_location.split()[0], "yyyy-MM-dd"))
        self.location_jours_input.setText(str(jours))
        self.location_promotion_input.setText(str(promotion))
        self.location_fuel_combo.setCurrentText(fuel_depart)
        self.location_km_depart.setText(str(km_depart) if km_depart is not None else "")
        date_location = self.location_date_input.date().toString("yyyy-MM-dd")
        time_location = date_location.split()[1] if len(date_location.split()) > 1 else "00:00:00"

        self.location_date_input.setDate(QDate.fromString(date_location.split()[0], "yyyy-MM-dd"))
        self.location_time_input.setTime(QTime.fromString(time_location, "HH:mm:ss"))

        # Accessoires
        accessories = {
            "radio": acc_radio, "jack": acc_jack, "lighter": acc_lighter,
            "mat": acc_mat, "code": acc_code
        }
        for key, value in accessories.items():
            group = self.accessories_groups[key]
            group.setExclusive(False)
            if value == "oui":
                group.button(1).setChecked(True)
            elif value == "non":
                group.button(0).setChecked(True)
            else:
                group.button(0).setChecked(False)
                group.button(1).setChecked(False)
            group.setExclusive(True)
        
        # ← PASSER EN MODE ÉDITION (comme réservations)
        self.location_add_btn.setText("MODIFIER")
        try:
            self.location_add_btn.clicked.disconnect()
        except TypeError:
            pass
        self.location_add_btn.clicked.connect(lambda: self.update_location(self.current_edit_id))
        self.location_cancel_btn.setVisible(True)
        
        print("✅ Location data loaded for editing")

    def switch_to_edit_mode(self):
        """Bascule l'interface en mode édition pour les LOCATIONS"""
        print("🔄 Switching to EDIT mode for LOCATIONS")
        
        # Vérifier que les boutons existent
        if not hasattr(self, 'location_update_btn'):
            print("❌ ERROR: location_update_btn does not exist!")
            return
        
        if not hasattr(self, 'location_cancel_btn'):
            print("❌ ERROR: location_cancel_btn does not exist!")
            return
        
        # Cache le bouton "CRÉER LA LOCATION"
        self.location_add_btn.setVisible(False)
        
        # Affiche les boutons "MODIFIER" et "ANNULER"
        self.location_update_btn.setVisible(True)
        self.location_cancel_btn.setVisible(True)

        # Reconnecte le bouton MODIFIER
        try:
            self.location_update_btn.clicked.disconnect()
        except TypeError:
            pass
        
        self.location_update_btn.clicked.connect(
            lambda: self.update_location(self.current_edit_id)
        )
        
        # Force la mise à jour visuelle
        QApplication.processEvents()
        self.buttons_layout.update()
        self.update()
        
        print("✅ Edit mode activated - Buttons should be visible now")
        print(f"   location_add_btn visible: {self.location_add_btn.isVisible()}")
        print(f"   location_update_btn visible: {self.location_update_btn.isVisible()}")
        print(f"   location_cancel_btn visible: {self.location_cancel_btn.isVisible()}")


    def switch_to_add_mode(self):
        """Remet l'interface en mode ajout pour les LOCATIONS"""
        print("🔄 Switching to ADD mode for LOCATIONS")
        
        # Affiche le bouton "CRÉER LA LOCATION"
        self.location_add_btn.setVisible(True)
        
        # Cache les boutons "MODIFIER" et "ANNULER"
        if hasattr(self, 'location_update_btn'):
            self.location_update_btn.setVisible(False)
        if hasattr(self, 'location_cancel_btn'):
            self.location_cancel_btn.setVisible(False)

        # Réinitialise l'ID d'édition
        self.current_edit_id = None

        # Reconnecte le bouton créer
        try:
            self.location_add_btn.clicked.disconnect()
        except TypeError:
            pass
        
        self.location_add_btn.clicked.connect(self.add_location)
        
        # Force la mise à jour visuelle
        QApplication.processEvents()
        self.buttons_layout.update()
        self.update()
        
        print("✅ Add mode activated for LOCATIONS")



    def cancel_edit_location(self):
        """Annule l'édition (comme dans réservations)"""
        print("❌ Cancelling edit")
        self.clear_location_form()
        
        # ← Remettre en mode ajout
        self.location_add_btn.setText("CRÉER LA LOCATION")
        try:
            self.location_add_btn.clicked.disconnect()
        except TypeError:
            pass
        self.location_add_btn.clicked.connect(self.add_location)
        self.location_cancel_btn.setVisible(False)
        
        self.load_voitures_combo(self.location_voiture_combo)

    def open_insurance_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Assurance & Informations de Paiement")
        dialog.setFixedSize(self.scale(600), self.scale(550))
        dialog.setStyleSheet("background: white; border-radius: 16px;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Informations Assurance & Paiement")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #1e293b;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)

        self.ins_company = QLineEdit()
        self.ins_policy = QLineEdit()
        self.pay_method = QComboBox()
        self.pay_method.addItems(["Espèces", "Chèque"])
        self.check_num = QLineEdit()
        self.check_date = QDateEdit()
        self.check_date.setCalendarPopup(True)
        self.check_date.setDate(QDate.currentDate())
        self.deposit_amount = QLineEdit()
        self.deposit_method = QComboBox()
        self.deposit_method.addItems(["Espèces", "Chèque"])
        self.bank_name = QLineEdit()

        fields = [
            ("Compagnie d'assurance :", self.ins_company),
            ("Numéro de police d'assurance :", self.ins_policy),
            ("Mode de paiement :", self.pay_method),
            ("Numéro du chèque :", self.check_num),
            ("Date du chèque :", self.check_date),
            ("Montant de la caution (DA) :", self.deposit_amount),
            ("Mode de caution :", self.deposit_method),
            ("Banque :", self.bank_name),
        ]

        for label_text, widget in fields:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: 600; color: #374151; font-size: 15px;")
            widget.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px;")
            form.addRow(lbl, widget)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet("background: #059669; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold;")
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("background: #e11d48; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold;")
        
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addSpacing(15)
        btn_box.addWidget(save_btn)
        btn_box.addStretch()
        layout.addLayout(btn_box)

                # Stockage des valeurs dans l'instance pour utilisation dans add_location / update_location
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_insurance_data = {
                "company": self.ins_company.text().strip(),
                "policy": self.ins_policy.text().strip(),
                "pay_method": "Cash" if self.pay_method.currentIndex() == 0 else "Check",   # ← Anglais
                "check_num": self.check_num.text().strip(),
                "check_date": self.check_date.date().toString("yyyy-MM-dd"),
                "deposit_amount": float(self.deposit_amount.text() or 0),
                "deposit_method": "Cash" if self.deposit_method.currentIndex() == 0 else "Check",  # ← Anglais
                "bank": self.bank_name.text().strip(),
            }
            QMessageBox.information(self, "Succès", "Les informations d'assurance et de paiement ont été enregistrées temporairement.")
        else:
            self.current_insurance_data = None


    def load_voitures_combo(self, combo):
        """Charge TOUTES les voitures avec indication si réservées"""
        try:
            if combo is None or not hasattr(combo, 'clear'):
                return
            
            combo.clear()
            
            # Date sélectionnée (pour location) ou aujourd'hui
            if hasattr(self, 'location_date_input') and combo == self.location_voiture_combo:
                selected_date = self.location_date_input.date().toString("yyyy-MM-dd")
            else:
                selected_date = QDate.currentDate().toString("yyyy-MM-dd")
            
            print(f"🔍 Loading cars for date: {selected_date}")
            
            # Récupérer TOUTES les voitures
            self.cursor.execute("""
                SELECT v.id, v.modele, v.numero_matricule, v.statut
                FROM voitures v
                ORDER BY v.modele
            """)
            
            all_cars = self.cursor.fetchall()
            
            for car_id, modele, matricule, statut in all_cars:
                # Vérifier si la voiture a une réservation active
                self.cursor.execute("""
                    SELECT date_debut, jours 
                    FROM reservations 
                    WHERE voiture_id = ? AND statut = 'Active'
                    ORDER BY date_debut
                    LIMIT 1
                """, (car_id,))
                
                reservation = self.cursor.fetchone()
                
                if reservation:
                    date_debut, jours = reservation
                    date_debut_qt = QDate.fromString(date_debut, "yyyy-MM-dd")
                    date_fin_qt = date_debut_qt.addDays(jours - 1)
                    
                    date_debut_formatted = date_debut_qt.toString("dd/MM/yyyy")
                    date_fin_formatted = date_fin_qt.toString("dd/MM/yyyy")
                    
                    # Afficher avec période de réservation
                    display_text = f"{modele} - {matricule} (Réservée du {date_debut_formatted} au {date_fin_formatted})"
                    
                    # ⚠️ LOGIQUE CORRIGÉE : Vérifier si la date de location CHEVAUCHE la réservation
                    selected_qt = QDate.fromString(selected_date, "yyyy-MM-dd")
                    
                    # ← FIX: La voiture est disponible SI la date est AVANT **le début** OU APRÈS **la fin**
                    if selected_qt < date_debut_qt or selected_qt > date_fin_qt:
                        # Date de location HORS de la réservation → DISPONIBLE
                        combo.addItem(display_text, car_id)
                        print(f"✅ Car {car_id} ({modele}) is AVAILABLE (outside reservation period)")
                    else:
                        # Date de location PENDANT la réservation → désactivée
                        combo.addItem(display_text, None)
                        print(f"❌ Car {car_id} ({modele}) is BLOCKED (inside reservation period)")
                
                elif statut == "Disponible":
                    # Voiture totalement disponible
                    combo.addItem(f"{modele} - {matricule}", car_id)
                    print(f"✅ Car {car_id} ({modele}) is fully available")
                
                elif statut == "Louée":
                    # Actuellement louée → ne pas afficher
                    print(f"🚫 Car {car_id} ({modele}) is currently rented (hidden)")
                    pass
                
                elif statut == "En Réparation":
                    # En réparation → affichée mais désactivée
                    combo.addItem(f"{modele} - {matricule} (En Réparation)", None)
                    print(f"🔧 Car {car_id} ({modele}) is in repair (disabled)")
            
        except (RuntimeError, AttributeError) as e:
            print(f"ERROR in load_voitures_combo: {e}")
            pass



    def get_client_id(self, client_name):
        if not client_name.strip():
            return None

        client_name = client_name.strip()
        
        # On cherche EXACTEMENT le nom complet dans la base
        self.cursor.execute("""
            SELECT id FROM clients 
            WHERE nom || ' ' || prenom = ? 
            OR prenom || ' ' || nom = ?
        """, (client_name, client_name))
        
        result = self.cursor.fetchone()
        if result:
            return result[0]

        # Si pas trouvé exactement → on fait une recherche intelligente par parties
        self.cursor.execute("SELECT id, nom, prenom FROM clients")
        all_clients = self.cursor.fetchall()

        search_words = client_name.lower().split()
        
        for cid, nom, prenom in all_clients:
            full_name = f"{nom} {prenom}".lower()
            full_name_reverse = f"{prenom} {nom}".lower()
            
            # Si tous les mots tapés sont dans le nom complet → on valide
            if all(word in full_name or word in full_name_reverse for word in search_words):
                return cid

        return None  # Vraiment pas trouvé
    
    def load_clients_completer(self, completer):
        self.cursor.execute("SELECT nom || ' ' || prenom FROM clients ORDER BY nom")
        clients = [row[0] for row in self.cursor.fetchall()]
        
        model = QStringListModel(clients)
        completer.setModel(model)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)  # Recherche même en tapant au milieu
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.cursor.execute("SELECT nom || ' ' || prenom FROM clients ORDER BY nom")
        clients = [row[0] for row in self.cursor.fetchall()]
        
        model = QStringListModel(clients)
        completer.setModel(model)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)  # Recherche même en tapant au milieu
        completer.setCompletionMode(QCompleter.PopupCompletion)


    def add_location(self):
        voiture_id = self.location_voiture_combo.currentData()
        
        # ← VÉRIFICATION SI LA VOITURE EST DÉSACTIVÉE (None)
        if voiture_id is None:
            QMessageBox.warning(self, "Erreur", 
                "Cette voiture n'est pas disponible pour la date sélectionnée.\n"
                "Veuillez choisir une autre voiture ou modifier la date de location.")
            return
        
        print(f"✅ Selected car ID: {voiture_id}")
        
        client_name = self.location_client_input.text().strip()
        client_id = self.get_client_id(client_name)
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Client principal non trouvé.")
            return

        # ← VÉRIFICATION : Alerte si voiture réservée ET date dans la période
        date_location_selected = self.location_date_input.date().toString("yyyy-MM-dd")
        
        self.cursor.execute("""
            SELECT r.date_debut, r.jours, c.nom || ' ' || c.prenom
            FROM reservations r
            JOIN clients c ON r.client_id = c.id
            WHERE r.voiture_id = ? AND r.statut = 'Active'
            ORDER BY r.date_debut
            LIMIT 1
        """, (voiture_id,))
        
        reservation_info = self.cursor.fetchone()
        
        if reservation_info:
            date_debut, jours, client_reserv = reservation_info
            date_debut_qt = QDate.fromString(date_debut, "yyyy-MM-dd")
            date_fin_qt = date_debut_qt.addDays(jours - 1)
            
            date_debut_formatted = date_debut_qt.toString("dd/MM/yyyy")
            date_fin_formatted = date_fin_qt.toString("dd/MM/yyyy")
            
            selected_qt = QDate.fromString(date_location_selected, "yyyy-MM-dd")
            
            # ← FIX CRITIQUE : Afficher l'alerte UNIQUEMENT si la date est HORS de la réservation
            if selected_qt < date_debut_qt or selected_qt > date_fin_qt:
                print(f"ℹ️ Date {date_location_selected} is outside reservation ({date_debut} to {date_fin_qt.toString('yyyy-MM-dd')})")
                
                # Date de location HORS de la réservation → OK mais on informe
                alert_dialog = QDialog(self)
                alert_dialog.setWindowTitle("ℹ️ Information")
                alert_dialog.setFixedSize(self.scale(500), self.scale(240))
                alert_dialog.setStyleSheet("""
                    QDialog {
                        background: white;
                        border-radius: 16px;
                    }
                """)
                
                layout = QVBoxLayout(alert_dialog)
                layout.setContentsMargins(30, 30, 30, 30)
                layout.setSpacing(20)
                
                # Titre
                title = QLabel("ℹ️ Voiture Réservée")
                title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0891b2;")
                title.setAlignment(Qt.AlignCenter)
                layout.addWidget(title)
                
                # Message d'information
                info_text = f"""
                <b>Cette voiture a une réservation active :</b><br><br>
                <b>Client :</b> {client_reserv}<br>
                <b>Période réservée :</b> du {date_debut_formatted} au {date_fin_formatted}<br><br>
                <span style="color:#059669; font-weight:bold;">
                ✓ Votre date de location ({self.location_date_input.date().toString('dd/MM/yyyy')}) 
                est en dehors de cette période, vous pouvez continuer.
                </span>
                """
                
                info_label = QLabel(info_text)
                info_label.setStyleSheet("font-size: 14px; color: #374151; line-height: 1.6;")
                info_label.setWordWrap(True)
                layout.addWidget(info_label)
                
                # Bouton OK
                ok_btn = QPushButton("✓ J'ai compris, continuer")
                ok_btn.setStyleSheet("""
                    background: #059669; color: white; padding: 12px 30px;
                    border-radius: 10px; font-weight: bold; font-size: 14px;
                """)
                ok_btn.setCursor(Qt.PointingHandCursor)
                ok_btn.clicked.connect(alert_dialog.accept)
                
                layout.addWidget(ok_btn, alignment=Qt.AlignCenter)
                
                alert_dialog.exec_()
            else:
                # ← Si la date tombe PENDANT la réservation, on ne devrait JAMAIS arriver ici
                # car load_voitures_combo() aurait dû mettre voiture_id = None
                print(f"⚠️ WARNING: Date {date_location_selected} is INSIDE reservation but car was selectable!")
                QMessageBox.critical(self, "Erreur Système", 
                    "Erreur de validation : cette voiture est réservée pour cette date.\n"
                    "Veuillez recharger la page ou contacter le support.")
                return


        # ← TEST CONDUCTEUR 1 (principal)
        self.cursor.execute("SELECT date_naissance FROM clients WHERE id = ?", (client_id,))
        date_naiss_row = self.cursor.fetchone()
        
        if date_naiss_row and date_naiss_row[0]:
            try:
                date_naiss = datetime.strptime(date_naiss_row[0], "%Y-%m-%d").date()
                age = (date.today() - date_naiss).days // 365
                
                if age < 25:
                    age_dialog = QDialog(self)
                    age_dialog.setWindowTitle("⚠️ Âge Insuffisant - Conducteur Principal")
                    age_dialog.setFixedSize(self.scale(500), self.scale(250))
                    age_dialog.setStyleSheet("QDialog { background: white; border-radius: 16px; }")
                    
                    layout = QVBoxLayout(age_dialog)
                    layout.setContentsMargins(30, 30, 30, 30)
                    layout.setSpacing(20)
                    
                    title = QLabel("⚠️ Conducteur Principal Trop Jeune")
                    title.setStyleSheet("font-size: 22px; font-weight: bold; color: #dc2626;")
                    title.setAlignment(Qt.AlignCenter)
                    layout.addWidget(title)
                    
                    info_text = f"""
                    <b>Client :</b> {client_name}<br>
                    <b>Âge actuel :</b> {age} ans<br><br>
                    <span style="color:#dc2626; font-weight:bold;">
                    ⚠️ L'âge minimum requis pour louer un véhicule est de 25 ans.
                    </span>
                    """
                    
                    info_label = QLabel(info_text)
                    info_label.setStyleSheet("font-size: 14px; color: #374151; line-height: 1.6;")
                    info_label.setWordWrap(True)
                    layout.addWidget(info_label)
                    
                    question = QLabel("Voulez-vous continuer malgré tout ?")
                    question.setStyleSheet("font-size: 15px; font-weight: 600; color: #1e293b;")
                    question.setAlignment(Qt.AlignCenter)
                    layout.addWidget(question)
                    
                    btn_layout = QHBoxLayout()
                    btn_layout.setSpacing(15)
                    
                    continue_btn = QPushButton("✓ Continuer")
                    continue_btn.setStyleSheet("background: #f59e0b; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold; font-size: 14px;")
                    continue_btn.setCursor(Qt.PointingHandCursor)
                    
                    cancel_btn = QPushButton("✕ Annuler")
                    cancel_btn.setStyleSheet("background: #dc2626; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold; font-size: 14px;")
                    cancel_btn.setCursor(Qt.PointingHandCursor)
                    
                    continue_btn.clicked.connect(age_dialog.accept)
                    cancel_btn.clicked.connect(age_dialog.reject)
                    
                    btn_layout.addWidget(continue_btn)
                    btn_layout.addWidget(cancel_btn)
                    layout.addLayout(btn_layout)
                    
                    result = age_dialog.exec_()
                    
                    if result != QDialog.Accepted:
                        print("❌ Location cancelled due to age restriction (driver 1)")
                        return
                    
                    print("✅ User chose to continue despite age < 25 (driver 1)")
            except:
                pass

        # ← NOUVEAU : TEST CONDUCTEUR 2 (secondaire) ===
        client2_name = self.location_client2_input.text().strip()
        second_client_id = self.get_client_id(client2_name) if client2_name else None
        
        if second_client_id:
            self.cursor.execute("SELECT date_naissance FROM clients WHERE id = ?", (second_client_id,))
            date_naiss_row2 = self.cursor.fetchone()
            
            if date_naiss_row2 and date_naiss_row2[0]:
                try:
                    date_naiss2 = datetime.strptime(date_naiss_row2[0], "%Y-%m-%d").date()
                    age2 = (date.today() - date_naiss2).days // 365
                    
                    if age2 < 25:
                        age_dialog2 = QDialog(self)
                        age_dialog2.setWindowTitle("⚠️ Âge Insuffisant - Conducteur Secondaire")
                        age_dialog2.setFixedSize(self.scale(500), self.scale(250))
                        age_dialog2.setStyleSheet("QDialog { background: white; border-radius: 16px; }")
                        
                        layout2 = QVBoxLayout(age_dialog2)
                        layout2.setContentsMargins(30, 30, 30, 30)
                        layout2.setSpacing(20)
                        
                        title2 = QLabel("⚠️ Conducteur Secondaire Trop Jeune")
                        title2.setStyleSheet("font-size: 22px; font-weight: bold; color: #dc2626;")
                        title2.setAlignment(Qt.AlignCenter)
                        layout2.addWidget(title2)
                        
                        info_text2 = f"""
                        <b>Client secondaire :</b> {client2_name}<br>
                        <b>Âge actuel :</b> {age2} ans<br><br>
                        <span style="color:#dc2626; font-weight:bold;">
                        ⚠️ L'âge minimum requis pour conduire est de 25 ans.
                        </span>
                        """
                        
                        info_label2 = QLabel(info_text2)
                        info_label2.setStyleSheet("font-size: 14px; color: #374151; line-height: 1.6;")
                        info_label2.setWordWrap(True)
                        layout2.addWidget(info_label2)
                        
                        question2 = QLabel("Voulez-vous continuer malgré tout ?")
                        question2.setStyleSheet("font-size: 15px; font-weight: 600; color: #1e293b;")
                        question2.setAlignment(Qt.AlignCenter)
                        layout2.addWidget(question2)
                        
                        btn_layout2 = QHBoxLayout()
                        btn_layout2.setSpacing(15)
                        
                        continue_btn2 = QPushButton("✓ Continuer")
                        continue_btn2.setStyleSheet("background: #f59e0b; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold; font-size: 14px;")
                        continue_btn2.setCursor(Qt.PointingHandCursor)
                        
                        cancel_btn2 = QPushButton("✕ Annuler")
                        cancel_btn2.setStyleSheet("background: #dc2626; color: white; padding: 12px 30px; border-radius: 10px; font-weight: bold; font-size: 14px;")
                        cancel_btn2.setCursor(Qt.PointingHandCursor)
                        
                        continue_btn2.clicked.connect(age_dialog2.accept)
                        cancel_btn2.clicked.connect(age_dialog2.reject)
                        
                        btn_layout2.addWidget(continue_btn2)
                        btn_layout2.addWidget(cancel_btn2)
                        layout2.addLayout(btn_layout2)
                        
                        result2 = age_dialog2.exec_()
                        
                        if result2 != QDialog.Accepted:
                            print("❌ Location cancelled due to age restriction (driver 2)")
                            return
                        
                        print("✅ User chose to continue despite age < 25 (driver 2)")
                except:
                    pass# Si erreur de parsing de date, continuer normalement

        # === NOUVELLE VÉRIFICATION : Réservation active du client ===
        self.cursor.execute("""
            SELECT r.id, r.date_debut, r.cout_total, r.payment_percentage, v.modele
            FROM reservations r
            JOIN voitures v ON r.voiture_id = v.id
            WHERE r.client_id = ? AND r.statut = 'Active'
            ORDER BY r.date_debut DESC
            LIMIT 1
        """, (client_id,))
        
        reservation = self.cursor.fetchone()
        
        montant_a_deduire = 0
        reservation_id_to_close = None
        
        if reservation:
            res_id, date_debut, cout_total, payment_percentage, modele = reservation
            montant_paye = cout_total * payment_percentage / 100
            
            # Créer un popup personnalisé
            reply_dialog = QDialog(self)
            reply_dialog.setWindowTitle("Réservation Détectée")
            reply_dialog.setFixedSize(self.scale(500), self.scale(280))
            reply_dialog.setStyleSheet("""
                QDialog {
                    background: white;
                    border-radius: 16px;
                }
            """)
            
            layout = QVBoxLayout(reply_dialog)
            layout.setContentsMargins(30, 30, 30, 30)
            layout.setSpacing(20)
            
            # Titre
            title = QLabel("⚠️ Réservation Active Trouvée")
            title.setStyleSheet("font-size: 22px; font-weight: bold; color: #dc2626;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Message d'information
            info_text = f"""
            <b>Client :</b> {client_name}<br>
            <b>Véhicule réservé :</b> {modele}<br>
            <b>Date de réservation :</b> {date_debut}<br>
            <b>Montant total :</b> {cout_total:,.0f} DA<br>
            <b style="color:#059669;">Montant déjà payé :</b> {montant_paye:,.0f} DA
            """
            
            info_label = QLabel(info_text)
            info_label.setStyleSheet("font-size: 14px; color: #374151; line-height: 1.6;")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            question = QLabel("Voulez-vous déduire ce montant du coût de la location ?")
            question.setStyleSheet("font-size: 15px; font-weight: 600; color: #1e293b;")
            question.setAlignment(Qt.AlignCenter)
            layout.addWidget(question)
            
            # Boutons
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(8)
            
            continue_btn = QPushButton(" Continuer")
            continue_btn.setStyleSheet("""
                background: #059669; color: white; padding: 12px 30px;
                border-radius: 10px; font-weight: bold; font-size: 14px;
            """)
            continue_btn.setCursor(Qt.PointingHandCursor)
            
            ignore_btn = QPushButton(" Ignorer")
            ignore_btn.setStyleSheet("""
                background: #f59e0b; color: white; padding: 12px 30px;
                border-radius: 10px; font-weight: bold; font-size: 14px;
            """)
            ignore_btn.setCursor(Qt.PointingHandCursor)
            
            cancel_btn = QPushButton(" Annuler")
            cancel_btn.setStyleSheet("""
                background: #dc2626; color: white; padding: 12px 30px;
                border-radius: 10px; font-weight: bold; font-size: 14px;
            """)
            cancel_btn.setCursor(Qt.PointingHandCursor)
            
            # Variable pour stocker le choix
            user_choice = {"action": None}
            
            def on_continue():
                user_choice["action"] = "deduct"
                reply_dialog.accept()
            
            def on_ignore():
                user_choice["action"] = "ignore"
                reply_dialog.accept()
            
            def on_cancel():
                user_choice["action"] = "cancel"
                reply_dialog.reject()
            
            continue_btn.clicked.connect(on_continue)
            ignore_btn.clicked.connect(on_ignore)
            cancel_btn.clicked.connect(on_cancel)
            
            btn_layout.addWidget(continue_btn)
            btn_layout.addWidget(ignore_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            # Exécuter le dialog
            result = reply_dialog.exec_()
            
            # Si le dialog a été fermé sans choisir d'action (X ou Escape), annuler
            if user_choice["action"] is None or user_choice["action"] == "cancel":
                return  # Annuler complètement la création de location
            
            if user_choice["action"] == "deduct":
                montant_a_deduire = montant_paye
                reservation_id_to_close = res_id

        # === SUITE DU CODE NORMAL (avec déduction si applicable) ===
        
        # Vérification de l'expiration du permis
        self.cursor.execute("SELECT date_expiration_permis FROM clients WHERE id = ?", (client_id,))
        exp_row = self.cursor.fetchone()
        if exp_row and exp_row[0]:
            try:
                exp_date = datetime.strptime(exp_row[0], "%Y-%m-%d").date()
                if exp_date < date.today():
                    QMessageBox.warning(self, "Permis expiré", 
                        "Le permis de conduire du client principal est expiré.\nImpossible de créer la location.")
                    return
            except:
                pass

        # Vérification permis client secondaire
        client2_name = self.location_client2_input.text().strip()
        second_client_id = self.get_client_id(client2_name) if client2_name else None
        if second_client_id:
            self.cursor.execute("SELECT date_expiration_permis FROM clients WHERE id = ?", (second_client_id,))
            exp_row = self.cursor.fetchone()
            if exp_row and exp_row[0]:
                try:
                    exp_date = datetime.strptime(exp_row[0], "%Y-%m-%d").date()
                    if exp_date < date.today():
                        QMessageBox.warning(self, "Permis expiré", 
                            "Le permis de conduire du client secondaire est expiré.\nImpossible de créer la location.")
                        return
                except:
                    pass

        date_location = self.location_date_input.date().toString("yyyy-MM-dd")
        time_location = self.location_time_input.time().toString("HH:mm:ss")
        date_location_full = f"{date_location} {time_location}"        
            
        try:
            jours = int(self.location_jours_input.text())
            if jours <= 0:
                raise ValueError(self.translations["fr"]["error_jours_positif"])
            promotion = int(self.location_promotion_input.text() or 0)
            if promotion < 0:
                raise ValueError("Promotion doit être positive ou zéro.")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return

        fuel_depart = self.location_fuel_combo.currentText()
        try:
            km_depart = int(self.location_km_depart.text() or 0)
            if km_depart < 0:
                raise ValueError("Kilométrage doit être positif ou zéro.")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return
        
        accessories = {}
        for key, group in self.accessories_groups.items():
            if group.checkedId() == 1:
                accessories[key] = "oui"
            elif group.checkedId() == 0:
                accessories[key] = "non"
            else:
                accessories[key] = None

        self.cursor.execute("SELECT prix_jour FROM voitures WHERE id = ?", (voiture_id,))
        result = self.cursor.fetchone()
        if not result:
            QMessageBox.critical(self, "Erreur", "Voiture introuvable ou supprimée !")
            return
        
        prix_jour = result[0]
        cout_total = jours * (prix_jour - promotion)
        
        # === DÉDUCTION DU MONTANT DE LA RÉSERVATION ===
        cout_final = cout_total - montant_a_deduire
        if cout_final < 0:
            cout_final = 0

        # Insurance & payment data
        ins_data = getattr(self, "current_insurance_data", None) or {
            "company": "", "policy": "", "pay_method": "Cash",
            "check_num": "", "check_date": "", "deposit_amount": 0.0,
            "deposit_method": "Cash", "bank": ""
        }

        insurance_company = ins_data["company"]
        insurance_policy = ins_data["policy"]
        payment_method = ins_data["pay_method"]
        check_number = ins_data["check_num"]
        check_date = ins_data["check_date"]
        deposit_amount = ins_data["deposit_amount"]
        deposit_method = ins_data["deposit_method"]
        bank = ins_data["bank"]
        
        # ← UTILISER date_location_full au lieu de date_location + datetime.now()
        self.cursor.execute("""
            INSERT INTO locations (
                voiture_id, client_id, second_client_id, date_heure_location, jours, cout_total,
                fuel_depart, promotion, accessories_radio, accessories_jack, accessories_lighter,
                accessories_mat, accessories_code, km_depart,
                insurance_company, insurance_policy, payment_method, check_number, check_date,
                deposit_amount, deposit_method, bank
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            voiture_id, client_id, second_client_id, date_location_full, jours, cout_final,
            fuel_depart, promotion,
            accessories['radio'], accessories['jack'], accessories['lighter'], accessories['mat'], accessories['code'],
            km_depart,
            insurance_company, insurance_policy, payment_method, check_number, check_date,
            deposit_amount, deposit_method, bank
        ))

        self.cursor.execute("UPDATE voitures SET statut = 'Louée' WHERE id = ?", (voiture_id,))
        
        # === CLÔTURER LA RÉSERVATION SI DÉDUCTION APPLIQUÉE ===
        if reservation_id_to_close:
            self.cursor.execute("UPDATE reservations SET statut = 'Terminée' WHERE id = ?", (reservation_id_to_close,))
        
        self.conn.commit()
        
        self.load_locations()
        self.load_voitures()
        self.load_reservations()
        self.load_voitures_combo(self.location_voiture_combo)  # ← FIX: Passer le combo en paramètre
        
        # Générer facture
        details = f"Location ID: {self.cursor.lastrowid}\nVoiture: {self.location_voiture_combo.currentText()}\nClient: {client_name}\nDate: {date_location}\nJours: {jours}\nCoût Total: {cout_final:.2f} DA"
        self.cursor.execute("INSERT INTO factures (location_id, details) VALUES (?, ?)", (self.cursor.lastrowid, details))
        self.conn.commit()
        self.load_factures()
        self.clear_location_form()
        self.switch_to_add_mode()
        self.load_voitures_combo(self.location_voiture_combo)  # ← FIX: Passer le combo en paramètre

        # Message de confirmation personnalisé
        if montant_a_deduire > 0:
            QMessageBox.information(self, "Succès", 
                f"Location créée avec succès !\n\n"
                f"Coût brut : {cout_total:,.0f} DA\n"
                f"Montant déduit (réservation) : -{montant_a_deduire:,.0f} DA\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"TOTAL À PAYER : {cout_final:,.0f} DA\n\n"
                f"La réservation associée a été clôturée automatiquement.")
        else:
            QMessageBox.information(self, "Succès", "Location ajoutée et facture générée.")


    def load_locations(self):
        self.update_expired_locations()  # <--- AJOUTE ÇA
        self.location_table.setRowCount(0)
        # Ajouter le statut dans la requête SQL
        self.cursor.execute("""
            SELECT l.id, v.numero_matricule, v.modele, c.nom || ' ' || c.prenom, 
                l.date_heure_location, l.jours, l.cout_total, l.statut
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
            WHERE l.statut = 'Active' OR l.statut = 'Terminée'
            ORDER BY l.date_heure_location DESC
        """)
        rows = self.cursor.fetchall()
        self.location_table.setRowCount(len(rows))

        for i, (lid, matricule, modele, client, date_loc, jours, cout, statut_db) in enumerate(rows):
            self.location_table.setItem(i, 0, QTableWidgetItem(matricule))
            self.location_table.setItem(i, 1, QTableWidgetItem(modele))
            self.location_table.setItem(i, 2, QTableWidgetItem(client))
            self.location_table.setItem(i, 3, QTableWidgetItem(date_loc.split()[0]))
            self.location_table.setItem(i, 4, QTableWidgetItem(str(jours)))
            self.location_table.setItem(i, 5, QTableWidgetItem(f"{cout:.2f} DA"))

            # Statut réel mis à jour
            if statut_db == "Terminée":
                statut_item = QTableWidgetItem("Terminée")
                statut_item.setForeground(QColor("#16a34a"))  # vert
                statut_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            else:
                # Vérifier si elle devrait être terminée
                date_debut = QDate.fromString(date_loc.split()[0], "yyyy-MM-dd")
                date_fin_prevue = date_debut.addDays(jours)
                if QDate.currentDate() > date_fin_prevue:
                    # Mise à jour automatique du statut
                    self.cursor.execute("UPDATE locations SET statut = 'Terminée' WHERE id = ?", (lid,))
                    self.conn.commit()
                    statut_item = QTableWidgetItem("Terminée")
                    statut_item.setForeground(QColor("#16a34a"))
                else:
                    statut_item = QTableWidgetItem("En cours")
                    statut_item.setForeground(QColor("#dc2626"))
                statut_item.setFont(QFont("Segoe UI", 14, QFont.Bold))

            self.location_table.setItem(i, 6, statut_item)

            # ACTIONS
            actions = QWidget()
            a_layout = QHBoxLayout(actions)
            a_layout.setContentsMargins(8, 4, 8, 4)
            a_layout.setSpacing(8)


            details = QPushButton("Détails")
            details.setStyleSheet( "background:#3b82f6; color:white;")
            details.clicked.connect(lambda _, x=lid: self.show_location_details(x))

            edit = QPushButton("Éditer")
            edit.setStyleSheet( "background:#06b6d4; color:white;")
            edit.clicked.connect(lambda _, x=lid: self.edit_location(x))

            supp = QPushButton("Supprimer")
            supp.setStyleSheet( "background:#dc2626; color:white;")
            supp.clicked.connect(lambda _, x=lid: self.delete_location(x))
            
            a_layout.addWidget(details)
            a_layout.addWidget(edit)
            a_layout.addWidget(supp)

            self.location_table.setCellWidget(i, 7, actions)

    def update_expired_locations(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        self.cursor.execute("""
            SELECT l.id, l.jours, l.date_heure_location, l.voiture_id
            FROM locations l
            WHERE l.statut = 'Active'
        """)
        for loc_id, jours, date_str, voiture_id in self.cursor.fetchall():
            date_debut = QDate.fromString(date_str.split()[0], "yyyy-MM-dd")
            date_fin = date_debut.addDays(jours)
            if QDate.currentDate() >= date_fin:
                self.cursor.execute("UPDATE locations SET statut = 'Terminée' WHERE id = ?", (loc_id,))
                # Libérer la voiture seulement si plus aucune location active
                self.cursor.execute("""
                    UPDATE voitures SET statut = 'Disponible' 
                    WHERE id = ? AND id NOT IN (
                        SELECT voiture_id FROM locations WHERE statut = 'Active'
                    )
                """, (voiture_id,))
        self.conn.commit()


    def delete_selected_locations(self):
        selected_ids = []
        for i in range(self.location_table.rowCount()):
            check_widget = self.location_table.cellWidget(i, 0)
            check = check_widget.layout().itemAt(0).widget()
            if check.isChecked():
                lid = int(self.location_table.item(i, 1).text())
                selected_ids.append(lid)
        if selected_ids:
            reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_selection"],
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for lid in selected_ids:
                    self.cursor.execute("SELECT voiture_id FROM locations WHERE id = ?", (lid,))
                    voiture_id = self.cursor.fetchone()[0]
                    self.cursor.execute("DELETE FROM locations WHERE id = ?", (lid,))
                    self.cursor.execute("DELETE FROM factures WHERE location_id = ?", (lid,))
                    self.cursor.execute("UPDATE voitures SET statut = 'Disponible' WHERE id = ?", (voiture_id,))
                self.conn.commit()
                self.load_locations()
                self.load_voitures()
                self.load_factures()

    def show_location_details(self, location_id):
        self.cursor.execute("""
            SELECT v.modele, c.nom || ' ' || c.prenom, c2.nom || ' ' || c2.prenom, l.date_heure_location, l.jours, l.cout_total, l.fuel_depart, l.promotion, l.accessories_radio, l.accessories_jack, l.accessories_lighter, l.accessories_mat, l.accessories_code
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
            LEFT JOIN clients c2 ON l.second_client_id = c2.id
            WHERE l.id = ?
        """, (location_id,))
        location = self.cursor.fetchone()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.translations['fr']['details']} Location ID {location_id}")
        layout = QVBoxLayout(dialog)
        labels = [
            self.translations['fr']["modele"],
            self.translations['fr']["client"],
            self.translations['fr']["client_2_optionnel"],
            self.translations['fr']["date_location"],
            self.translations['fr']["jours"],
            self.translations['fr']["cout_total"],
            self.translations['fr']["fuel_depart"],
            self.translations['fr']["promotion"]
        ]
        for label, value in zip(labels, location[:8]):
            layout.addWidget(QLabel(f"{label} {value or 'N/A'}"))
            
        # Accessories
        accessories_labels = [
            "Radio",
            "Jack et roue de secours",
            "Allume-cigare",
            "Tapis",
            "Code"
        ]
        for alabel, avalue in zip(accessories_labels, location[8:]):
            layout.addWidget(QLabel(f"{alabel}: {avalue or 'N/A'}"))
        close_btn = QPushButton(self.translations['fr']["fermer"])
        close_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; border-radius: 5px;")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dialog.resize(600, 400)
        dialog.exec_()




    def update_location(self, location_id):
        voiture_id = self.location_voiture_combo.currentData()
        client_name = self.location_client_input.text().strip()
        client_id = self.get_client_id(client_name)
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Client principal non trouvé.")
            return

        client2_name = self.location_client2_input.text().strip()
        second_client_id = self.get_client_id(client2_name) if client2_name else None

        date_location = self.location_date_input.date().toString("yyyy-MM-dd")
        time_location = self.location_time_input.time().toString("HH:mm:ss")
        date_location_full = f"{date_location} {time_location}"
        
        try:
            jours = int(self.location_jours_input.text())
            if jours <= 0:
                raise ValueError("Le nombre de jours doit être positif.")
            promotion = int(self.location_promotion_input.text() or 0)
            if promotion < 0:
                raise ValueError("La promotion doit être positive ou zéro.")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return

        fuel_depart = self.location_fuel_combo.currentText()
        km_depart = int(self.location_km_depart.text() or 0)
        accessories = {}
        for key, group in self.accessories_groups.items():
            if group.checkedId() == 1:
                accessories[key] = "oui"
            elif group.checkedId() == 0:
                accessories[key] = "non"
            else:
                accessories[key] = None

        self.cursor.execute("SELECT prix_jour FROM voitures WHERE id = ?", (voiture_id,))
        result = self.cursor.fetchone()
        if not result:
            QMessageBox.critical(self, "Erreur", "Voiture introuvable ou supprimée !")
            return
        prix_jour = result[0]
        cout_total = jours * (prix_jour - promotion)

        ins_data = getattr(self, "current_insurance_data", None) or {
            "company": "", "policy": "", "pay_method": "Cash",
            "check_num": "", "check_date": "", "deposit_amount": 0.0,
            "deposit_method": "Cash", "bank": ""
        }

        self.cursor.execute("SELECT voiture_id FROM locations WHERE id = ?", (location_id,))
        old_voiture_id = self.cursor.fetchone()[0]

        self.cursor.execute("""
            UPDATE locations SET
                voiture_id = ?, client_id = ?, second_client_id = ?,
                date_heure_location = ?, jours = ?, cout_total = ?,
                fuel_depart = ?, promotion = ?,
                accessories_radio = ?, accessories_jack = ?, accessories_lighter = ?,
                accessories_mat = ?, accessories_code = ?, km_depart = ?,
                insurance_company = ?, insurance_policy = ?, payment_method = ?,
                check_number = ?, check_date = ?, deposit_amount = ?, deposit_method = ?, bank = ?,
                statut = 'Active'
            WHERE id = ?
        """, (
            voiture_id, client_id, second_client_id,
            date_location_full, jours, cout_total,  # ← UTILISER date_location_full
            fuel_depart, promotion,
            accessories['radio'], accessories['jack'], accessories['lighter'],
            accessories['mat'], accessories['code'], km_depart,
            ins_data["company"], ins_data["policy"], ins_data["pay_method"],
            ins_data["check_num"], ins_data["check_date"],
            ins_data["deposit_amount"], ins_data["deposit_method"], ins_data["bank"],
            location_id
        ))

        if old_voiture_id != voiture_id:
            self.cursor.execute("""
                UPDATE voitures SET statut = 'Disponible'
                WHERE id = ? AND id NOT IN (
                    SELECT voiture_id FROM locations WHERE statut = 'Active'
                    UNION
                    SELECT voiture_id FROM reservations WHERE statut = 'Active'
                )
            """, (old_voiture_id,))

        self.cursor.execute("UPDATE voitures SET statut = 'Louée' WHERE id = ?", (voiture_id,))

        self.conn.commit()

        details = f"Location ID: {location_id}\nVoiture: {self.location_voiture_combo.currentText()}\nClient: {client_name}\nDate: {date_location}\nJours: {jours}\nCoût Total: {cout_total:.2f} DA"
        self.cursor.execute("UPDATE factures SET details = ? WHERE location_id = ?", (details, location_id))
        self.conn.commit()

        # ← CRITIQUE : REMETTRE EN MODE AJOUT APRÈS SUCCÈS
        self.clear_location_form()
        
        # ← REMETTRE LE TEXTE DU BOUTON À "CRÉER LA LOCATION"
        self.location_add_btn.setText("CRÉER LA LOCATION")
        
        # ← DÉCONNECTER update_location ET RECONNECTER add_location
        try:
            self.location_add_btn.clicked.disconnect()
        except TypeError:
            pass
        self.location_add_btn.clicked.connect(self.add_location)
        
        # ← CACHER LE BOUTON ANNULER
        self.location_cancel_btn.setVisible(False)
        
        # ← RÉINITIALISER L'ID D'ÉDITION
        self.current_edit_id = None

        # ← RECHARGER TOUT
        self.load_locations()
        self.load_voitures()
        self.load_factures()
        self.load_voitures_combo(self.location_voiture_combo)

        QMessageBox.information(self, "Succès", "Location mise à jour avec succès.")


    def delete_location(self, location_id):
        reply = QMessageBox.question(self, "Confirmer", "Voulez-vous supprimer cette location ?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cursor.execute("SELECT voiture_id FROM locations WHERE id = ?", (location_id,))
            voiture_id = self.cursor.fetchone()[0]
            self.cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            self.cursor.execute("DELETE FROM factures WHERE location_id = ?", (location_id,))
            self.cursor.execute("UPDATE voitures SET statut = 'Disponible' WHERE id = ?", (voiture_id,))
            self.conn.commit()
            self.load_locations()
            self.load_voitures()
            self.load_factures()



    def clear_location_form(self):
        self.location_voiture_combo.setCurrentIndex(0)
        self.location_client_input.clear()
        self.location_client2_input.clear()
        self.location_date_input.setDate(QDate.currentDate())
        self.location_time_input.setTime(QTime.currentTime())  # ← AJOUT reset heure
        self.location_jours_input.clear()
        self.location_promotion_input.clear()
        self.location_fuel_combo.setCurrentIndex(0)
        self.location_km_depart.clear()
        for group in self.accessories_groups.values():
            group.setExclusive(False)
            group.button(1).setChecked(False)
            group.button(0).setChecked(False)
            group.setExclusive(True)
    
    
    def setup_reservations_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(18)

        # ================== TITRE ==================
        title = QLabel("Gestion des Réservations")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#111827; margin-bottom:10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== SECTION HAUT – FORMULAIRE + CALENDRIER (40% HEIGHT) ==================
        top_section = QWidget()
        top_section.setStyleSheet("""
            background:white; 
            border-radius:16px; 
            padding:20px; 
            box-shadow: 0 6px 16px rgba(0,0,0,0.07);
        """)
        top_section.setMaximumHeight(int(self.height() * 0.40))

        top_layout = QHBoxLayout(top_section)
        top_layout.setSpacing(20)

        # --- FORMULAIRE GAUCHE (COMPACT) ---
        form_widget = QWidget()
        form_widget.setStyleSheet("background:transparent;")
        form_layout = QGridLayout(form_widget)
        form_layout.setColumnStretch(1, 1)
        form_layout.setVerticalSpacing(18)
        form_layout.setHorizontalSpacing(18)

        labels = [
            "Voiture :", "Client :", "Date début :", "Jours :", "Montant payé (DA) :"
        ]

        self.res_voiture_combo = QComboBox()
        self.res_client_input = QLineEdit()

            # === DATE (LECTURE SEULE + BOUTON POPUP) ===
        self.res_date_input = QDateEdit()
        self.res_date_input.setDate(QDate.currentDate())
        self.res_date_input.setVisible(False)  # ← MASQUÉ

        date_btn = QPushButton("📅")
        date_btn.setFixedSize(self.scale(25), self.scale(25))
        date_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 14px;
            }
        """)
        date_btn.clicked.connect(self.open_date_picker_reservation)

        self.res_date_label = QLabel(QDate.currentDate().toString("dd/MM/yyyy"))
        self.res_date_label.setStyleSheet("""
            font-weight:600;
            font-size:14px; 
            color:#1e40af; 
            background:#f0f9ff;
            border:2px solid #3b82f6;
            border-radius:12px;
            padding:16px 24px;
        """)
        self.res_date_label.setAlignment(Qt.AlignCenter)

        date_widget = QWidget()
        date_widget.setStyleSheet("background:transparent;")
        date_h = QHBoxLayout(date_widget)
        date_h.setContentsMargins(0, 0, 0, 0)
        date_h.setSpacing(12)
        date_h.addWidget(self.res_date_label)  # ← LABEL EN PREMIER
        date_h.addWidget(date_btn) 

        self.res_jours_input = QLineEdit()
        self.res_jours_input.setPlaceholderText("ex: 5")
        
        self.res_payment_input = QLineEdit()
        self.res_payment_input.setPlaceholderText("ex: 5000")

        widgets = [
            self.res_voiture_combo,
            self.res_client_input,
            date_widget,
            self.res_jours_input,
            self.res_payment_input
        ]
            # Initialisation
        self.load_voitures_combo(self.res_voiture_combo)
            
        self.res_client_completer = QCompleter()
        self.res_client_input.setCompleter(self.res_client_completer)
        self.load_clients_completer(self.res_client_completer)

        # STYLE DES CHAMPS (COMPACT)
        input_style = """
            QLineEdit, QComboBox {
                border:1px solid #d1d5db;
                border-radius:6px;
                padding: 20px;
                font-size:18px;
                background:#ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border:2px solid #3b82f6;
            }
        """
        
        for w in widgets:
            if w is not date_widget:
                w.setStyleSheet(input_style)

        self.res_date_input.setStyleSheet("""
            QDateEdit {
                color:#1e293b;
                background:#ffffff;
                border:1px solid #d1d5db;
                padding:20px;
                font-size:18px;
                border-radius:6px;
            }
            QDateEdit:focus { border:2px solid #3b82f6; }
            QCalendarWidget {
                background-color: white;
            }
            QCalendarWidget QWidget {
                background-color: white;
            }
            QCalendarWidget QAbstractItemView {
                background-color: white;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QCalendarWidget QToolButton {
                background-color: white;
                color: #1e293b;
            }
        """)

        # LABELS (COMPACT)
        for i, (lbl_text, widget) in enumerate(zip(labels, widgets)):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("font-weight:600; color:#374151; font-size:18px;")
            form_layout.addWidget(lbl, i, 0)
            form_layout.addWidget(widget, i, 1)

        # ← FIXED: TOTAL LABEL WITH PROPER STYLING LIKE OTHER DISPLAY LABELS
        total_lbl = QLabel("Total à payer :")
        total_lbl.setStyleSheet("font-weight:600; color:#374151; font-size:18px;")
        
        self.res_total_label = QLabel("0 DA")
        self.res_total_label.setStyleSheet("""
            font-weight:600;
            font-size:18px; 
            color:#059669; 
            background:#ffffff;
            border:1px solid #d1d5db;
            border-radius:6px;
            padding:20px;
        """)
        self.res_total_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        form_layout.addWidget(total_lbl, len(widgets), 0)
        form_layout.addWidget(self.res_total_label, len(widgets), 1)

        # ← CONNECTER LES CHANGEMENTS POUR CALCUL EN TEMPS RÉEL
        self.res_voiture_combo.currentIndexChanged.connect(self.calculate_reservation_total)
        self.res_jours_input.textChanged.connect(self.calculate_reservation_total)

        # ================== BOUTONS (COMPACT) ==================
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addStretch()

        self.res_add_btn = QPushButton("CRÉER LA RÉSERVATION")
        self.res_add_btn.setStyleSheet("""
            background:#059669; color:white; font-weight:bold;
            padding: 20px; border-radius:8px; font-size:14px;
        """)
        self.res_add_btn.setCursor(Qt.PointingHandCursor)
        self.res_add_btn.clicked.connect(self.add_reservation)

        self.res_cancel_btn = QPushButton("ANNULER")
        self.res_cancel_btn.setStyleSheet("""
            background:#ef4444; color:white; font-weight:bold;
            padding: 20px; border-radius:8px; font-size:14px;
        """)
        self.res_cancel_btn.setCursor(Qt.PointingHandCursor)
        self.res_cancel_btn.clicked.connect(self.cancel_edit_reservation)
        self.res_cancel_btn.setVisible(False)

        self.buttons_layout.addWidget(self.res_add_btn)
        self.buttons_layout.addSpacing(10)
        self.buttons_layout.addWidget(self.res_cancel_btn)
        self.buttons_layout.addStretch()

        # ← AJOUTER LES BOUTONS APRÈS LE LABEL TOTAL
        form_layout.addLayout(self.buttons_layout, len(widgets) + 1, 0, 1, 2)

        top_layout.addWidget(form_widget, 3)

        # --- CALENDRIER À DROITE (COMPACT) ---
        cal_box = QWidget()
        cal_box.setStyleSheet("background:#f9fafb; border-radius:10px; padding:10px; border:1px solid #e5e7eb;")
        cal_layout = QVBoxLayout(cal_box)
        cal_layout.setSpacing(6)
        
        title_cal = QLabel("Calendrier des Réservations")
        title_cal.setStyleSheet("font-size:14px; font-weight:700; color:#1e40af;")
        cal_layout.addWidget(title_cal)

        self.reservation_calendar = QCalendarWidget()
        self.reservation_calendar.setGridVisible(True)
        self.reservation_calendar.clicked.connect(self.show_reservations_date)
        self.reservation_calendar.setStyleSheet("""
            QCalendarWidget { background:white; border-radius:8px; font-size:13px; }
            QCalendarWidget QToolButton { color:#000000; font-weight:bold; padding:4px; }
        """)
        cal_layout.addWidget(self.reservation_calendar)
        top_layout.addWidget(cal_box, 2)

        layout.addWidget(top_section)

        # ================== RECHERCHE ==================
        layout.addWidget(QLabel("Historique des Réservations", 
            styleSheet="font-size:18px; font-weight:700; color:#111827; margin:15px 0 8px 0;"))

        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Rechercher par matricule, modèle ou client...")
        search_bar.setStyleSheet("""
            QLineEdit {
                padding:12px 16px;
                font-size:15px;
                border:1px solid #d1d5db;
                border-radius:12px;
                background:#f9fafb;
            }
            QLineEdit:focus { border:2px solid #3b82f6; }
        """)
        search_bar.textChanged.connect(self.filter_reservations)
        self.reservation_search = search_bar
        layout.addWidget(search_bar)

        # ================== TABLEAU (60%) ==================
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.reservation_table = QTableWidget()
        self.reservation_table.setColumnCount(8)
        self.reservation_table.setHorizontalHeaderLabels([
            "Matricule", "Modèle", "Client", "Début", "Jours", "Total", "Payé %", "Actions"
        ])

        self.reservation_table.setStyleSheet("""
            QTableWidget {
                background:white; border:1px solid #e2e8f0; border-radius:16px; font-size:18px;
                gridline-color:#f1f5f9;
            }
            QHeaderView::section {
                background:#1e40af; color:white; padding:12px; font-weight:bold; font-size:18px;
            }
        """)

        self.reservation_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.reservation_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.reservation_table.verticalHeader().setDefaultSectionSize(60)
        self.reservation_table.setAlternatingRowColors(True)
        self.reservation_table.setSelectionBehavior(QTableWidget.SelectRows)

        header = self.reservation_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed); self.reservation_table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.Fixed); self.reservation_table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed); self.reservation_table.setColumnWidth(5, 110)
        header.setSectionResizeMode(6, QHeaderView.Fixed); self.reservation_table.setColumnWidth(6, 100)
        header.setSectionResizeMode(7, QHeaderView.Fixed); self.reservation_table.setColumnWidth(7, 460)

        table_layout.addWidget(self.reservation_table)
        layout.addWidget(table_container, 1)

        # ================== FINAL ==================
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        
        self.setMinimumSize(self.scale(800), self.scale(600))

        if self.content_stack.count() > 4:
            old = self.content_stack.widget(4)
            self.content_stack.removeWidget(old)
            old.deleteLater()
        
        self.content_stack.insertWidget(4, scroll)
        self.content_stack.setCurrentIndex(4)

        self.update_available_cars()
        self.load_reservations()
        
        # ← Force calculation after everything is loaded
        QTimer.singleShot(100, self.calculate_reservation_total)

    # ========== NOUVELLE FONCTION POUR RÉSERVATION ==========
    def open_date_picker_reservation(self):
        """Ouvre le sélecteur de date pour la réservation"""
        current = self.res_date_input.date()
        
        dialog = DatePickerDialog(current, self)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_date()
            self.res_date_input.setDate(selected)
            self.res_date_label.setText(selected.toString("dd/MM/yyyy"))
            self.update_available_cars()  # Recharger les voitures disponibles
            print(f"✅ Date selected: {selected.toString('dd/MM/yyyy')}")

    def calculate_reservation_total(self):
        """Calcule et affiche le total de la réservation en temps réel"""
        print("calculate_reservation_total() called")
        try:
            voiture_id = self.res_voiture_combo.currentData()
            print(f"Selected voiture_id: {voiture_id}")

            jours_text = self.res_jours_input.text().strip()

            if not voiture_id or not jours_text:
                self.res_total_label.setText("0 DA")
                self.res_total_label.setStyleSheet("font-size:18px; font-weight:bold; color:#6b7280;")
                return

            try:
                jours = int(jours_text)
                if jours <= 0:
                    self.res_total_label.setText("0 DA")
                    self.res_total_label.setStyleSheet("font-size:18px; font-weight:bold; color:#dc2626;")
                    return
            except ValueError:
                self.res_total_label.setText("-- DA")
                self.res_total_label.setStyleSheet("font-size:18px; font-weight:bold; color:#dc2626;")
                return

            self.cursor.execute("SELECT prix_jour FROM voitures WHERE id = ?", (voiture_id,))
            result = self.cursor.fetchone()

            if result:
                prix_jour = result[0]
                total = jours * prix_jour

                # ← THE FIX: Use normal space instead of comma/non-breaking space
                total_str = f"{total:,.0f}".replace(",", " ").replace("\u00a0", " ")
                # or simply:
                # total_str = f"{int(total): } DA"  # but better with grouping

                self.res_total_label.setText(f"{total_str} DA")
                self.res_total_label.setStyleSheet("font-size:18px; font-weight:bold; color:#059669;")
                print(f"Total displayed: {total_str} DA")
            else:
                self.res_total_label.setText("0 DA")
                self.res_total_label.setStyleSheet("font-size:18px; font-weight:bold; color:#6b7280;")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.res_total_label.setText("Erreur")

    def cancel_edit_reservation(self):
            """Annule le mode édition et remet le formulaire en mode ajout"""
            self.clear_reservation_form()
            
            self.res_add_btn.setText("CRÉER LA RÉSERVATION")
            self.res_add_btn.clicked.disconnect()
            self.res_add_btn.clicked.connect(self.add_reservation)
            
            self.res_cancel_btn.setVisible(False)
            
            self.update_available_cars()


    def update_available_cars(self):
        """Pour la page réservation : mise à jour des voitures disponibles"""
        self.res_voiture_combo.clear()
        selected_date = self.res_date_input.date().toString("yyyy-MM-dd")
        end_date = (self.res_date_input.date().addDays(7)).toString("yyyy-MM-dd")

        query = """
            SELECT v.id, v.numero_matricule || ' - ' || v.modele || ' (' || v.statut || ')'
            FROM voitures v
            WHERE v.id NOT IN (
                SELECT voiture_id FROM locations 
                WHERE statut = 'Active'
                AND NOT (date_heure_location > ? OR date(date_heure_location, '+' || jours || ' days') < ?)
            )
            AND v.id NOT IN (
                SELECT voiture_id FROM reservations 
                WHERE statut = 'Active'
                AND NOT (date_debut > ? OR date(date_debut, '+' || jours || ' days') < ?)
            )
        """
        self.cursor.execute(query, (end_date, selected_date, end_date, selected_date))
        for car_id, text in self.cursor.fetchall():
            self.res_voiture_combo.addItem(text, car_id)

    def load_reservations(self, filter_text=""):
        self.reservation_table.setRowCount(0)
        
        query = """
            SELECT r.id, v.numero_matricule, v.modele, 
                c.nom || ' ' || c.prenom, r.date_debut, r.jours, 
                r.cout_total, r.payment_percentage
            FROM reservations r
            JOIN voitures v ON r.voiture_id = v.id
            JOIN clients c ON r.client_id = c.id
            WHERE r.statut = 'Active'
        """
        params = []
        if filter_text:
            query += " AND (v.numero_matricule LIKE ? OR v.modele LIKE ? OR c.nom LIKE ? OR c.prenom LIKE ?)"
            search = f"%{filter_text}%"
            params = [search, search, search, search]

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        self.reservation_table.setRowCount(len(rows))

        for row_idx, (res_id, matricule, modele, client, date_debut, jours, total, paye_percent) in enumerate(rows):
            self.reservation_table.setItem(row_idx, 0, QTableWidgetItem(matricule))
            self.reservation_table.setItem(row_idx, 1, QTableWidgetItem(modele))
            self.reservation_table.setItem(row_idx, 2, QTableWidgetItem(client))
            self.reservation_table.setItem(row_idx, 3, QTableWidgetItem(date_debut))
            self.reservation_table.setItem(row_idx, 4, QTableWidgetItem(str(jours)))
            self.reservation_table.setItem(row_idx, 5, QTableWidgetItem(f"{total:,.0f} DA"))
            
            montant_paye = total * paye_percent / 100
            self.reservation_table.setItem(row_idx, 6, QTableWidgetItem(f"{montant_paye:,.0f} DA"))

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(12, 8, 12, 8)
            actions_layout.setSpacing(12)

            print_btn = QPushButton("Imprimer")
            print_btn.setStyleSheet("background:#10b981; color:white;")
            print_btn.clicked.connect(lambda _, rid=res_id: self.print_reservation_contract(rid))

            details_btn = QPushButton("Détails")
            details_btn.setStyleSheet("background:#3b82f6; color:white;")
            details_btn.clicked.connect(lambda _, rid=res_id: self.show_reservation_details(rid))

            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet("background:#f59e0b; color:white;")
            edit_btn.clicked.connect(lambda _, rid=res_id: self.edit_reservation(rid))

            delete_btn = QPushButton("Supprimer")
            delete_btn.setStyleSheet("background:#ef4444; color:white;")
            delete_btn.clicked.connect(lambda _, rid=res_id: self.delete_reservation(rid))

            actions_layout.addWidget(print_btn)
            actions_layout.addWidget(details_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)

            self.reservation_table.setCellWidget(row_idx, 7, actions)


    def filter_reservations(self):
        text = self.reservation_search.text().strip()
        self.load_reservations(text)

    def delete_selected_reservations(self):
        selected_ids = []
        for i in range(self.reservation_table.rowCount()):
            check_widget = self.reservation_table.cellWidget(i, 0)
            check = check_widget.layout().itemAt(0).widget()
            if check.isChecked():
                rid = int(self.reservation_table.item(i, 1).text())
                selected_ids.append(rid)
        if selected_ids:
            reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_selection"],
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for rid in selected_ids:
                    self.cursor.execute("DELETE FROM reservations WHERE id = ?", (rid,))
                self.conn.commit()
                self.load_reservations()

    def show_reservation_details(self, reservation_id):
        self.cursor.execute("""
            SELECT v.modele, c.nom || ' ' || c.prenom, r.date_debut, r.jours, r.cout_total, r.payment_percentage, r.statut
            FROM reservations r
            JOIN voitures v ON r.voiture_id = v.id
            JOIN clients c ON r.client_id = c.id
            WHERE r.id = ?
        """, (reservation_id,))
        reservation = self.cursor.fetchone()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.translations['fr']['details']} Réservation ID {reservation_id}")
        layout = QVBoxLayout(dialog)
        labels = [
            self.translations['fr']["modele"],
            self.translations['fr']["client"],
            self.translations['fr']["date_location"],
            self.translations['fr']["jours"],
            self.translations['fr']["cout_total"],
            self.translations['fr']["payment_percentage"],
            self.translations['fr']["statut"]
        ]
        for label, value in zip(labels, reservation):
            layout.addWidget(QLabel(f"{label} {value}"))
        close_btn = QPushButton(self.translations['fr']["fermer"])
        close_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; border-radius: 5px;")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dialog.resize(600, 400)
        dialog.exec_()


    def add_reservation(self):
        voiture_id = self.res_voiture_combo.currentData()
        client_name = self.res_client_input.text().strip()
        client_id = self.get_client_id(client_name)
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Client non trouvé.")
            return

        self.cursor.execute("SELECT date_expiration_permis FROM clients WHERE id = ?", (client_id,))
        exp_row = self.cursor.fetchone()
        if exp_row and exp_row[0]:
            try:
                exp_date = datetime.strptime(exp_row[0], "%Y-%m-%d").date()
                if exp_date < date.today():
                    QMessageBox.warning(self, "Permis expiré", 
                        "Le permis de conduire du client est expiré.\nImpossible de créer la réservation.")
                    return
            except:
                pass

        date_debut = self.res_date_input.date().toString("yyyy-MM-dd")
        if not (voiture_id and client_id):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une voiture et un client.")
            return
        if self.res_date_input.date() < QDate.currentDate():
            QMessageBox.warning(self, "Erreur", "La date de début ne peut pas être dans le passé.")
            return
        
        try:
            jours = int(self.res_jours_input.text())
            if jours <= 0:
                raise ValueError("Le nombre de jours doit être positif.")
            
            montant_paye = float(self.res_payment_input.text() or 0)
            if montant_paye < 0:
                raise ValueError("Le montant payé doit être positif.")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return

        end_date = (datetime.strptime(date_debut, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")

        self.cursor.execute("""
            SELECT id FROM locations
            WHERE voiture_id = ? AND statut = 'Active'
            AND NOT (date_heure_location > ? OR date(date_heure_location, '+' || jours || ' days') < ?)
        """, (voiture_id, end_date, date_debut))
        if self.cursor.fetchone():
            QMessageBox.warning(self, "Erreur", "Voiture non disponible pour cette période (conflit avec une location existante).")
            return

        self.cursor.execute("""
            SELECT id FROM reservations
            WHERE voiture_id = ? AND statut = 'Active'
            AND NOT (date_debut > ? OR date(date_debut, '+' || jours || ' days') < ?)
        """, (voiture_id, end_date, date_debut))
        if self.cursor.fetchone():
            QMessageBox.warning(self, "Erreur", "Voiture non disponible pour cette période (conflit avec une réservation existante).")
            return

        self.cursor.execute("SELECT prix_jour FROM voitures WHERE id = ?", (voiture_id,))
        prix_jour = self.cursor.fetchone()[0]
        cout_total = jours * prix_jour

        payment_percentage = (montant_paye / cout_total * 100) if cout_total > 0 else 0

        try:
            self.cursor.execute("""
                INSERT INTO reservations (voiture_id, client_id, date_debut, jours, cout_total, payment_percentage, statut)
                VALUES (?, ?, ?, ?, ?, ?, 'Active')
            """, (voiture_id, client_id, date_debut, jours, cout_total, payment_percentage))
            
            self.cursor.execute("UPDATE voitures SET statut = 'Réservée' WHERE id = ?", (voiture_id,))
            self.conn.commit()
            
            self.load_reservations()
            self.load_voitures()
            self.clear_reservation_form()
            
            QMessageBox.information(self, "Succès", 
                f"Réservation ajoutée avec succès !\n\n"
                f"Coût total : {cout_total:,.0f} DA\n"
                f"Montant payé : {montant_paye:,.0f} DA\n"
                f"Reste à payer : {cout_total - montant_paye:,.0f} DA")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de base de données: {e}")


    def edit_reservation(self, reservation_id):
        self.cursor.execute("""
            SELECT voiture_id, client_id, date_debut, jours, cout_total, payment_percentage 
            FROM reservations WHERE id = ?
        """, (reservation_id,))
        data = self.cursor.fetchone()
        
        if data:
            voiture_id, client_id, date_debut, jours, cout_total, payment_percentage = data
            
            self.res_voiture_combo.setCurrentIndex(self.res_voiture_combo.findData(voiture_id))
            
            self.cursor.execute("SELECT nom || ' ' || prenom FROM clients WHERE id = ?", (client_id,))
            client_name = self.cursor.fetchone()[0]
            self.res_client_input.setText(client_name)
            
            self.res_date_input.setDate(QDate.fromString(date_debut, "yyyy-MM-dd"))
            self.res_jours_input.setText(str(jours))
            
            montant_paye = cout_total * payment_percentage / 100
            self.res_payment_input.setText(f"{montant_paye:.0f}")

            self.current_edit_id = reservation_id
            self.switch_to_edit_mode()
            self.update_car_statuses()
            self.load_reservations()
            self.load_voitures()

    def update_reservation(self, reservation_id):
        voiture_id = self.res_voiture_combo.currentData()
        client_name = self.res_client_input.text().strip()
        client_id = self.get_client_id(client_name)
        
        if not client_id:
            QMessageBox.warning(self, "Erreur", "Client non trouvé.")
            return
            
        date_debut = self.res_date_input.date().toString("yyyy-MM-dd")
        
        if not (voiture_id and client_id):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une voiture et un client.")
            return
            
        if self.res_date_input.date() < QDate.currentDate():
            QMessageBox.warning(self, "Erreur", "La date de début ne peut pas être dans le passé.")
            return
        
        try:
            jours = int(self.res_jours_input.text())
            if jours <= 0:
                raise ValueError("Le nombre de jours doit être positif.")
            
            montant_paye = float(self.res_payment_input.text() or 0)
            if montant_paye < 0:
                raise ValueError("Le montant payé doit être positif.")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return
        
        end_date = (datetime.strptime(date_debut, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")
        
        self.cursor.execute("""
            SELECT id FROM locations
            WHERE voiture_id = ? AND statut = 'Active'
            AND NOT (date_heure_location > ? OR date(date_heure_location, '+' || jours || ' days') < ?)
        """, (voiture_id, end_date, date_debut))
        if self.cursor.fetchone():
            QMessageBox.warning(self, "Erreur", "Voiture non disponible (conflit avec une location).")
            return
        
        self.cursor.execute("""
            SELECT id FROM reservations
            WHERE voiture_id = ? AND statut = 'Active' AND id != ?
            AND NOT (date_debut > ? OR date(date_debut, '+' || jours || ' days') < ?)
        """, (voiture_id, reservation_id, end_date, date_debut))
        if self.cursor.fetchone():
            QMessageBox.warning(self, "Erreur", "Voiture non disponible (conflit avec une réservation).")
            return
        
        self.cursor.execute("SELECT voiture_id FROM reservations WHERE id = ?", (reservation_id,))
        old_voiture_id = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT prix_jour FROM voitures WHERE id = ?", (voiture_id,))
        prix_jour = self.cursor.fetchone()[0]
        cout_total = jours * prix_jour
        
        payment_percentage = (montant_paye / cout_total * 100) if cout_total > 0 else 0
        
        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            self.cursor.execute("""
                UPDATE reservations 
                SET voiture_id = ?, client_id = ?, date_debut = ?, jours = ?, 
                    cout_total = ?, payment_percentage = ?
                WHERE id = ?
            """, (voiture_id, client_id, date_debut, jours, cout_total, payment_percentage, reservation_id))
            
            self.cursor.execute("UPDATE voitures SET statut = 'Réservée' WHERE id = ?", (voiture_id,))
            
            self.cursor.execute("""
                SELECT 1 FROM reservations 
                WHERE voiture_id = ? AND statut = 'Active' AND id != ?
                LIMIT 1
            """, (old_voiture_id, reservation_id))
            reservation_exists = self.cursor.fetchone()
            
            self.cursor.execute("""
                SELECT 1 FROM locations 
                WHERE voiture_id = ? AND statut = 'Active'
                LIMIT 1
            """, (old_voiture_id,))
            location_exists = self.cursor.fetchone()
            
            if not (reservation_exists or location_exists):
                self.cursor.execute("UPDATE voitures SET statut = 'Disponible' WHERE id = ?", (old_voiture_id,))
            
            self.conn.commit()
            
            self.load_reservations()
            self.load_voitures()
            self.clear_reservation_form()
            
            self.res_add_btn.setText("CRÉER LA RÉSERVATION")
            self.res_add_btn.clicked.disconnect()
            self.res_add_btn.clicked.connect(self.add_reservation)
            self.res_cancel_btn.setVisible(False)
            
            QMessageBox.information(self, "Succès", 
                f"Réservation mise à jour !\n\n"
                f"Coût total : {cout_total:,.0f} DA\n"
                f"Montant payé : {montant_paye:,.0f} DA\n"
                f"Reste à payer : {cout_total - montant_paye:,.0f} DA")
        except sqlite3.Error as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur de base de données: {e}")


    def delete_reservation(self, reservation_id):
        reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_reservation"],
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cursor.execute("SELECT voiture_id FROM reservations WHERE id = ?", (reservation_id,))
            voiture_id = self.cursor.fetchone()[0]
            self.cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
            self.cursor.execute("UPDATE voitures SET statut = 'Disponible' WHERE id = ?", (voiture_id,))
            self.conn.commit()
            self.load_reservations()
            self.load_voitures()

    def clear_reservation_form(self):
        self.res_voiture_combo.setCurrentIndex(0)
        self.res_client_input.clear()
        self.res_date_input.setDate(QDate.currentDate())
        self.res_jours_input.clear()
        self.res_payment_input.clear()
        self.res_total_label.setText("Total : 0 DA")

    def show_reservations_date(self, date):
        selected_date = date.toString("yyyy-MM-dd")
        self.cursor.execute("""
            SELECT r.id, v.numero_matricule, v.modele, c.nom || ' ' || c.prenom, r.cout_total, r.payment_percentage
            FROM reservations r
            JOIN voitures v ON r.voiture_id = v.id
            JOIN clients c ON r.client_id = c.id
            WHERE r.date_debut = ?
            AND r.statut = 'Active'
        """, (selected_date,))
        rows = self.cursor.fetchall()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.translations['fr']['calendrier_reservations']} {selected_date}")
        layout = QVBoxLayout(dialog)
        if not rows:
            layout.addWidget(QLabel(self.translations['fr']["aucune_reservation"], styleSheet="color: #2C3E50; font-size: 14px;"))
        else:
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                self.translations['fr']["id_reservation"],
                self.translations['fr']["matricule"],
                self.translations['fr']["modele"],
                self.translations['fr']["client"],
                self.translations['fr']["cout_total"],
                self.translations['fr']["payment_percentage"]
            ])
            table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #e5e7eb;
                    border-radius: 5px;
                    font-size: 14px;
                    background-color: #f9fafb;
                }
                QHeaderView::section {
                    background-color: #3498DB;
                    color: white;
                    padding: 10px;
                    font-weight: bold;
                }
            """)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.verticalHeader().setDefaultSectionSize(50)
            table.setRowCount(len(rows))
            for i, (res_id, matricule, modele, client, cout_total, payment_percentage) in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(res_id)))
                table.setItem(i, 1, QTableWidgetItem(matricule))
                table.setItem(i, 2, QTableWidgetItem(modele))
                table.setItem(i, 3, QTableWidgetItem(client))
                table.setItem(i, 4, QTableWidgetItem(f"{cout_total:.2f}"))
                table.setItem(i, 5, QTableWidgetItem(str(payment_percentage)))
            layout.addWidget(table, 1)
        close_btn = QPushButton(self.translations['fr']["fermer"])
        close_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; border-radius: 5px;")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dialog.resize(600, 400)
        dialog.exec_()


    def switch_to_edit_mode(self):
        self.res_add_btn.setText("MODIFIER")
        self.res_add_btn.clicked.disconnect()
        self.res_add_btn.clicked.connect(lambda: self.update_reservation(self.current_edit_id))
        self.res_cancel_btn.setVisible(True)


    def print_reservation_contract(self, reservation_id):
        try:
            # Récupération des données (SANS brand ni CIN)
            self.cursor.execute("""
                SELECT v.numero_matricule, v.modele,
                    c.nom, c.prenom, 
                    COALESCE(c.telephone, 'Non renseigné') AS telephone,
                    r.date_debut, r.jours, r.cout_total, r.payment_percentage
                FROM reservations r
                JOIN voitures v ON r.voiture_id = v.id
                JOIN clients c ON r.client_id = c.id
                WHERE r.id = ?
            """, (reservation_id,))
            
            row = self.cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Réservation non trouvée.")
                return

            matricule, modele, nom, prenom, telephone, date_debut, jours, total, paye_percent = row

            # ← CALCUL MONTANT PAYÉ EN DA
            montant_paye = total * paye_percent / 100
            reste = total - montant_paye

            # Calcul date de fin
            date_fin_qt = QDate.fromString(date_debut, "yyyy-MM-dd").addDays(jours - 1)
            date_fin = date_fin_qt.toString("dd/MM/yyyy")

            # HTML du contrat (adapté avec montants en DA)
            html = f"""
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>عقد حجز سيارة - LOCATOP</title>
                <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{ 
                        font-family: 'Cairo', sans-serif; 
                        direction: rtl; 
                        color: #000 !important; 
                        background: white; 
                        line-height: 1.3; 
                        padding: 0; margin: 0; 
                    }}
                    .print-btn {{ 
                        position: fixed; top: 10px; right: 10px; 
                        background: #004080; color: white; 
                        padding: 8px 16px; border: none; border-radius: 4px; 
                        cursor: pointer; font-weight: bold; z-index: 1000; 
                    }}
                    @media print {{ .print-btn {{ display: none; }} }}

                    .page {{ 
                        width: 210mm; min-height: 297mm; 
                        padding: 8mm 10mm; margin: 0 auto; 
                        background: white; position: relative; 
                        font-size: 9pt;
                    }}

                    .header {{ text-align: center; padding-bottom: 4px; margin-bottom: 6px; border-bottom: 1.8px solid #004080; }}
                    .logo {{ font-size: 19pt; font-weight: 800; color: #004080; }}
                    .main-title {{ font-size: 13pt; font-weight: bold; margin: 4px 0; }}
                    .agency-info {{ font-size: 8.2pt; display: flex; justify-content: space-between; margin: 2px 0; }}
                    .contract-number {{ 
                        text-align: center; font-size: 11.5pt; font-weight: bold; 
                        color: #004080; background: #e9ecef; padding: 5px; 
                        border: 1.2px solid #ced4da; border-radius: 4px; margin: 10px 0;
                    }}

                    table {{ 
                        width: 100% !important; 
                        border-collapse: collapse; 
                        margin: 8px 0; 
                        font-size: 9.2pt;
                    }}
                    th, td {{ 
                        border: 1.3px solid #004080; 
                        padding: 6px 8px; 
                        text-align: center; 
                        background: #f8fcff;
                    }}
                    th {{ background: #e3f2fd !important; font-weight: bold; color: #004080; }}

                    .note-box {{ 
                        background: #fff8e6; border: 2.5px solid #ff9800; 
                        padding: 12px; border-radius: 8px; margin: 14px 0; 
                        font-size: 10.8pt; text-align: center; font-weight: bold; color: #e65100;
                    }}

                    .signatures-container {{
                        position: absolute;
                        bottom: 18mm;
                        left: 12mm;
                        right: 12mm;
                        border-top: 2.5px solid #004080;
                        padding-top: 22px;
                        display: flex;
                        justify-content: space-between;
                        align-items: flex-end;
                    }}
                    .sig-left {{
                        width: 45%;
                        text-align: center;
                    }}
                    .sig-label {{
                        font-weight: bold;
                        font-size: 11pt;
                        color: #004080;
                        margin-bottom: 8px;
                    }}
                    .sig-underline {{
                        border-top: 2px solid #004080;
                        width: 100%;
                        margin-top: 28px;
                        padding-top: 6px;
                        font-size: 10pt;
                        min-height: 30px;
                    }}
                </style>
            </head>
            <body>
                <button class="print-btn" onclick="window.print()">طباعة</button>

                <div class="page">
                    <div class="header">
                        <div class="logo">LOCATOP</div>
                        <div class="main-title">عقد حجز سيارة</div>
                        <div class="agency-info">
                            <span>**عيساوي عبد القادر** - 05 تجمع 30 الخريبة ندرومة</span>
                            <span>**ر.س**: <strong>11 / 1365901 _ 13/00</strong></span>
                        </div>
                        <div class="agency-info">
                            <span>الهاتف: <strong>0775.86.87.65</strong></span>
                            <span>رات: <strong>198313400077917</strong></span>
                            <span>ت.ج: <strong>0557.46.11.65</strong></span>
                        </div>
                    </div>

                    <div class="contract-number">عقد حجز رقم : <strong>RES-{reservation_id:04d}</strong></div>

                    <h3 style="text-align:center; color:#004080; margin:15px 0;">معلومات العميل والحجز</h3>
                    
                    <table>
                        <tr>
                            <th>الاسم الكامل</th>
                            <th>رقم الهاتف</th>
                        </tr>
                        <tr>
                            <td><strong>{nom} {prenom}</strong></td>
                            <td>{telephone}</td>
                        </tr>
                    </table>

                    <h3 style="text-align:center; color:#004080; margin:15px 0 8px;">فترة الحجز والجانب المالي</h3>
                    <table>
                        <tr>
                            <th>السيارة</th>
                            <th>من تاريخ</th>
                            <th>إلى تاريخ</th>
                            <th>عدد الأيام</th>
                            <th>المبلغ الإجمالي</th>
                            <th>الدفعة المقدمة</th>
                            <th>المتبقي</th>
                        </tr>
                        <tr>
                            <td><strong>{modele}<br>{matricule}</strong></td>
                            <td>{date_debut}</td>
                            <td>{date_fin}</td>
                            <td><strong>{jours}</strong></td>
                            <td><strong>{total:,.0f} دج</strong></td>
                            <td style="background:#e8f5e8;">{montant_paye:,.0f} دج</td>
                            <td style="background:#ffebee;color:#d32f2f;font-weight:bold;">
                                {reste:,.0f} دج
                            </td>
                        </tr>
                    </table>

                    <div class="note-box">
                        الحجز نهائي بعد دفع الدفعة المقدمة • الإلغاء قبل 48 ساعة: خصم 50% • قبل 24 ساعة: خصم 100%
                    </div>

                    <div class="signatures-container">
                        <div class="sig-left">
                            <div class="sig-label">إمضاء المؤجر (الوكالة)</div>
                        </div>
                        <div class="sig-left">
                            <div class="sig-label">إمضاء العميل</div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            # Impression
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setFullPage(True)

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle("Aperçu - Contrat de Réservation")
            
            doc = QTextDocument()
            doc.setHtml(html)
            preview.paintRequested.connect(doc.print_)
            preview.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'imprimer le contrat :\n{str(e)}")


    def setup_frais_page(self):
            page = QWidget()
            scroll = QScrollArea()
            scroll.setWidget(page)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 30)
            layout.setSpacing(18)

            # ================== TITRE ==================
            title = QLabel("Gestion des Frais & Dépenses")
            title.setStyleSheet("font-size:26px; font-weight:800; color:#111827;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # ================== CARTES RÉSUMÉ ==================
            cards_widget = QWidget()
            cards_layout = QHBoxLayout(cards_widget)
            cards_layout.setSpacing(16)

            self.total_frais_label = QLabel("0.00 DA")
            self.total_faux_frais_label = QLabel("0.00 DA")
            self.total_general_frais_label = QLabel("0.00 DA")

            cards_data = [
                ("Total Frais", self.total_frais_label, "#dc2626"),
                ("Total Faux Frais", self.total_faux_frais_label, "#d97706"),
                ("Total Général", self.total_general_frais_label, "#7c3aed")
            ]

            for text, label, color in cards_data:
                card = QWidget()
                card.setFixedHeight(100)
                card.setStyleSheet(f"""
                    background:white;
                    border-radius:16px;
                    border-left:5px solid {color};
                    box-shadow: 0 6px 16px rgba(0,0,0,0.07);
                """)
                v = QVBoxLayout(card)
                v.setContentsMargins(18,16,18,16)
                v.addWidget(QLabel(text, styleSheet="color:#374151; font-size:14px; font-weight:600;"))
                v.addWidget(label)
                label.setStyleSheet(f"color:{color}; font-size:32px; font-weight:900;")
                label.setAlignment(Qt.AlignCenter)
                cards_layout.addWidget(card)

            layout.addWidget(cards_widget)

            # ================== RECHERCHE ==================
            search_bar = QLineEdit()
            search_bar.setPlaceholderText("Rechercher par type ou description...")
            search_bar.setStyleSheet("""
                QLineEdit {
                    padding:12px 16px;
                    font-size:15px;
                    border:1px solid #d1d5db;
                    border-radius:12px;
                    background:#f9fafb;
                }
                QLineEdit:focus { border:2px solid #3b82f6; }
            """)
            search_bar.textChanged.connect(self.load_frais)  # recherche en temps réel
            self.frais_search_input = search_bar
            layout.addWidget(search_bar)

            # ================== TABLEAU ==================
            self.frais_table = QTableWidget()
            self.frais_table.setColumnCount(6)
            self.frais_table.setHorizontalHeaderLabels(["ID", "Type", "Coût (DA)", "Date", "Description", "Actions"])

            self.frais_table.setStyleSheet("""
                QTableWidget {
                    background:white;
                    border:1px solid #e5e7eb;
                    border-radius:16px;
                    gridline-color:#f3f4f6;
                    font-size:18px;
                }
                QHeaderView::section {
                    background:#1e40af;
                    color:white;
                    padding:14px;
                    font-weight:bold;
                    font-size:18px;
                }
            """)

            self.frais_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.frais_table.verticalHeader().setDefaultSectionSize(60)
            self.frais_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.frais_table.setAlternatingRowColors(True)

            header = self.frais_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(4, QHeaderView.Stretch)
            self.frais_table.setColumnWidth(0, 80)
            self.frais_table.setColumnWidth(1, 150)
            self.frais_table.setColumnWidth(2, 120)
            self.frais_table.setColumnWidth(3, 150)
            self.frais_table.setColumnWidth(5, 220)

            layout.addWidget(self.frais_table, 1)

            # ================== BOUTON AJOUT ==================
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()

            add_btn = QPushButton("Nouveau Frais")
            add_btn.setStyleSheet("background:#1e40af; color:white; padding:12px 28px; border-radius:12px; font-weight:bold; font-size:18px;")
            add_btn.clicked.connect(lambda: self.frais_form.setVisible(not self.frais_form.isVisible()))
            btn_layout.addWidget(add_btn)
            layout.addLayout(btn_layout)

            # ================== FORMULAIRE AJOUT/MODIF (caché par défaut) ==================
            self.frais_form = QWidget()
            self.frais_form.setVisible(False)
            form_card = QWidget()
            form_card.setStyleSheet("background:white; border-radius:16px; padding:24px; box-shadow: 0 8px 25px rgba(0,0,0,0.08);")
            form_layout = QGridLayout(form_card)

            self.frais_type_combo = QComboBox()
            self.frais_type_combo.addItems(["Frais", "Faux Frais"])

            self.frais_cout_input = QLineEdit()
            self.frais_date_input = QDateEdit()
            self.frais_date_input.setCalendarPopup(True)
            self.frais_date_input.setDate(QDate.currentDate())

            self.frais_desc_input = QTextEdit()
            self.frais_desc_input.setFixedHeight(100)

            fields = [
                ("Type", self.frais_type_combo),
                ("Coût (DA)", self.frais_cout_input),
                ("Date", self.frais_date_input),
                ("Description", self.frais_desc_input),
            ]

            for i, (label_text, widget) in enumerate(fields):
                lbl = QLabel(label_text + " :")
                lbl.setStyleSheet("font-weight:600; color:#374151;")
                form_layout.addWidget(lbl, i, 0)
                widget.setStyleSheet("padding:10px; border:1px solid #d1d5db; border-radius:8px;")
                form_layout.addWidget(widget, i, 1)

            self.frais_save_btn = QPushButton("Enregistrer le Frais")
            self.frais_save_btn.setStyleSheet("background:#059669; color:white; padding:14px; border-radius:12px; font-weight:bold; font-size:15px;")
            self.frais_save_btn.clicked.connect(self.save_frais)
            form_layout.addWidget(self.frais_save_btn, len(fields), 0, 1, 2)

            self.frais_form.setLayout(QVBoxLayout())
            self.frais_form.layout().addWidget(form_card)
            layout.addWidget(self.frais_form)

            scroll.setWidget(page)
            self.content_stack.insertWidget(5, scroll)
            self.load_frais()  # charge au démarrage


    def load_frais(self):
        search = self.frais_search_input.text().lower() if hasattr(self, 'frais_search_input') and self.frais_search_input else ""

        query = """
            SELECT id, type, cost, date, description 
            FROM expenses
            WHERE (lower(type) LIKE ? OR lower(description) LIKE ?)
            ORDER BY date DESC, id DESC
        """
        params = (f"%{search}%", f"%{search}%")

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        self.frais_table.setRowCount(len(rows))

        for row_idx, (fid, ftype, cost, fdate, desc) in enumerate(rows):
            self.frais_table.setItem(row_idx, 0, QTableWidgetItem(str(fid)))
            self.frais_table.setItem(row_idx, 1, QTableWidgetItem(ftype))
            self.frais_table.setItem(row_idx, 2, QTableWidgetItem(f"{cost:.2f}"))
            self.frais_table.setItem(row_idx, 3, QTableWidgetItem(fdate))

            desc_item = QTableWidgetItem(desc if len(desc) <= 60 else desc[:57]+"...")
            desc_item.setToolTip(desc)
            self.frais_table.setItem(row_idx, 4, desc_item)

            # Actions
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(8,4,8,4)
            actions_layout.setSpacing(8)

            edit_btn = QPushButton("Éditer")
            edit_btn.setStyleSheet("background:#06b6d4; color:white; padding:6px 12px;")
            edit_btn.clicked.connect(lambda _, i=row_idx, id=fid: self.edit_frais(id))

            del_btn = QPushButton("Supprimer")
            del_btn.setStyleSheet("background:#dc2626; color:white; padding:6px 12px;")
            del_btn.clicked.connect(lambda _, id=fid: self.delete_frais(id))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)
            self.frais_table.setCellWidget(row_idx, 5, actions)

        # Mise à jour des cartes résumé
        self.cursor.execute("SELECT SUM(cost) FROM expenses WHERE type='Frais'")
        self.total_frais_label.setText(f"{self.cursor.fetchone()[0] or 0:.2f} DA")

        self.cursor.execute("SELECT SUM(cost) FROM expenses WHERE type='Faux Frais'")
        self.total_faux_frais_label.setText(f"{self.cursor.fetchone()[0] or 0:.2f} DA")

        self.cursor.execute("SELECT SUM(cost) FROM expenses")
        total = self.cursor.fetchone()[0] or 0
        self.total_general_frais_label.setText(f"{total:.2f} DA")

    def edit_frais(self, frais_id):
        self.cursor.execute("SELECT type, cost, date, description FROM expenses WHERE id=?", (frais_id,))
        ftype, cost, fdate, desc = self.cursor.fetchone()

        self.frais_type_combo.setCurrentText(ftype)
        self.frais_cout_input.setText(str(cost))
        self.frais_date_input.setDate(QDate.fromString(fdate, "yyyy-MM-dd"))
        self.frais_desc_input.setPlainText(desc)
        self.current_frais_id = frais_id
        self.frais_save_btn.setText("Mettre à jour")
        self.frais_form.setVisible(True)

    def save_frais(self):
        ftype = self.frais_type_combo.currentText()
        try:
            cost = float(self.frais_cout_input.text().replace(',','.'))
        except:
            QMessageBox.warning(self, "Erreur", "Le coût doit être un nombre valide.")
            return

        fdate = self.frais_date_input.date().toString("yyyy-MM-dd")
        desc = self.frais_desc_input.toPlainText().strip()

        if not desc:
            QMessageBox.warning(self, "Erreur", "La description est obligatoire.")
            return

        if hasattr(self, 'current_frais_id') and self.current_frais_id:
            self.cursor.execute("""
                UPDATE expenses SET type=?, cost=?, date=?, description=? WHERE id=?
            """, (ftype, cost, fdate, desc, self.current_frais_id))
        else:
            self.cursor.execute("""
                INSERT INTO expenses (type, cost, date, description) VALUES (?, ?, ?, ?)
            """, (ftype, cost, fdate, desc))

        self.conn.commit()
        self.load_frais()
        self.update_dashboard_stats()
        self.frais_form.setVisible(False)
        self.current_frais_id = None
        self.frais_save_btn.setText("Enregistrer le Frais")
        # vider le formulaire
        self.frais_cout_input.clear()
        self.frais_desc_input.clear()

    def delete_frais(self, frais_id):
        reply = QMessageBox.question(self, "Confirmation", "Supprimer ce frais ?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM expenses WHERE id=?", (frais_id,))
            self.conn.commit()
            self.load_frais()
            self.update_dashboard_stats()

    def delete_selected_frais(self):
        selected_ids = []
        for i in range(self.frais_table.rowCount()):
            check_widget = self.frais_table.cellWidget(i, 0)
            check = check_widget.layout().itemAt(0).widget()
            if check.isChecked():
                fid = int(self.frais_table.item(i, 1).text())
                selected_ids.append(fid)
        if selected_ids:
            reply = QMessageBox.question(self, "Confirmer", self.translations["fr"]["confirm_supprimer_selection"],
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for fid in selected_ids:
                    self.cursor.execute("DELETE FROM expenses WHERE id = ?", (fid,))
                self.conn.commit()
                self.load_frais()
                self.update_dashboard_stats()

    def setup_factures_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(18)

        # ================== TITRE ==================
        title = QLabel("Gestion des Factures")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#111827;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== CARTES RÉSUMÉ ==================
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(16)

        self.nb_factures_label = QLabel("0")
        self.total_factures_label = QLabel("0.00 DA")

        cards_data = [
            ("Nombre de Factures", self.nb_factures_label, "#7c3aed"),
            ("Revenu Total", self.total_factures_label, "#059669")
        ]

        for text, value_label, color in cards_data:
            card = QWidget()
            card.setFixedHeight(100)
            card.setStyleSheet(f"""
                background:white;
                border-radius:16px;
                border-left:5px solid {color};
                box-shadow: 0 6px 16px rgba(0,0,0,0.07);
            """)
            v = QVBoxLayout(card)
            v.setContentsMargins(18,16,18,16)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("color:#374151; font-size:18px; font-weight:600;")
            v.addWidget(text_label)
            
            value_label.setStyleSheet(f"color:{color}; font-size:32px; font-weight:900;")
            value_label.setAlignment(Qt.AlignCenter)
            v.addWidget(value_label)
            cards_layout.addWidget(card)

        layout.addWidget(cards_widget)

        # Titre de la liste
        list_label = QLabel("Liste des Factures Générées")
        list_label.setStyleSheet("font-size:18px; font-weight:bold; color:#1e40af; margin-top:15px;")
        layout.addWidget(list_label)

        # ================== RECHERCHE ==================
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Rechercher par client, matricule...")
        search_bar.setStyleSheet("""
            QLineEdit {
                padding:12px 16px;
                font-size:18px;
                border:1px solid #d1d5db;
                border-radius:12px;
                background:#f9fafb;
            }
            QLineEdit:focus { border:2px solid #3b82f6; }
        """)
        search_bar.textChanged.connect(self.load_factures)
        self.facture_search_input = search_bar
        layout.addWidget(search_bar)

        # ================== TABLEAU ==================
        self.facture_table = QTableWidget()
        self.facture_table.setColumnCount(7)
        self.facture_table.setHorizontalHeaderLabels([
            "ID Facture", "ID Location", "Client", "Véhicule", "Date Location", "Coût Total (DA)", "Actions"
        ])
        
        self.facture_table.setStyleSheet("""
            QTableWidget { 
                background:white; border:1px solid #e5e7eb; border-radius:16px; 
                gridline-color:#f3f4f6; font-size:18px; 
            }
            QHeaderView::section { 
                background:#1e40af; color:white; padding:14px; 
                font-weight:bold; font-size:18px; 
            }
        """)
        
        self.facture_table.verticalHeader().setDefaultSectionSize(60)
        self.facture_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.facture_table.setAlternatingRowColors(True)

        header = self.facture_table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.facture_table.setColumnWidth(0, 140)
        self.facture_table.setColumnWidth(1, 140)
        self.facture_table.setColumnWidth(3, 160)
        self.facture_table.setColumnWidth(4, 150)
        self.facture_table.setColumnWidth(5, 140)
        self.facture_table.setColumnWidth(6, 320)

        layout.addWidget(self.facture_table, 1)

        scroll.setWidget(page)
        self.content_stack.insertWidget(6, scroll)

        # Charger les factures
        self.load_factures()


    def load_factures(self):
        search = self.facture_search_input.text().lower() if hasattr(self, 'facture_search_input') else ""

        # Nettoyage complet
        self.facture_table.clearContents()
        self.facture_table.setRowCount(0)

        query = """
            SELECT f.id, l.id, 
                c.nom || ' ' || c.prenom,
                v.numero_matricule || ' - ' || v.modele,
                substr(l.date_heure_location, 1, 10),
                l.cout_total
            FROM factures f
            JOIN locations l ON f.location_id = l.id
            JOIN clients c ON l.client_id = c.id
            JOIN voitures v ON l.voiture_id = v.id
            WHERE lower(c.nom || ' ' || c.prenom || v.numero_matricule || v.modele) LIKE ?
            ORDER BY f.id DESC
        """
        self.cursor.execute(query, (f"%{search}%",))
        rows = self.cursor.fetchall()

        self.facture_table.setRowCount(len(rows))

        for i, (fid, loc_id, client, voiture, date_loc, cout) in enumerate(rows):
            self.facture_table.setItem(i, 0, QTableWidgetItem(str(fid)))
            self.facture_table.setItem(i, 1, QTableWidgetItem(str(loc_id)))
            self.facture_table.setItem(i, 2, QTableWidgetItem(client))
            self.facture_table.setItem(i, 3, QTableWidgetItem(voiture))
            self.facture_table.setItem(i, 4, QTableWidgetItem(date_loc))
            
            item = QTableWidgetItem(f"{cout:.2f} DA")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.facture_table.setItem(i, 5, item)

            # === ACTIONS : 4 BOUTONS ===
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(6, 3, 6, 3)
            layout.setSpacing(6)

            btn_view_ar = QPushButton("Voir")
            btn_view_ar.setStyleSheet("background:#3b82f6; color:white; padding:6px 10px; font-size:13px;")
            btn_view_ar.clicked.connect(lambda _, id_f=fid: self.view_facture(id_f))

            btn_print_ar = QPushButton("Imprimer")
            btn_print_ar.setStyleSheet("background:#16a34a; color:white; padding:6px 10px; font-size:13px;")
            btn_print_ar.clicked.connect(lambda _, id_f=fid: self.print_facture(id_f))

            btn_view_fr = QPushButton("Voir FR")
            btn_view_fr.setStyleSheet("background:#8b5cf6; color:white; padding:6px 10px; font-size:13px;")
            btn_view_fr.clicked.connect(lambda _, id_f=fid: self.view_facture_fr(id_f))

            btn_print_fr = QPushButton("Imprimer FR")
            btn_print_fr.setStyleSheet("background:#dc2626; color:white; padding:6px 10px; font-size:13px;")
            btn_print_fr.clicked.connect(lambda _, id_f=fid: self.print_facture_fr(id_f))

            layout.addWidget(btn_view_ar)
            layout.addWidget(btn_print_ar)
            layout.addWidget(btn_view_fr)
            layout.addWidget(btn_print_fr)

            self.facture_table.setCellWidget(i, 6, widget)
        # Stats
        self.cursor.execute("SELECT COUNT(*), COALESCE(SUM(l.cout_total),0) FROM factures f JOIN locations l ON f.location_id = l.id")
        count, total = self.cursor.fetchone()
        self.nb_factures_label.setText(str(count))
        self.total_factures_label.setText(f"{total:.2f} DA")



    def view_facture(self, facture_id):
        self.cursor.execute("SELECT location_id FROM factures WHERE id = ?", (facture_id,))
        location_id = self.cursor.fetchone()[0]
        html = self.get_facture_html(location_id)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Facture Nº {facture_id}")
        dialog.resize(1000, 1200)
        view = QWebEngineView()
        base_url = QUrl.fromLocalFile(os.path.join(get_app_path(), "").replace("\\", "/"))
        view.setHtml(html, base_url)
        vbox = QVBoxLayout(dialog)
        vbox.addWidget(view)
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.close)
        vbox.addWidget(close_btn, alignment=Qt.AlignRight)
        dialog.exec_()


    def show_factures(self):
        self.content_stack.setCurrentIndex(6)
        self.load_factures()                     # ← Charge les factures normales
        self.switch_facture_mode("normal")       # ← Force le mode normal + nettoie tout
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white; background-color: #34495E; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["factures"].setStyleSheet("color: white; background-color: #3498DB; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def view_facture_fr(self, facture_id):
        self.cursor.execute("SELECT location_id FROM factures WHERE id = ?", (facture_id,))
        location_id = self.cursor.fetchone()[0]
        html = self.get_facture_html_fr(location_id)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Facture Nº {facture_id} (Version Française)")
        dialog.resize(1000, 1200)

        view = QWebEngineView()
        base_url = QUrl.fromLocalFile(os.path.join(get_app_path(), "").replace("\\", "/"))
        view.setHtml(html, base_url)

        vbox = QVBoxLayout(dialog)
        vbox.addWidget(view)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.close)
        vbox.addWidget(close_btn, alignment=Qt.AlignRight)

        dialog.exec_()

    def print_facture_fr(self, facture_id):
        self.cursor.execute("SELECT location_id FROM factures WHERE id = ?", (facture_id,))
        location_id = self.cursor.fetchone()[0]
        html = self.get_facture_html_fr(location_id)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)

        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            view = QWebEngineView()
            base_url = QUrl.fromLocalFile(os.path.join(get_app_path(), "").replace("\\", "/"))
            view.setHtml(html, base_url)

            def do_print():
                view.page().print(printer, lambda success: None)

            view.loadFinished.connect(do_print)


    def get_facture_html(self, location_id):
        # Fetch location data
        self.cursor.execute("""
            SELECT 
                v.numero_matricule, v.modele, v.brand, 
                c.nom, c.prenom, c.date_naissance, c.lieu_naissance, c.adresse, c.numero_permis, c.date_permis, c.telephone, 
                c2.nom, c2.prenom, c2.date_naissance, c2.lieu_naissance, c2.adresse, c2.numero_permis, c2.date_permis, 
                l.date_heure_location, l.jours, l.cout_total, l.fuel_depart, l.promotion, 
                l.accessories_radio, l.accessories_jack, l.accessories_lighter, l.accessories_mat, l.accessories_code, l.km_depart,
                l.insurance_company, l.insurance_policy, l.payment_method, l.check_number, l.check_date,
                l.deposit_amount, l.deposit_method, l.bank
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
            LEFT JOIN clients c2 ON l.second_client_id = c2.id
            WHERE l.id = ?
        """, (location_id,))
        data = self.cursor.fetchone()
        if not data:
            return "<h1>Facture non trouvée</h1>"

        (plate, model, brand, c1_nom, c1_prenom, c1_birth_date, c1_birth_place, c1_address, c1_license, c1_license_date, c1_phone, 
        c2_nom, c2_prenom, c2_birth_date, c2_birth_place, c2_address, c2_license, c2_license_date, 
        date_location, jours, cout_total, fuel_depart, promotion, 
        acc_radio, acc_jack, acc_lighter, acc_mat, acc_code, km_depart_db,
        insurance_company, insurance_policy, payment_method_db, check_number, check_date,
        deposit_amount, deposit_method_db, bank) = data

        # Format data
        contract_number = f"LOC-{location_id:04d}"
        c1_name = f"{c1_nom} {c1_prenom}"
        c1_birth = f"{c1_birth_date} - {c1_birth_place}"
        c1_license_date = c1_license_date or ""
        c2_name = f"{c2_nom} {c2_prenom}" if c2_nom else ""
        c2_birth = f"{c2_birth_date} - {c2_birth_place}" if c2_birth_date else ""
        c2_license_date = c2_license_date or ""
        c2_address = c2_address or ""
        c2_license = c2_license or ""
        date_depart = date_location.split()[0]
        time_depart = date_location.split()[1]
        date_return = (datetime.strptime(date_depart, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")        
        time_return = ""
        km_depart = str(km_depart_db)
        km_return = ""
        fuel_depart = f"{fuel_depart}"
        fuel_return =""

        category = ""
        price_per_day = f"{cout_total / jours if jours > 0 else 0:.2f} DZ"
        days = str(jours)
        discount = f"{promotion} DZ"
        total_price = f"{cout_total:.2f} DZ"


        car_image = "car22.png"
                # Use real data from DB, but keep empty if None
        insurance_company = insurance_company or ""
        insurance_policy = insurance_policy or ""
        check_number = check_number or ""
        check_date = check_date or ""
        deposit_amount = f"{deposit_amount:.2f}" if deposit_amount and deposit_amount > 0 else ""
        bank = bank or ""
        # Récupère les données d'assurance (si elles existent dans la DB ou depuis current_insurance_data)
        # Supposons que tu les récupères dans des variables comme :
        payment_method = "Cash"      # valeur en anglais depuis la DB
        deposit_method = "Cash"      # valeur en anglais depuis la DB

        # Traduction pour l'affichage dans la facture
        pay_cash_checked = 'checked' if payment_method == "Cash" else ''
        pay_check_checked = 'checked' if payment_method == "Check" else ''
        pay_cash_class = ' checked' if payment_method == "Cash" else ''
        pay_check_class = ' checked' if payment_method == "Check" else ''

        g_cash_checked = 'checked' if deposit_method == "Cash" else ''
        g_check_checked = 'checked' if deposit_method == "Check" else ''
        g_cash_class = ' checked' if deposit_method == "Cash" else ''
        g_check_class = ' checked' if deposit_method == "Check" else ''
        # Default methods
        payment_method = payment_method or "Cash"   # 'Cash' or 'Check'
        deposit_method = deposit_method or "Cash"   # 'Cash' or 'Check'
        # تحويل قيم اللواحق
        radio   = "oui" if acc_radio == "oui" else "non" if acc_radio == "non" else ""
        jack    = "oui" if acc_jack == "oui" else "non" if acc_jack == "non" else ""
        lighter = "oui" if acc_lighter == "oui" else "non" if acc_lighter == "non" else ""
        mat     = "oui" if acc_mat == "oui" else "non" if acc_mat == "non" else ""
        code    = "oui" if acc_code == "oui" else "non" if acc_code == "non" else ""

        # دالة لتوليد صف checkbox
        def chk(desc, name, val):
            yes = 'checked' if val == "oui" else ''
            no  = 'checked' if val == "non" else ''
            yes_cls = ' checked' if yes else ''
            no_cls  = ' checked' if no else ''
            return f'''
                <div class="checkbox-row">
                    <span style="flex:1;">{desc}</span>
                    <div class="checkbox-label">
                        <input type="checkbox" id="{name}_y" name="{name}" {yes}>
                        <label for="{name}_y" class="modern-checkbox{yes_cls}"></label>
                    </div>
                    <div class="checkbox-label">
                        <input type="checkbox" id="{name}_n" name="{name}" {no}>
                        <label for="{name}_n" class="modern-checkbox{no_cls}"></label>
                    </div>
                </div>'''

        accessories_html = (
            chk("المذياع",            "radio",   radio) +
            chk("الرافعة وعجلة النجدة", "jack",    jack) +
            chk("ولاعة السجائر",       "lighter", lighter) +
            chk("البساط",              "mat",     mat) +
            chk("الرمز",               "code",    code)
        )

        # القالب الكامل للـ HTML (مع {{ accessories_html }} فقط في مكان اللواحق)
        html = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>عقد كراء سيارة - LOCATOP</title>
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;800&display=swap" rel="stylesheet">
<style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Cairo', sans-serif; direction: rtl; color: #000 !important; background: white; line-height: 1.3; padding: 0; margin: 0; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; background: #004080; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; z-index: 1000; }}
        @media print {{ .print-btn {{ display: none; }} .page {{ border: none !important; }} }}

        .page {{ width: 210mm; min-height: 297mm; padding: 8mm 10mm; margin: 0 auto; background: white; page-break-after: always; display: block; font-size: 10pt; position: relative; }}
        .page:last-child {{ page-break-after: avoid; }}

        .header {{ text-align: center; padding-bottom: 4px; margin-bottom: 6px; border-bottom: 1.5px solid #004080; }}
        .logo {{ font-size: 18pt; font-weight: 800; color: #004080; }}
        .main-title {{ font-size: 12pt; font-weight: bold; margin: 3px 0; }}
        .agency-info {{ font-size: 8pt; display: flex; justify-content: space-between; margin: 2px 0; }}
        .contract-number {{ text-align: center; font-size: 11pt; font-weight: bold; color: #004080; background: #e9ecef; padding: 3px; border: 1px solid #ced4da; border-radius: 3px; margin: 5px 0; }}

        .line-dotted {{ border-bottom: 1px dotted #a0a0a0; flex-grow: 1; margin: 0 3px; min-height: 1.1em; font-weight: 600; font-size: 10pt; color: #000; padding: 0 3px; display: inline-block; }}

        table {{ width: 100%; border-collapse: collapse; margin: 4px 6px; font-size: 9.5pt; }}
        th, td {{ border: 1px solid #ced4da; padding: 4px; text-align: center; }}
        th {{ background: #e9ecef; font-weight: bold; }}

        .section-header {{ font-weight: bold; font-size: 10.5pt; color: #004080; border-bottom: 1.3px solid #004080; padding-bottom: 1px; margin: 6px 0 4px; text-align: center; }}

        .flex-row {{ display: flex; gap: 6px; margin-bottom: 6px; }}
        .col-2 {{ flex: 2; }} .col-3 {{ flex: 3; }}
        .field-group {{ display: flex; align-items: center; margin-bottom: 2px; font-size: 9.2pt; }}
        .field-group label {{ min-width: 80px; margin-left: 4px; font-weight: 500; }}

        .condition-row {{ display: flex; gap: 6px; margin: 4px 0; }}
        .condition-box {{ flex: 1; border: 2px solid #004080; padding: 3px; height: 180px; text-align: center; background: #f8f9fa; font-size: 10pt; }}
        .condition-box span {{ font-weight: bold; color: #004080; display: block; margin-bottom: 2px; }}
        .car-img-container {{ width: 100%; height: 150px; background: #fff; border: 1px dashed #ced4da; }}
        .car-img-container img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}

        .bottom-row {{ display: flex; gap: 6px; margin-top: 4px; }}
        .box {{ border: 1px solid #ced4da; padding: 5px; background: white; flex: 1; }}
        .box h4 {{ margin: 0 0 4px; font-size: 10pt; text-align: center; color: #004080; }}

        .accessories-header {{ font-weight: bold; font-size: 8.5pt; display: flex; justify-content: flex-end; gap: 10px; margin-bottom: 2px; padding: 0 5px; }}
        .accessories-header span:first-child {{ flex-grow: 1; text-align: right; }}
        .checkbox-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 1px; font-size: 9pt; padding: 0 5px; }}
        .checkbox-label {{ display: flex; align-items: center; gap: 4px; }}
        .modern-checkbox {{ width: 11px; height: 11px; border: 1.5px solid #004080; background: white; position: relative; display: inline-block; cursor: pointer; }}
        .modern-checkbox.checked::after {{ content: '✓'; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #004080; color: white; font-size: 7.5pt; display: flex; align-items: center; justify-content: center; }}
        input[type="checkbox"] {{ opacity: 0; position: absolute; }}

        .signatures {{ display: flex; justify-content: space-around; margin-top: 8px; padding-top: 6px; border-top: 1.3px solid #004080; gap: 6px; }}
        .sig-box {{ width: 30%; text-align: center; padding-top: 20px;  }}
        .sig-line {{ border-top: 1px solid #004080; margin-top: 20px; padding-top: 2px; font-size: 9pt; }}

        .terms-title {{ text-align: center; font-size: 15pt; font-weight: bold; margin: 25px; }}
        .terms-content {{ display: flex; gap: 10px; margin-top: 6px; min-height: 170mm; }}
        .terms-column {{ flex: 1; text-align: justify; font-size: 10.7pt; line-height: 1.4; margin-left:10px; }}
        .term {{ text-indent: -16pt; margin-right: 16pt; margin-bottom: 3.5pt; page-break-inside: avoid; }}
        .term-number {{ font-weight: bold; margin-left: 5pt; }}

        @page {{ size: A4 portrait; margin: 0; }}
        @media print {{ .page {{ padding: 8mm 10mm; min-height: 297mm; }} .condition-box {{ height: 180px !important; }} .car-img-container {{ height: 150px !important; }} .sig-line {{ margin-top: 15px !important; }} .terms-column {{ font-size: 8.7pt !important; }} }}
    </style>
        </head>
        <body>

        <button class="print-btn" onclick="window.print()"></button>
            <!-- ====================== الصفحة 1 ====================== -->
            <div class="page">
                <div class="header">
                    <div class="logo">LOCATOP</div>
                    <div class="main-title">عقد كراء سيارة مع أو بدون سائق</div>
                    <div class="agency-info">
                        <span style="color:black;">**عيساوي عبد القادر** - 05 تجمع 30 الخريبة ندرومة</span>
                        <span>**ر.س**: <strong>11 / 1365901 _ 13/00</strong></span>
                    </div>
                    <div class="agency-info">
                        <span>الهاتف: <strong style ="color:green;">0775.86.87.65/0557.46.11.65</strong></span>
                        <span><strong></strong></span>
                        <span>رات: <strong>198313400077917</strong></span>
                    </div>
                </div>

                <div class="contract-number">عقد تأجير رقم : <span class="line-dotted">{contract_number}</span></div>

                <div class="flex-row">
                    <div class="col-3">
                        <h3 class="section-header">معلومات المستأجر (السائق الأول)</h3>
                        <div class="field-group"><label>الإسم واللقب :</label><span class="line-dotted">{c1_name}</span></div>
                        <div class="field-group"><label>تاريخ ومكان الإزدياد:</label><span class="line-dotted">{c1_birth}</span></div>
                        <div class="field-group"><label>العنوان:</label><span class="line-dotted">{c1_address}</span></div>
                        <div class="field-group"><label>رخصة السياقة رقم:</label><span class="line-dotted">{c1_license}</span></div>
                        <div class="field-group"><label>الصادرة في:</label><span class="line-dotted">{c1_license_date}</span></div>
                        <div class="field-group"><label>الهاتف:</label><span class="line-dotted">{c1_phone}</span></div>

                        <h4 style="font-size:9.5pt;color:#004080;margin:6px 0 2px;border-top:1px dashed #ced4da;padding-top:2px;">السائق الثاني (إضافي):</h4>
                        <div class="field-group"><label>الإسم واللقب:</label><span class="line-dotted">{c2_name}</span></div>
                        <div class="field-group"><label>العنوان:</label><span class="line-dotted">{c2_address}</span></div>
                        <div class="field-group"><label>تاريخ ومكان الإزدياد:</label><span class="line-dotted">{c2_birth}</span></div>
                        <div class="field-group"><label>رخصة السياقة رقم:</label><span class="line-dotted">{c2_license}</span></div>
                        <div class="field-group"><label>الصادرة في:</label><span class="line-dotted">{c2_license_date}</span></div>
                    </div>

                    <div class="col-2">
                        <h3 class="section-header">تفاصيل مدة التأجير</h3>
                        <table>
                            <tr><th></th><th>الإقلاع</th><th>العودة</th></tr>
                            <tr><td>الكيلومترات</td><td>{km_depart}</td><td>{km_return}</td></tr>
                            <tr><td>الوقود</td><td>{fuel_depart}</td><td></td></tr>
                            <tr><td>مدة التأجير</td><td colspan="2">{jours} أيام</td></tr>
                                                        <tr><td>التاريخ</td><td style ="color:green;">{date_depart}</td><td style ="color:red;">{date_return}</td></tr>                            <tr><td>الساعة</td><td>{time_depart}</td><td>{time_depart}</td></tr>
                        </table>
                    </div>
                </div>

                <div class="section-header">مواصفات السيارة والجانب المالي</div>
                <table>
                    <tr><th>رقم التسجيل</th><th>تاريخ الإقلاع</th><th>الصنف</th><th>النوع</th><th>سعر 24 سا</th><th>عدد أيام الكراء</th><th>التخفيضات</th><th>السعر الكلي</th></tr>
                    <tr style="height: 50px;"><td style ="font-weight: bold;">{plate}</td><td>{date_depart}</td><td style ="font-weight: bold;">{brand}</td><td style ="font-weight: bold;">{model}</td><td>{price_per_day}</td><td>{days}</td><td>{discount}</td><td>{total_price}</td></tr>
                </table>

                <div class="section-header">حالة السيارة (تحديد الأضرار والخدوش)</div>
                <div class="condition-row">
                    <div class="condition-box"><span>عند الإقلاع</span>
                        <div class="car-img-container"><img src="car22.png" alt="Car"></div>
                    </div>
                    <div class="condition-box"><span>عند العودة</span>
                        <div class="car-img-container"><img src="car22.png" alt="Car"></div>
                    </div>
                </div>

                <div class="bottom-row">
                    <!-- اللواحق (هنا يتم استبدالها ديناميكيًا) -->
                    <div class="box">
                        <h4>لواحق السيارة المستلمة</h4>
                        <div class="accessories-header">
                            <span>البيان</span><span>نعم</span><span>لا</span>
                        </div>
                        {accessories_html}
                    </div>

                    <div class="box">
                        <div style="position: relative; background-color: rgba(255, 0, 0, 0.15); border: 1px solid #ff0000; border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; text-align: right; direction: rtl;">
                            <h4 style="margin: 0 0 10px 0; color: #d00000; font-size: 14pt; text-align: center;">تنبيه هام ⚠️</h4>
                            <p style="margin: 0; font-size: 7pt; line-height: 1.5;font-weight: bold; color: #333;">
                            المعدل الكيلومتري المسموح به من طرف الوكالة خلال 24 ساعة هو 300 كلم
                            ، وفي حالة تجاوز الحد المحدد في العقد يلتزم المستأجر بدفع 20 دج عن كل كيلومتر إضافي. 
                            كما أن مدة الإيجار هي 24 ساعة،
                              وفي حال تأخر المستأجر عن إرجاع السيارة في الوقت المحدد يلتزم بدفع 600 دج لساعة واحدة، و1500 دج لساعتين،
                              و2400 دج لثلاث ساعات، وإذا تجاوز التأخير ثلاث ساعات تُحسب أجرة يوم كامل.

                            </p>
                        </div>
                    </div>
                </div>

                <div class="signatures">
                    <div class="sig-box"><div class="sig-line">ختم وتوقيع الوكالة</div></div>

                    <div class="sig-box"><div class="sig-line">توقيع السائق الأول وبصمته</div></div>
                    <div class="sig-box"><div class="sig-line">توقيع السائق الثاني وبصمته</div></div>
                    
                </div>
            </div>

            <!-- ====================== الصفحة 2 - الشروط ====================== -->
            <div class="page">
                <h1 class="terms-title">الشروط العامة لعقد تأجير السيارة</h1>

                    <div class="terms-content">
                        <div class="terms-column">
                            <p class="term"><span class="term-number">01</span> يتعين على المستأجر وعلى المرافق السائق الثاني) أن يطرح نسخة من بطاقة تعريفه الوطنية أو نسخة من جواز سفره ونسخة من رخصة السياقة كلها سارية المفعول إلى المؤجر للاستدلال بها طبقا للقانون.</p>
                            <p class="term"><span class="term-number">02</span> لا تؤجر السيارة إلا للاشخاص البالغين 25 سنة على الأقل و الحائزين على رخصة سياقة تزيد عن 24 شهرا يبدأ حسابها من تاريخ صدورها و سارية المفعول من وقت التأجير والى غاية رجوع السيارة.</p>
                            <p class="term"><span class="term-number">03</span> يتعين على المستأجر قبل التوقيع على العقد و قبل مغادرته للوكالة أن يتفحص السيارة ويصرح بالعيوب والنقائص الموجودة بها.</p>
                            <p class="term"><span class="term-number">04</span> تقع المسؤولية المدنية على المستأجر لوحده إذا لم يصرح بالعيوب والنقائص التي لاحظها على السيارة قبل مغادرته الوكالة.</p>
                            <p class="term"><span class="term-number">05</span> يتعين على المؤجر والمستأجر إمضاء ملحق عقد الإيجار التي تدون فيه وجوبا كافة الملاحظات الناتجة عن معاينة السيارة بعد انتهاء مدة التأجير.</p>
                            <p class="term"><span class="term-number">06</span> يتعين على المستأجر أن يخضع للقوانين والأنظمة المتعلقة بالمرور والى حمله رخصة السياقة الخاصة به إضافة إلى الوثائق التي يسلمها المؤجر له المتعلقة بالسيارة وبان يحترم نظام استعمال السيارة.</p>
                            <p class="term"><span class="term-number">07</span> لا يسمح بقيادة السيارة إلا من قبل المستأجر والمرافق السابق الثاني) الذي أمضى على عقد التأجير وعند حدوث أي ضرر يكونان مسؤولان بالتضامن عن الأضرار التي تلحق بالسيارة.</p>
                            <p class="term"><span class="term-number">08</span> في حالة رغبة أي شخص آخر في قيادة السيارة ليس طرفا في عقد كراء السيارة فانه يتعين عليه أن يتقدم وجوبا إلى الوكالة لإضافة اسمه في التقسيمة الملحقة بالعقد مع مصادقته على كافة شروط العقد إلى جانب المستأجر ليكونان مسؤولان بالتضامن عن أي أضرار قد تلحق بالسيارة.</p>
                            <p class="term"><span class="term-number">09</span> يتعين على المستأجر أن يركن السيارة في مكان امن وأن يقوم بغلق الأبواب جيدا وبان يشغل نظام الإنذار إن وجد ويمنع عليه أن يترك مفاتيح السيارة في داخل السيارة وذلك مهما كانت الظروف.</p>
                            <p class="term"><span class="term-number">10</span> يتعين على المستأجر عدم استعمال السيارة في نقل البضائع مهما كان نوعها المحظورة وغير المحظورة قانونا ) أو في نقل المسافرين سواء بمقابل أو بدون مقابل.</p>
                            <p class="term"><span class="term-number">11</span> يتعين على المستأجر عدم استعمال السيارة للسباق أو لجر أو قطر مركبات أو قاطرات أو أي وسيلة أخرى بعجلات أو بدون عجلات أو استعمال السيارة محل الكراء في غير الغرض الموجهة إليه.</p>
                            <p class="term"><span class="term-number">12</span> يتعين على المستأجر عدم استعمال السيارة بعد احتساء المشروبات الكحولية أو المواد المهلوسة وذلك تحت طائلة مسؤوليته المدنية.</p>
                            <p class="term"><span class="term-number">13</span> يتعين على المستاجر عدم استعمال السيارة المؤجرة لتعليم السياقة.</p>
                            <p class="term"><span class="term-number">14</span> يتعين على المستأجر عدم بيع أو رهن أو إبداع السيارة أو ملحقاتها الأغراضه الشخصية.</p>
                            <p class="term"><span class="term-number">15</span> يتعين على المستأجر عدم إضافة أو تعديل أي جهاز من أجهزة. السيارة محل الكراء.</p>
                            <p class="term"><span class="term-number">16</span> يتحمل المستأجر المسؤولية كاملة في حالة سرقة السيارة أو لواحقها أو في حالة تعرضها للتخريب نتيجة إهماله وعدم حيطته واحتياطه.</p>
                                                        <p class="term"><span class="term-number">17</span> يتعين على المستأجر الالتزام بالتصريح لدى السلطات المعنية فورا في حالة تعرض السيارة أو لواحقها للسرقة وبان يقدم نسخة من محضر التصريح إلى المؤجر تحت طائلة متابعته بجريمة السرقة وخيانة الأمانة.</p>

                        </div>
                        <div class="terms-column">
                            
                            <p class="term"><span class="term-number">18</span> يتعين على المستأجر تعويض قيمة السيارة إلى المؤجر إذا لم يتم العثور عليها في مهلة 30 يوما من تاريخ التسريح بالسرقة.</p>
                            <p class="term"><span class="term-number">19</span> في حالة تعرض السيارة لأي أضرار مادية وهي تحت تصرف المستاجر فانه يتحمل المصاريف الخاصة بتصليح السيارة والمصاريف الناتجة عن توقف السيارة بالورشة كاملة.</p>
                            <p class="term"><span class="term-number">20</span> يتعين على المستاجر دفع مصاريف مكوث السيارة بالمحشر حالة حجزها من قبل السلطات المعنية.</p>
                            <p class="term"><span class="term-number">21</span> يتعين على المستأجر إعلام المؤجر بالإعطاب الميكانيكية التي قد تلحق بالسيارة تحت طائلة مسؤوليته العقدية و التقصيرية.</p>
                            <p class="term"><span class="term-number">22</span> يكون المستأجر مسؤولا عن أي ضرر قد يصيب السيارة حالة عدم تعليمه للسيارة في تاريخ انتهاء مدة العقد وفي حالة رغبته في تمديد العقد يتعين عليه التقدم وبدون تماطل إلى الوكالة لتسوية وضعيته اتجاهها.</p>
                            <p class="term"><span class="term-number">23</span> للمؤجر الخيار في طلب مبلغ 30000 دج (ثلاثين ألف دينار جزائري) نقدا أو بموجب صك بالمبلغ وموقع من طرف المستأجر لتغطية الأضرار التي قد تصيب السيارة بالإضافة إلى بطاقة التعريف الوطنية أو جواز السفر بالنسبة للمغتربين كضمان.</p>
                            <p class="term"><span class="term-number">24</span> تكون مدة الإيجار 24 ساعة ويتعين على المستأجر في حالة تأخره عن إرجاع السيارة في الوقت المحدد أن يدفع مبلغ 600 ج الساعة واحدة ( 01 ساعة ) ومبلغ 1500 دج لساعتين (2) ساعة ) ومبلغ 2400 دج الثلاث ساعات ) 03 ساعات ) وأكثر من ثلاث ساعات يدفع أجرة يوم كامل</p>
                            <p class="term"><span class="term-number">25</span> المعدل الكيلوميتري المسموح به من طرف الوكالة في 24 ساعة هو 300 كلم وفي حالة تجاوز النسبة المحددة في العقد يتعين على المستأجر أن يدفع مبلغ عشرين دينار جزائري (20 دج ) لكل كيلومتر واحد</p>
                            <p class="term"><span class="term-number">26</span> يتعين على المستأجر ملا الخزان بالوقود عند إرجاع السيارة وبنفس الكمية عند الطلاق السيارة من الوكالة ومن نفس النوع المصرح به من طرف المؤجر تحت طائلة مسؤوليته المدنية التامة حالة أي عطب قد يصيب السيارة بسبب تغيير نوع الوقود أو بسبب رداءته.</p>
                            <p class="term"><span class="term-number">27</span> يتعين على المستأجر إرجاع السيارة عند نهاية عقد الإيجار أو عند نهاية فترة التمديد وبدون تأخر وبان يرجع السيارة نظيفة ومرتبة والأضواء منطفثة والأبواب مغلقة وبان يركنها بطريقة سليمة وتبعا لما ينص عليه قانون المرور</p>
                            <p class="term"><span class="term-number">28</span> يتم تحرير عقد الإيجار بموجب عقد مكتوب و في نسختين موقعة من طرف الأطراف المتعاقدة ويلتزم المؤجر بان يسلم نسخة منها إلى المستأجر وبان يحتفظ بالنسخة الثانية للاستدلال بها طبقا للقانون.</p>
                            <p class="term"><span class="term-number">29</span> في حالة تمديد عقد كراء السيارة يتم المصادقة والتوقيع على التمديد من طرف الأطراف في نفس العقد المتعلق بتأجير السيارة وفي الخانة المخصصة</p>
                            <p class="term"><span class="term-number">30</span> يتعين على طرفي العقد الإمضاء على ملحق عقد الإيجار المتضمن كافة الملاحظات الناتجة عن معاينة السيارة بعد انتهاء فترة الكراء أو تمديد عقد الكراء.</p>
                            <p class="term"><span class="term-number">31</span> في حالة وقوع نزاع تكون محكمة ندرومة مختصة محليا للفصل دون سواها في النزاع المطروح أمامها.</p>
                        </div>

                    </div>
                    <div class="signatures" style="margin-top:20px;">
                       
                                                <div class="sig-box"><div class="sig-line">إمضاء المؤجر (الوكالة)   </div></div>

                        <div class="sig-box"><div class="sig-line">المستاجر الأول: قرأت و صادقت عليه)</div></div>
                         <div class="sig-box"><div class="sig-line">المستأجر الثاني: قرأت و صادقت عليه)</div></div>
                    </div>
            </div>

            <script>
                document.querySelectorAll('label.modern-checkbox').forEach(l => {{
                    l.addEventListener('click', e => {{
                        e.preventDefault();
                        const input = document.getElementById(l.getAttribute('for'));
                        const name = input.name;
                        if (name) {{
                            document.querySelectorAll(`input[name="${{name}}"]`).forEach(i => {{
                                if (i !== input) {{ i.checked = false; document.querySelector(`label[for="${{i.id}}"]`).classList.remove('checked'); }}
                            }});
                        }}
                        input.checked = !input.checked;
                        l.classList.toggle('checked', input.checked);
                    }});
                }});
            </script>
        </body>
        </html>
        """

        # استبدال القيم
        html = html.replace("{contract_number}", contract_number)
        html = html.replace("{c1_name}", c1_name)
        html = html.replace("{c1_birth}", c1_birth)
        html = html.replace("{c1_address}", c1_address or "")
        html = html.replace("{c1_license}", c1_license or "")
        html = html.replace("{c1_license_date}", c1_license_date)
        html = html.replace("{c1_phone}", c1_phone or "")
        html = html.replace("{c2_name}", c2_name)
        html = html.replace("{c2_address}", c2_address)
        html = html.replace("{c2_birth}", c2_birth)
        html = html.replace("{c2_license}", c2_license)
        html = html.replace("{c2_license_date}", c2_license_date)
        html = html.replace("{km_depart}", km_depart)
        html = html.replace("{km_return}", km_return)
        html = html.replace("{fuel_depart}", fuel_depart)
        html = html.replace("{fuel_return}", fuel_return)
        html = html.replace("{date_depart}", date_depart)
        html = html.replace("{date_return}", date_return)
        html = html.replace("{time_depart}", time_depart)
        html = html.replace("{time_return}", time_return or "")
        html = html.replace("{plate}", plate)
        html = html.replace("{brand}", brand)
        html = html.replace("{model}", model)
        html = html.replace("{price_per_day}", price_per_day)
        html = html.replace("{days}", days)
        html = html.replace("{discount}", discount)
        html = html.replace("{total_price}", total_price)
        html = html.replace("{insurance_company}", insurance_company)
        html = html.replace("{insurance_policy}", insurance_policy)
        html = html.replace("{check_number}", check_number)
        html = html.replace("{check_date}", check_date)
        html = html.replace("{deposit_amount}", deposit_amount)
        html = html.replace("{bank}", bank)
        # === NEW: Replace insurance & payment fields ===
        html = html.replace("{insurance_company}", insurance_company)
        html = html.replace("{insurance_policy}", insurance_policy)
        html = html.replace("{check_number}", check_number)
        html = html.replace("{check_date}", check_date)
        html = html.replace("{deposit_amount}", deposit_amount)
        html = html.replace("{bank}", bank)
        html = html.replace("{pay_cash_checked}", pay_cash_checked)
        html = html.replace("{pay_check_checked}", pay_check_checked)
        html = html.replace("{pay_cash_class}", pay_cash_class)
        html = html.replace("{pay_check_class}", pay_check_class)
        html = html.replace("{g_cash_checked}", g_cash_checked)
        html = html.replace("{g_check_checked}", g_check_checked)
        html = html.replace("{g_cash_class}", g_cash_class)
        html = html.replace("{g_check_class}", g_check_class)
        # === Dynamic checkboxes for payment method ===
        if payment_method == "Cash":
            html = html.replace('id="pay_cash" name="pay" checked', 'id="pay_cash" name="pay" checked')
            html = html.replace('id="pay_check" name="pay">', 'id="pay_check" name="pay">')
        else:  # Check
            html = html.replace('id="pay_cash" name="pay" checked', 'id="pay_cash" name="pay">')
            html = html.replace('id="pay_check" name="pay">', 'id="pay_check" name="pay" checked')

        # === Dynamic checkboxes for deposit method ===
        if deposit_method == "Cash":
            html = html.replace('id="g_cash" name="g" checked', 'id="g_cash" name="g" checked')
            html = html.replace('id="g_check" name="g">', 'id="g_check" name="g">')
        else:  # Check
            html = html.replace('id="g_cash" name="g" checked', 'id="g_cash" name="g">')
            html = html.replace('id="g_check" name="g">', 'id="g_check" name="g" checked')

        # Replace accessories

        # إضافة اللواحق المولدة
        html = html.replace("{accessories_html}", accessories_html)

        return html
    def get_facture_html_fr(self, location_id):
        # Même requête que pour l'arabe
        self.cursor.execute("""
            SELECT 
                v.numero_matricule, v.modele, v.brand, 
                c.nom, c.prenom, c.date_naissance, c.lieu_naissance, c.adresse, c.numero_permis, c.date_permis, c.telephone, 
                c2.nom, c2.prenom, c2.date_naissance, c2.lieu_naissance, c2.adresse, c2.numero_permis, c2.date_permis, 
                l.date_heure_location, l.jours, l.cout_total, l.fuel_depart, l.promotion, 
                l.accessories_radio, l.accessories_jack, l.accessories_lighter, l.accessories_mat, l.accessories_code, l.km_depart,
                l.insurance_company, l.insurance_policy, l.payment_method, l.check_number, l.check_date,
                l.deposit_amount, l.deposit_method, l.bank
            FROM locations l
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
            LEFT JOIN clients c2 ON l.second_client_id = c2.id
            WHERE l.id = ?
        """, (location_id,))
        data = self.cursor.fetchone()
        if not data:
            return "<h1>Facture non trouvée</h1>"

        (plate, model, brand, c1_nom, c1_prenom, c1_birth_date, c1_birth_place, c1_address, c1_license, c1_license_date, c1_phone, 
        c2_nom, c2_prenom, c2_birth_date, c2_birth_place, c2_address, c2_license, c2_license_date, 
        date_location, jours, cout_total, fuel_depart, promotion, 
        acc_radio, acc_jack, acc_lighter, acc_mat, acc_code, km_depart_db,
        insurance_company, insurance_policy, payment_method_db, check_number, check_date,
        deposit_amount, deposit_method_db, bank) = data

        # Format data
        contract_number = f"LOC-{location_id:04d}"
        c1_name = f"{c1_nom} {c1_prenom}"
        c1_birth = f"{c1_birth_date} - {c1_birth_place}"
        c1_license_date = c1_license_date or ""
        c2_name = f"{c2_nom} {c2_prenom}" if c2_nom else ""
        c2_birth = f"{c2_birth_date} - {c2_birth_place}" if c2_birth_date else ""
        c2_license_date = c2_license_date or ""
        c2_address = c2_address or ""
        c2_license = c2_license or ""
        date_depart = date_location.split()[0]
        time_depart = date_location.split()[1]
        date_return = (datetime.strptime(date_depart, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")        
        time_return = ""
        km_depart = str(km_depart_db)
        km_return = ""
        fuel_depart = f"{fuel_depart}"
        fuel_return =""

        category = ""
        price_per_day = f"{cout_total / jours if jours > 0 else 0:.2f} DZ"
        days = str(jours)
        discount = f"{promotion} DZ"
        total_price = f"{cout_total:.2f} DZ"
        deposit_amount = f"{deposit_amount:.2f}" if deposit_amount and deposit_amount > 0 else ""

        # Traduction des accessoires (oui/non → oui/non, mais en français cette fois)
        radio   = "oui" if acc_radio == "oui" else "non" if acc_radio == "non" else ""
        jack    = "oui" if acc_jack == "oui" else "non" if acc_jack == "non" else ""
        lighter = "oui" if acc_lighter == "oui" else "non" if acc_lighter == "non" else ""
        mat     = "oui" if acc_mat == "oui" else "non" if acc_mat == "non" else ""
        code    = "oui" if acc_code == "oui" else "non" if acc_code == "non" else ""

        # Même fonction chk mais avec textes en français
        def chk_fr(desc, name, val):
            yes = 'checked' if val == "oui" else ''
            no  = 'checked' if val == "non" else ''
            yes_cls = ' checked' if yes else ''
            no_cls  = ' checked' if no else ''
            return f'''
                <div class="checkbox-row">
                    <span style="flex:1;">{desc}</span>
                    <div class="checkbox-label">
                        <input type="checkbox" id="{name}_y" name="{name}" {yes}>
                        <label for="{name}_y" class="modern-checkbox{yes_cls}"></label>
                    </div>
                    <div class="checkbox-label">
                        <input type="checkbox" id="{name}_n" name="{name}" {no}>
                        <label for="{name}_n" class="modern-checkbox{no_cls}"></label>
                    </div>
                </div>'''

        accessories_html_fr = (
            chk_fr("Radio",                 "radio",   radio) +
            chk_fr("Cric + roue de secours", "jack",    jack) +
            chk_fr("Allume-cigare",         "lighter", lighter) +
            chk_fr("Tapis",                 "mat",     mat) +
            chk_fr("Code antivol",          "code",    code)
        )

        # Paiement et garantie (même logique)
        payment_method = payment_method_db or "Cash"
        deposit_method = deposit_method_db or "Cash"

        pay_cash_checked = 'checked' if payment_method == "Cash" else ''
        pay_check_checked = 'checked' if payment_method == "Check" else ''
        pay_cash_class = ' checked' if payment_method == "Cash" else ''
        pay_check_class = ' checked' if payment_method == "Check" else ''

        g_cash_checked = 'checked' if deposit_method == "Cash" else ''
        g_check_checked = 'checked' if deposit_method == "Check" else ''
        g_cash_class = ' checked' if deposit_method == "Cash" else ''
        g_check_class = ' checked' if deposit_method == "Check" else ''

        # HTML presque identique, mais en français + dir="ltr" + lang="fr"
        html_fr = f"""<!DOCTYPE html>
<html lang="fr" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contrat de location de véhicule - LOCATOP</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Cairo', sans-serif; direction: ltr; color: #000 !important; background: white; line-height: 1.3; padding: 0; margin: 0; }}
        .print-btn {{ position: fixed; top: 10px; left: 10px; background: #004080; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; z-index: 1000; }}
        @media print {{ .print-btn {{ display: none; }} .page {{ border: none !important; }} }}
        .page {{ width: 210mm; min-height: 297mm; padding: 8mm 10mm; margin: 0 auto; background: white; page-break-after: always; display: block; font-size: 10pt; position: relative; }}
        .page:last-child {{ page-break-after: avoid; }}
        .header {{ text-align: center; padding-bottom: 4px; margin-bottom: 6px; border-bottom: 1.5px solid #004080; }}
        .logo {{ font-size: 18pt; font-weight: 800; color: #004080; }}
        .main-title {{ font-size: 12pt; font-weight: bold; margin: 3px 0; }}
        .agency-info {{ font-size: 8pt; display: flex; justify-content: space-between; margin: 2px 0; }}
        .contract-number {{ text-align: center; font-size: 11pt; font-weight: bold; color: #004080; background: #e9ecef; padding: 3px; border: 1px solid #ced4da; border-radius: 3px; margin: 5px 0; }}
        .line-dotted {{ border-bottom: 1px dotted #a0a0a0; flex-grow: 1; margin: 0 3px; min-height: 1.1em; font-weight: 600; font-size: 10pt; color: #000; padding: 0 3px; display: inline-block; }}
        table {{ width: 100%; border-collapse: collapse; margin: 4px 6px; font-size: 9.5pt; }}
        th, td {{ border: 1px solid #ced4da; padding: 4px; text-align: center; }}
        th {{ background: #e9ecef; font-weight: bold; }}
        .section-header {{ font-weight: bold; font-size: 10.5pt; color: #004080; border-bottom: 1.3px solid #004080; padding-bottom: 1px; margin: 6px 0 4px; text-align: center; }}
        .flex-row {{ display: flex; gap: 6px; margin-bottom: 6px; }}
        .col-2 {{ flex: 2; }} .col-3 {{ flex: 3; }}
        .field-group {{ display: flex; align-items: center; margin-bottom: 2px; font-size: 9.2pt; }}
        .field-group label {{ min-width: 80px; margin-right: 4px; font-weight: 500; }}
        .condition-row {{ display: flex; gap: 6px; margin: 4px 0; }}
        .condition-box {{ flex: 1; border: 2px solid #004080; padding: 3px; height: 180px; text-align: center; background: #f8f9fa; font-size: 10pt; }}
        .condition-box span {{ font-weight: bold; color: #004080; display: block; margin-bottom: 2px; }}
        .car-img-container {{ width: 100%; height: 150px; background: #fff; border: 1px dashed #ced4da; }}
        .car-img-container img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .bottom-row {{ display: flex; gap: 6px; margin-top: 4px; }}
        .box {{ border: 1px solid #ced4da; padding: 5px; background: white; flex: 1; }}
        .box h4 {{ margin: 0 0 4px; font-size: 10pt; text-align: center; color: #004080; }}
        .accessories-header {{ font-weight: bold; font-size: 8.5pt; display: flex; justify-content: flex-end; gap: 10px; margin-bottom: 2px; padding: 0 5px; }}
        .accessories-header span:first-child {{ flex-grow: 1; text-align: left; }}
        .checkbox-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 1px; font-size: 9pt; padding: 0 5px; }}
        .checkbox-label {{ display: flex; align-items: center; gap: 4px; }}
        .modern-checkbox {{ width: 11px; height: 11px; border: 1.5px solid #004080; background: white; position: relative; display: inline-block; cursor: pointer; }}
        .modern-checkbox.checked::after {{ content: '✓'; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #004080; color: white; font-size: 7.5pt; display: flex; align-items: center; justify-content: center; }}
        input[type="checkbox"] {{ opacity: 0; position: absolute; }}
        .signatures {{ display: flex; justify-content: space-around; margin-top: 8px; padding-top: 6px; border-top: 1.3px solid #004080; gap: 6px; }}
        .sig-box {{ width: 30%; text-align: center; padding-top: 20px; }}
        .sig-line {{ border-top: 1px solid #004080; margin-top: 20px; padding-top: 2px; font-size: 9pt; }}
        .terms-title {{ text-align: center; font-size: 15pt; font-weight: bold; margin: 25px; }}
        .terms-content {{ display: flex; gap: 10px; margin-top: 6px; min-height: 170mm; }}
        .terms-column {{ flex: 1; text-align: justify; font-size: 10.7pt; line-height: 1.4; margin-right:10px; }}
        .term {{ text-indent: -16pt; margin-left: 16pt; margin-bottom: 3.5pt; page-break-inside: avoid; }}
        .term-number {{ font-weight: bold; margin-right: 5pt; }}
        @page {{ size: A4 portrait; margin: 0; }}
        @media print {{ .page {{ padding: 8mm 10mm; min-height: 297mm; }} .condition-box {{ height: 180px !important; }} .car-img-container {{ height: 150px !important; }} .sig-line {{ margin-top: 15px !important; }} .terms-column {{ font-size: 8pt !important; }} }}
    </style>
</head>
<body>
<button class="print-btn" onclick="window.print()">Imprimer le contrat</button>

<!-- ====================== Page 1 ====================== -->
<div class="page">
    <div class="header">
        <div class="logo">LOCATOP</div>
        <div class="main-title">Contrat de location de véhicule avec ou sans chauffeur</div>
        <div class="agency-info">
            <span style="color:black;">**Aissaoui Abdelkader** - 05 regroupement 30 Khouriba Nedroma</span>
            <span>**R.C** : <strong>11 / 1365901 _ 13/00</strong></span>
        </div>
        <div class="agency-info">
            <span>Téléphone : <strong style="color:green;">0775.86.87.65 / 0557.46.11.65</strong></span>
            <span><strong></strong></span>
            <span>NIF : <strong>198313400077917</strong></span>
        </div>
    </div>
    <div class="contract-number">Contrat de location n° : <span class="line-dotted">{contract_number}</span></div>
    
    <div class="flex-row">
        <div class="col-3">
            <h3 class="section-header">Informations du locataire (premier conducteur)</h3>
            <div class="field-group"><label>Nom et prénom :</label><span class="line-dotted">{c1_name}</span></div>
            <div class="field-group"><label>Date et lieu de naissance :</label><span class="line-dotted">{c1_birth}</span></div>
            <div class="field-group"><label>Adresse :</label><span class="line-dotted">{c1_address}</span></div>
            <div class="field-group"><label>N° permis de conduire :</label><span class="line-dotted">{c1_license}</span></div>
            <div class="field-group"><label>Délivré le :</label><span class="line-dotted">{c1_license_date}</span></div>
            <div class="field-group"><label>Téléphone :</label><span class="line-dotted">{c1_phone}</span></div>
            
            <h4 style="font-size:9.5pt;color:#004080;margin:6px 0 2px;border-top:1px dashed #ced4da;padding-top:2px;">Deuxième conducteur (supplémentaire) :</h4>
            <div class="field-group"><label>Nom et prénom :</label><span class="line-dotted">{c2_name}</span></div>
            <div class="field-group"><label>Adresse :</label><span class="line-dotted">{c2_address}</span></div>
            <div class="field-group"><label>Date et lieu de naissance :</label><span class="line-dotted">{c2_birth}</span></div>
            <div class="field-group"><label>N° permis de conduire :</label><span class="line-dotted">{c2_license}</span></div>
            <div class="field-group"><label>Délivré le :</label><span class="line-dotted">{c2_license_date}</span></div>
        </div>
        
        <div class="col-2">
            <h3 class="section-header">Détails de la durée de location</h3>
            <table>
                <tr><th></th><th>Départ</th><th>Retour</th></tr>
                <tr><td>Kilométrage</td><td>{km_depart}</td><td>{km_return}</td></tr>
                <tr><td>Carburant</td><td>{fuel_depart}</td><td></td></tr>
                <tr><td>Durée de location</td><td colspan="2">{jours} jours</td></tr>
                <tr><td>Date</td><td style="color:green;">{date_depart}</td><td style="color:red;">{date_return}</td></tr>
                <tr><td>Heure</td><td>{time_depart}</td><td>{time_depart}</td></tr>
            </table>
        </div>
    </div>
    
    <div class="section-header">Caractéristiques du véhicule et aspect financier</div>
    <table>
        <tr><th>Immatriculation</th><th>Date de départ</th><th>Catégorie</th><th>Marque</th><th>Prix 24h</th><th>Nombre de jours</th><th>Réductions</th><th>Prix total</th></tr>
        <tr style="height: 50px;"><td style="font-weight: bold;">{plate}</td><td>{date_depart}</td><td style="font-weight: bold;">{brand}</td><td style="font-weight: bold;">{model}</td><td>{price_per_day}</td><td>{days}</td><td>{discount}</td><td>{total_price}</td></tr>
    </table>
    
    <div class="section-header">État du véhicule (indication des dommages et rayures)</div>
    <div class="condition-row">
        <div class="condition-box"><span>Au départ</span>
            <div class="car-img-container"><img src="car22.png" alt="Voiture"></div>
        </div>
        <div class="condition-box"><span>Au retour</span>
            <div class="car-img-container"><img src="car22.png" alt="Voiture"></div>
        </div>
    </div>
    
    <div class="bottom-row">
        <div class="box">
            <h4>Accessoires du véhicule remis</h4>
            <div class="accessories-header">
                <span>Description</span><span>Oui</span><span>Non</span>
            </div>
            {accessories_html_fr}
        </div>
        
        <div class="box">
         <div style="position: relative; background-color: rgba(255, 0, 0, 0.15); border: 1px solid #ff0000; border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; text-align: right; direction: rtl;">
            <h4 style="margin: 0 0 10px 0; color: #d00000; font-size: 14pt; text-align: center;"> Avertissement important ⚠️</h4>
            <p style="margin: 0; font-size: 7pt; line-height: 1.5;font-weight: bold; color: #333;">


            <p style="margin: 0; font-size: 7pt; line-height: 1.5; font-weight: bold; color: #333;">
            Le kilométrage autorisé par l’agence est de 300 km pour une durée de 24 heures. En cas de dépassement du plafond fixé dans le contrat, le locataire est tenu de payer 20 DA pour chaque kilomètre supplémentaire. La durée de location est de 24 heures. En cas de retard dans la restitution du véhicule à l’heure prévue, le locataire devra s’acquitter de 600 DA pour une heure, 1 500 DA pour deux heures, 2 400 DA pour trois heures. Au-delà de trois heures de retard, une journée complète de location sera facturée.
            </p>
        </div>
        </div>
    </div>
    
    <div class="signatures">
        <div class="sig-box"><div class="sig-line">Cachet et signature de l'agence</div></div>
        <div class="sig-box"><div class="sig-line">Signature du premier conducteur et empreinte</div></div>
        <div class="sig-box"><div class="sig-line">Signature du second conducteur et empreinte</div></div>
    </div>
</div>

<!-- ====================== Page 2 - Conditions ====================== -->
<div class="page">
    <h1 class="terms-title">Conditions générales du contrat de location de véhicule</h1>
    <div class="terms-content">
        <div class="terms-column">
            <p class="term"><span class="term-number">01</span> Le locataire et le conducteur supplémentaire éventuel doivent présenter une copie de leur carte d’identité nationale ou de leur passeport ainsi qu’une copie de leur permis de conduire, tous en cours de validité, au loueur pour identification conformément à la loi.</p>
            <p class="term"><span class="term-number">02</span> Le véhicule n’est loué qu’aux personnes âgées d’au moins 25 ans et titulaires d’un permis de conduire depuis plus de 24 mois, calculés à partir de la date de délivrance, et valable du moment de la location jusqu’au retour du véhicule.</p>
            <p class="term"><span class="term-number">03</span> Le locataire doit, avant de signer le contrat et avant de quitter l’agence, inspecter le véhicule et déclarer les défauts et imperfections existants.</p>
            <p class="term"><span class="term-number">04</span> La responsabilité civile incombe uniquement au locataire s’il n’a pas déclaré les défauts et imperfections qu’il a constatés sur le véhicule avant de quitter l’agence.</p>
            <p class="term"><span class="term-number">05</span> Le loueur et le locataire doivent signer un annexe au contrat de location dans laquelle sont obligatoirement consignées toutes les observations résultant de l’inspection du véhicule à la fin de la période de location.</p>
            <p class="term"><span class="term-number">06</span> Le locataire doit respecter les lois et règlements relatifs à la circulation, porter son permis de conduire ainsi que les documents relatifs au véhicule remis par le loueur, et respecter les règles d’utilisation du véhicule.</p>
            <p class="term"><span class="term-number">07</span> La conduite du véhicule n’est autorisée qu’au locataire et au second conducteur éventuel ayant signé le contrat de location ; en cas de dommage, ils sont solidairement responsables des dommages causés au véhicule.</p>
            <p class="term"><span class="term-number">08</span> Si une autre personne souhaite conduire le véhicule sans être partie au contrat, elle doit obligatoirement se présenter à l’agence pour ajouter son nom à l’annexe du contrat et approuver toutes les conditions du contrat aux côtés du locataire, afin qu’ils soient solidairement responsables de tout dommage éventuel au véhicule.</p>
            <p class="term"><span class="term-number">09</span> Le locataire doit garer le véhicule dans un endroit sécurisé, bien fermer les portes, activer l’alarme si elle existe, et il lui est interdit de laisser les clés à l’intérieur du véhicule, quelles que soient les circonstances.</p>
            <p class="term"><span class="term-number">10</span> Le locataire ne doit pas utiliser le véhicule pour transporter des marchandises, qu’elles soient interdites ou non par la loi, ni pour transporter des passagers, avec ou sans contrepartie.</p>
            <p class="term"><span class="term-number">11</span> Le locataire ne doit pas utiliser le véhicule pour des courses, pour tracter ou remorquer des véhicules, des remorques ou tout autre moyen, avec ou sans roues, ni utiliser le véhicule loué à des fins autres que celles prévues.</p>
            <p class="term"><span class="term-number">12</span> Le locataire ne doit pas conduire le véhicule après avoir consommé des boissons alcoolisées ou des substances hallucinogènes, sous peine d’engager sa responsabilité civile.</p>
            <p class="term"><span class="term-number">13</span> Le locataire ne doit pas utiliser le véhicule loué pour l’apprentissage de la conduite.</p>
            <p class="term"><span class="term-number">14</span> Le locataire ne doit pas vendre, mettre en gage ou aliéner le véhicule ou ses accessoires à des fins personnelles.</p>
            <p class="term"><span class="term-number">15</span> Le locataire ne doit pas ajouter ou modifier aucun dispositif du véhicule loué.</p>
            <p class="term"><span class="term-number">16</span> Le locataire assume l’entière responsabilité en cas de vol du véhicule ou de ses accessoires, ou en cas de vandalisme résultant de sa négligence et de son manque de prudence.</p>
 
        </div>
        <div class="terms-column">
                       
            <p class="term"><span class="term-number">17</span> Le locataire doit déclarer immédiatement aux autorités compétentes tout vol du véhicule ou de ses accessoires et remettre une copie du procès-verbal de déclaration au loueur, sous peine de poursuites pour vol et abus de confiance.</p>
            <p class="term"><span class="term-number">18</span> Le locataire doit indemniser la valeur du véhicule au loueur si celui-ci n’est pas retrouvé dans un délai de 30 jours à compter de la date de déclaration de vol.</p>

            <p class="term"><span class="term-number">19</span> En cas de dommages matériels au véhicule alors qu’il est sous la garde du locataire, ce dernier supporte intégralement les frais de réparation ainsi que les frais résultant de l’immobilisation du véhicule à l’atelier.</p>
            <p class="term"><span class="term-number">20</span> Le locataire doit payer les frais de stationnement du véhicule à la fourrière en cas de saisie par les autorités compétentes.</p>
            <p class="term"><span class="term-number">21</span> Le locataire doit informer le loueur de toute panne mécanique survenant sur le véhicule, sous peine d’engager sa responsabilité contractuelle et délictuelle.</p>
            <p class="term"><span class="term-number">22</span> Le locataire est responsable de tout dommage au véhicule s’il ne le restitue pas à la date de fin du contrat ; en cas de souhait de prolongation, il doit se présenter sans délai à l’agence pour régulariser sa situation.</p>
            <p class="term"><span class="term-number">23</span> Le loueur a la faculté d’exiger un montant de 30 000 DA (trente mille dinars algériens) en espèces ou par chèque signé par le locataire, pour couvrir les éventuels dommages au véhicule, en plus de la carte d’identité nationale ou du passeport pour les expatriés, à titre de garantie.</p>
            <p class="term"><span class="term-number">24</span> La durée de location est de 24 heures ; en cas de retard dans la restitution du véhicule à l’heure convenue, le locataire doit payer 600 DA pour une (1) heure, 1 500 DA pour deux (2) heures, 2 400 DA pour trois (3) heures, et au-delà de trois heures, le prix d’une journée complète.</p>
            <p class="term"><span class="term-number">25</span> Le forfait kilométrique autorisé par l’agence pour 24 heures est de 300 km ; en cas de dépassement du forfait prévu au contrat, le locataire doit payer vingts dinars algériens (20 DA) par kilomètre supplémentaire.</p>
            <p class="term"><span class="term-number">26</span> Le locataire doit remplir le réservoir de carburant lors de la restitution du véhicule avec la même quantité et le même type que lors du départ de l’agence, sous peine d’engager sa pleine responsabilité civile en cas de panne due à un changement de type de carburant ou à sa mauvaise qualité.</p>
            <p class="term"><span class="term-number">27</span> Le locataire doit restituer le véhicule à la fin du contrat de location ou à la fin de la période de prolongation, sans retard, propre et rangé, avec les lumières éteintes, les portes fermées, et le garer correctement conformément au code de la route.</p>
            <p class="term"><span class="term-number">28</span> Le contrat de location est établi par écrit en deux exemplaires signés par les parties contractantes ; le loueur s’engage à remettre un exemplaire au locataire et à conserver le second pour preuve conformément à la loi.</p>
            <p class="term"><span class="term-number">29</span> En cas de prolongation du contrat de location, la prolongation est approuvée et signée par les parties sur le même contrat de location, dans l’espace prévu à cet effet.</p>
            <p class="term"><span class="term-number">30</span> Les parties au contrat doivent signer l’annexe au contrat de location contenant toutes les observations résultant de l’inspection du véhicule après la fin de la période de location ou de la prolongation.</p>
            <p class="term"><span class="term-number">31</span> En cas de litige, le tribunal de Nedroma est seul compétent territorialement pour statuer sur le litige qui lui est soumis.</p>
        </div>
    </div>
    
    <div class="signatures" style="margin-top:20px;">
        <div class="sig-box"><div class="sig-line">Signature du loueur (agence)</div></div>
        <div class="sig-box"><div class="sig-line">Locataire principal : lu et approuvé</div></div>
        <div class="sig-box"><div class="sig-line">Locataire secondaire : lu et approuvé</div></div>
    </div>
</div>

<script>
    document.querySelectorAll('label.modern-checkbox').forEach(l => {{
        l.addEventListener('click', e => {{
            e.preventDefault();
            const input = document.getElementById(l.getAttribute('for'));
            const name = input.name;
            if (name) {{
                document.querySelectorAll(`input[name="${{name}}"]`).forEach(i => {{
                    if (i !== input) {{ i.checked = false; document.querySelector(`label[for="${{i.id}}"]`).classList.remove('checked'); }}
                }});
            }}
            input.checked = !input.checked;
            l.classList.toggle('checked', input.checked);
        }});
    }});
</script>
</body>
</html>
"""

        # Remplacements identiques
        # (même série de .replace() que dans get_facture_html, mais sur html_fr)
        html_fr = html_fr.replace("{contract_number}", contract_number)
        html_fr = html_fr.replace("{c1_name}", c1_name)
        html_fr = html_fr.replace("{c1_birth}", c1_birth)
        html_fr = html_fr.replace("{c1_address}", c1_address or "")
        html_fr = html_fr.replace("{c1_license}", c1_license or "")
        html_fr = html_fr.replace("{c1_license_date}", c1_license_date)
        html_fr = html_fr.replace("{c1_phone}", c1_phone or "")
        html_fr = html_fr.replace("{c2_name}", c2_name)
        html_fr = html_fr.replace("{c2_address}", c2_address)
        html_fr = html_fr.replace("{c2_birth}", c2_birth)
        html_fr = html_fr.replace("{c2_license}", c2_license)
        html_fr = html_fr.replace("{c2_license_date}", c2_license_date)
        html_fr = html_fr.replace("{km_depart}", km_depart)
        html_fr = html_fr.replace("{km_return}", km_return)
        html_fr = html_fr.replace("{fuel_depart}", fuel_depart)
        html_fr = html_fr.replace("{fuel_return}", fuel_return)
        html_fr = html_fr.replace("{date_depart}", date_depart)
        html_fr = html_fr.replace("{date_return}", date_return)
        html_fr = html_fr.replace("{time_depart}", time_depart)
        html_fr = html_fr.replace("{time_return}", time_return or "")
        html_fr = html_fr.replace("{plate}", plate)
        html_fr = html_fr.replace("{brand}", brand)
        html_fr = html_fr.replace("{model}", model)
        html_fr = html_fr.replace("{price_per_day}", price_per_day)
        html_fr = html_fr.replace("{days}", days)
        html_fr = html_fr.replace("{discount}", discount)
        html_fr = html_fr.replace("{total_price}", total_price)
        html_fr = html_fr.replace("{insurance_company}", insurance_company)
        html_fr = html_fr.replace("{insurance_policy}", insurance_policy)
        html_fr = html_fr.replace("{check_number}", check_number)
        html_fr = html_fr.replace("{check_date}", check_date)
        html_fr = html_fr.replace("{deposit_amount}", deposit_amount)
        html_fr = html_fr.replace("{bank}", bank)
        # === NEW: Replace insurance & payment fields ===
        html_fr = html_fr.replace("{insurance_company}", insurance_company)
        html_fr = html_fr.replace("{insurance_policy}", insurance_policy)
        html_fr = html_fr.replace("{check_number}", check_number)
        html_fr = html_fr.replace("{check_date}", check_date)
        html_fr = html_fr.replace("{deposit_amount}", deposit_amount)
        html_fr = html_fr.replace("{bank}", bank)
        html_fr = html_fr.replace("{pay_cash_checked}", pay_cash_checked)
        html_fr = html_fr.replace("{pay_check_checked}", pay_check_checked)
        html_fr = html_fr.replace("{pay_cash_class}", pay_cash_class)
        html_fr = html_fr.replace("{pay_check_class}", pay_check_class)
        html_fr = html_fr.replace("{g_cash_checked}", g_cash_checked)
        html_fr = html_fr.replace("{g_check_checked}", g_check_checked)
        html_fr = html_fr.replace("{g_cash_class}", g_cash_class)
        html_fr = html_fr.replace("{g_check_class}", g_check_class)
        # === Dynamic checkboxes for payment method ===
        if payment_method == "Cash":
            html_fr = html_fr.replace('id="pay_cash" name="pay" checked', 'id="pay_cash" name="pay" checked')
            html_fr = html_fr.replace('id="pay_check" name="pay">', 'id="pay_check" name="pay">')
        else:  # Check
            html_fr = html_fr.replace('id="pay_cash" name="pay" checked', 'id="pay_cash" name="pay">')
            html_fr = html_fr.replace('id="pay_check" name="pay">', 'id="pay_check" name="pay" checked')

        # === Dynamic checkboxes for deposit method ===
        if deposit_method == "Cash":
            html_fr = html_fr.replace('id="g_cash" name="g" checked', 'id="g_cash" name="g" checked')
            html_fr = html_fr.replace('id="g_check" name="g">', 'id="g_check" name="g">')
        else:  # Check
            html_fr = html_fr.replace('id="g_cash" name="g" checked', 'id="g_cash" name="g">')
            html_fr = html_fr.replace('id="g_check" name="g">', 'id="g_check" name="g" checked')

        # Replace accessories
        html_fr = html_fr.replace("{accessories_html}", accessories_html_fr)  # si tu gardes le placeholder
        return html_fr

    def print_from_webview(self, webview):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        printer.setOutputFormat(QPrinter.NativeFormat)

        def handle_print(success):
            if not success:
                QMessageBox.warning(self, "Erreur", "Échec de l'impression")

        webview.page().print(printer, handle_print)

    def print_facture(self, facture_id):
        self.cursor.execute("SELECT location_id FROM factures WHERE id = ?", (facture_id,))
        location_id = self.cursor.fetchone()[0]
        html = self.get_facture_html(location_id)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)

        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            view = QWebEngineView()

            # الحل هنا أيضًا
            base_url = QUrl.fromLocalFile(os.path.join(get_app_path(), "").replace("\\", "/"))
            view.setHtml(html, base_url)

            def do_print():
                view.page().print(printer, lambda success: None)
            view.loadFinished.connect(do_print)


    def setup_parametres_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#f8fafc; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(40))
        layout.setSpacing(self.scale(25))

        # ================== TITRE PRINCIPAL ==================
        title = QLabel("Paramètres de l'Agence")
        title.setStyleSheet(f"font-size: {self.scale_font(32)}px; font-weight: 800; color: #1e293b; padding-bottom: {self.scale(10)}px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ================== SECTION SÉCURITÉ ==================
        security_card = QWidget()
        security_card.setStyleSheet(f"""
            background: white; border-radius: {self.scale(20)}px; padding: {self.scale(30)}px;
            margin-top: {self.scale(25)}px; border-left: {self.scale(6)}px solid #dc2626;
            box-shadow: 0 {self.scale(10)}px {self.scale(25)}px rgba(0,0,0,0.08);
        """)
        sec_layout = QVBoxLayout(security_card)
        sec_layout.setSpacing(self.scale(18))

        sec_title = QLabel("Sécurité • Changer les Identifiants de Connexion")
        sec_title.setStyleSheet(f"font-size: {self.scale_font(22)}px; font-weight: bold; color: #dc2626;")
        sec_layout.addWidget(sec_title)

        sec_grid = QGridLayout()
        sec_grid.setSpacing(self.scale(15))

        sec_grid.addWidget(QLabel("Nouveau nom d'utilisateur :"), 1, 0)
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("Laissez vide pour ne pas changer")
        self.new_username.setStyleSheet(f"padding: {self.scale(14)}px {self.scale(16)}px; font-size: {self.scale_font(15)}px; border: 2px solid #e2e8f0; border-radius: {self.scale(12)}px; background: #f9fafb;")
        sec_grid.addWidget(self.new_username, 1, 1)

        sec_grid.addWidget(QLabel("Nouveau mot de passe :"), 2, 0)
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Laissez vide pour ne pas changer")
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setStyleSheet(self.new_username.styleSheet())
        sec_grid.addWidget(self.new_password, 2, 1)

        sec_layout.addLayout(sec_grid)

        change_btn = QPushButton("Changer les Identifiants")
        change_btn.setStyleSheet(f"""
            background: #dc2626; color: white; padding: {self.scale(16)}px {self.scale(32)}px;
            border-radius: {self.scale(12)}px; font-size: {self.scale_font(16)}px; font-weight: bold;
            margin-top: {self.scale(15)}px;
        """)
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.clicked.connect(self.change_login_credentials)
        sec_layout.addWidget(change_btn, alignment=Qt.AlignCenter)

        layout.addWidget(security_card)

        # ================== INFORMATIONS AGENCE ==================
        info_card = QWidget()
        info_card.setStyleSheet(f"""
            background: white; border-radius: {self.scale(20)}px; padding: {self.scale(30)}px;
            border-left: {self.scale(6)}px solid #1d4ed8; box-shadow: 0 {self.scale(10)}px {self.scale(25)}px rgba(0,0,0,0.08);
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(self.scale(18))

        subtitle1 = QLabel("Informations de l'Agence")
        subtitle1.setStyleSheet(f"font-size: {self.scale_font(22)}px; font-weight: bold; color: #1e40af;")
        info_layout.addWidget(subtitle1)

        form_grid = QGridLayout()
        form_grid.setSpacing(self.scale(15))
        form_grid.setColumnStretch(1, 1)

        labels = ["Nom de l'Agence", "Propriétaire", "Téléphone", "Adresse Complète"]
        self.settings_nom_agence = QLineEdit(self.settings.get("nom_agence", "LOCATOP"))
        self.settings_proprietaire = QLineEdit(self.settings.get("proprietaire", "Aissaoui Abdelkader"))
        self.settings_telephone = QLineEdit(self.settings.get("telephone", "0775868765"))
        self.settings_adresse = QLineEdit(self.settings.get("adresse", "05 تجمع 30 الخريبة ندرومة"))

        fields = [self.settings_nom_agence, self.settings_proprietaire, self.settings_telephone, self.settings_adresse]

        for i, (txt, field) in enumerate(zip(labels, fields)):
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"font-size: {self.scale_font(15)}px; font-weight: 600; color: #374151;")
            field.setStyleSheet(f"""
                padding: {self.scale(14)}px {self.scale(16)}px; font-size: {self.scale_font(15)}px;
                border: 2px solid #e2e8f0; border-radius: {self.scale(12)}px; background: #f9fafb;
            """)
            form_grid.addWidget(lbl, i, 0)
            form_grid.addWidget(field, i, 1)

        info_layout.addLayout(form_grid)

        save_btn = QPushButton("Enregistrer les Modifications")
        save_btn.setStyleSheet(f"""
            background: #1d4ed8; color: white; padding: {self.scale(16)}px {self.scale(32)}px;
            border-radius: {self.scale(12)}px; font-size: {self.scale_font(16)}px; font-weight: bold;
            min-width: {self.scale(280)}px; margin-top: {self.scale(20)}px;
        """)
        save_btn.clicked.connect(self.save_settings)
        info_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        layout.addWidget(info_card)

        # ================== EXPORT & SAUVEGARDE ==================
        tools_card = QWidget()
        tools_card.setStyleSheet(f"""
            background: white; border-radius: {self.scale(20)}px; padding: {self.scale(30)}px;
            box-shadow: 0 {self.scale(10)}px {self.scale(25)}px rgba(0,0,0,0.08);
        """)
        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setSpacing(self.scale(20))

        subtitle2 = QLabel("Export & Sauvegarde")
        subtitle2.setStyleSheet(f"font-size: {self.scale_font(22)}px; font-weight: bold; color: #1e40af;")
        tools_layout.addWidget(subtitle2)

        # --- Boutons d'export ---
        export_grid = QGridLayout()
        export_grid.setSpacing(self.scale(15))

        exports = [
            ("Exporter Clients", "#7c3aed", self.export_clients_pdf),
            ("Exporter Voitures", "#059669", self.export_voitures_pdf),
            ("Exporter Factures", "#dc2626", self.export_factures_pdf),
            ("Exporter Réservations", "#f59e0b", self.export_reservations_pdf),
        ]

        for i, (text, color, func) in enumerate(exports):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                background: {color}; color: white; padding: {self.scale(16)}px;
                border-radius: {self.scale(14)}px; font-size: {self.scale_font(15)}px; font-weight: bold;
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(func)
            export_grid.addWidget(btn, i // 2, i % 2)

        tools_layout.addLayout(export_grid)

        # --- Sauvegarde & Import ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(self.scale(20))

        backup_btn = QPushButton("Sauvegarder la Base de Données")
        backup_btn.setStyleSheet(f"background: #1e293b; color: white; padding: {self.scale(14)}px; border-radius: {self.scale(12)}px; font-weight: bold;")
        backup_btn.clicked.connect(self.backup_database)
        btn_row.addWidget(backup_btn)

        import_btn = QPushButton("Importer une Base de Données")
        import_btn.setStyleSheet(f"background: #0891b2; color: white; padding: {self.scale(14)}px; border-radius: {self.scale(12)}px; font-weight: bold;")
        import_btn.clicked.connect(self.import_database)
        btn_row.addWidget(import_btn)

        reset_btn = QPushButton("Réinitialiser Complètement")
        reset_btn.setStyleSheet(f"background: #dc2626; color: white; padding: {self.scale(14)}px; border-radius: {self.scale(12)}px; font-weight: bold;")
        reset_btn.clicked.connect(self.reset_database)
        btn_row.addWidget(reset_btn)

        tools_layout.addLayout(btn_row)
        layout.addWidget(tools_card)

        # --- Crédits ---
        footer = QLabel(" ProLoc v1.0  •  Powered by MSD")
        footer.setStyleSheet(f"color: #64748b; font-size: {self.scale_font(14)}px; margin-top: {self.scale(20)}px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
        layout.addStretch()

        # Remplacer la page
        if self.content_stack.count() > 7:
            old = self.content_stack.widget(7)
            self.content_stack.removeWidget(old)
            old.deleteLater()

        scroll.setWidget(page)
        self.content_stack.insertWidget(7, scroll)


    # ====================== FONCTION D'IMPORT DE BASE DE DONNÉES ======================
    def import_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importer une Base de Données", "", "SQLite Database (*.db *.sqlite *.sqlite3)"
        )
        if not file_path:
            return

        reply = QMessageBox.question(
            self, "Confirmer l'import",
            "Attention : cela écrasera toutes les données actuelles !\nVoulez-vous continuer ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.conn.close()
            import shutil
            shutil.copyfile(file_path, get_db_path())

            # Reconnecter
            self.conn = sqlite3.connect(get_db_path())
            self.cursor = self.conn.cursor()

            # Recharger tout
            self.load_settings()
            self.load_voitures()
            self.load_clients()
            self.load_locations()
            self.load_reservations()
            self.load_frais()
            self.load_factures()
            self.update_dashboard_stats()

            QMessageBox.information(self, "Succès", "Base de données importée avec succès !\nL'application va redémarrer.")
            QTimer.singleShot(1000, self.restart_app)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de l'import :\n{str(e)}")

    def restart_app(self):
        self.close()
        QTimer.singleShot(500, lambda: os.execl(sys.executable, sys.executable, *sys.argv))


    # ====================== EXPORTS PDF AMÉLIORÉS (mise en page propre) ======================

    def export_clients_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter Clients PDF", "clients.pdf", "PDF Files (*.pdf)")
        if not file_path: 
            return
        
        # ← ENREGISTRER LA POLICE ARABE
        has_arabic = register_arabic_font()
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ← UTILISER LA POLICE ARABE SI DISPONIBLE
        if has_arabic:
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Title'],
                fontName='Arabic',
                fontSize=18,
                alignment=TA_CENTER
            )
            normal_style = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_RIGHT
            )
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']

        elements.append(Paragraph("Liste des Clients", title_style))
        elements.append(Paragraph(f"Exporté le {date.today().strftime('%d/%m/%Y')}", normal_style))
        elements.append(Paragraph("<br/><br/>", normal_style))

        self.cursor.execute("""
            SELECT nom, prenom, genre, date_naissance, lieu_naissance,
                adresse, numero_permis, date_permis, telephone 
            FROM clients
        """)
        
        data = [["Nom", "Prénom", "Genre", "Naissance", "Lieu", "Adresse", "Permis", "Délivré le", "Téléphone"]]
        
        for row in self.cursor.fetchall():
            # ← PRÉPARER CHAQUE CELLULE AVEC TEXTE ARABE
            processed_row = []
            for cell in row:
                if cell and isinstance(cell, str):
                    # Vérifier si le texte contient de l'arabe
                    if any('\u0600' <= c <= '\u06FF' for c in cell):
                        processed_row.append(prepare_arabic_text(cell))
                    else:
                        processed_row.append(cell)
                else:
                    processed_row.append(cell or "")
            data.append(processed_row)

        table = Table(data, colWidths=[60,60,40,60,70,90,70,60,70])
        
        # ← STYLE AVEC POLICE ARABE
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,1), (-1,-1), 9),
        ]
        
        if has_arabic:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Arabic'),
                ('FONTNAME', (0,1), (-1,-1), 'Arabic'),
            ])
        else:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ])
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        doc.build(elements)
        QMessageBox.information(self, "Succès", "Clients exportés en PDF avec succès.")


    # ========== MÊME CHOSE POUR LES AUTRES EXPORTS ==========

    def export_voitures_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter Voitures PDF", "voitures.pdf", "PDF Files (*.pdf)")
        if not file_path: 
            return
        
        has_arabic = register_arabic_font()
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
        styles = getSampleStyleSheet()
        
        if has_arabic:
            title_style = ParagraphStyle('ArabicTitle', parent=styles['Title'], fontName='Arabic', fontSize=18, alignment=TA_CENTER)
            normal_style = ParagraphStyle('ArabicNormal', parent=styles['Normal'], fontName='Arabic', fontSize=10)
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']
        
        elements = [
            Paragraph("Liste des Voitures", title_style), 
            Paragraph(f"Exporté le {date.today().strftime('%d/%m/%Y')}<br/><br/>", normal_style)
        ]

        self.cursor.execute("SELECT numero_matricule, modele, brand, statut, prix_jour FROM voitures")
        data = [["Matricule", "Modèle", "Marque", "Statut", "Prix/Jour (DA)"]]
        
        for row in self.cursor.fetchall():
            processed = []
            for cell in row:
                if isinstance(cell, str) and any('\u0600' <= c <= '\u06FF' for c in cell):
                    processed.append(prepare_arabic_text(cell))
                elif isinstance(cell, float):
                    processed.append(f"{cell:.2f}")
                else:
                    processed.append(str(cell) if cell else "")
            data.append(processed)

        table = Table(data, colWidths=[100,100,80,70,80])
        
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,1), (-1,-1), 10),
        ]
        
        if has_arabic:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,-1), 'Arabic'),
            ])
        else:
            table_style.append(('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'))
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        doc.build(elements)
        QMessageBox.information(self, "Succès", "Voitures exportées en PDF avec succès.")


    def export_factures_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter Factures PDF", "factures.pdf", "PDF Files (*.pdf)")
        if not file_path: 
            return
        
        # ← ENREGISTRER LA POLICE ARABE
        has_arabic = register_arabic_font()
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ← UTILISER LA POLICE ARABE SI DISPONIBLE
        if has_arabic:
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Title'],
                fontName='Arabic',
                fontSize=18,
                alignment=TA_CENTER
            )
            normal_style = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_RIGHT
            )
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']

        elements.append(Paragraph("Liste des Factures", title_style))
        elements.append(Paragraph(f"Exporté le {date.today().strftime('%d/%m/%Y')}", normal_style))
        elements.append(Paragraph("<br/><br/>", normal_style))

        self.cursor.execute("""
            SELECT f.id, v.modele, c.nom || ' ' || c.prenom, 
                l.date_heure_location, l.cout_total
            FROM factures f
            JOIN locations l ON f.location_id = l.id
            JOIN voitures v ON l.voiture_id = v.id
            JOIN clients c ON l.client_id = c.id
        """)
        
        data = [["ID", "Véhicule", "Client", "Date Location", "Montant (DA)"]]
        
        for row in self.cursor.fetchall():
            # ← PRÉPARER CHAQUE CELLULE AVEC TEXTE ARABE
            processed_row = []
            for i, cell in enumerate(row):
                if cell and isinstance(cell, str):
                    # Vérifier si le texte contient de l'arabe
                    if any('\u0600' <= c <= '\u06FF' for c in cell):
                        processed_row.append(prepare_arabic_text(cell))
                    else:
                        # Date : extraire uniquement YYYY-MM-DD (enlever l'heure)
                        if i == 3 and ' ' in cell:  # colonne date_heure_location
                            processed_row.append(cell.split()[0])
                        else:
                            processed_row.append(cell)
                elif isinstance(cell, float):
                    processed_row.append(f"{cell:.2f}")
                else:
                    processed_row.append(str(cell) if cell else "")
            
            data.append(processed_row)

        table = Table(data, colWidths=[50, 100, 120, 90, 80])
        
        # ← STYLE AVEC POLICE ARABE
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,1), (-1,-1), 9),
        ]
        
        if has_arabic:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Arabic'),
                ('FONTNAME', (0,1), (-1,-1), 'Arabic'),
            ])
        else:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ])
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        doc.build(elements)
        QMessageBox.information(self, "Succès", "Factures exportées en PDF avec succès.")


    def export_reservations_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter Réservations PDF", "reservations.pdf", "PDF Files (*.pdf)")
        if not file_path: 
            return
        
        # ← ENREGISTRER LA POLICE ARABE
        has_arabic = register_arabic_font()
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ← UTILISER LA POLICE ARABE SI DISPONIBLE
        if has_arabic:
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Title'],
                fontName='Arabic',
                fontSize=18,
                alignment=TA_CENTER
            )
            normal_style = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_RIGHT
            )
        else:
            title_style = styles['Title']
            normal_style = styles['Normal']

        elements.append(Paragraph("Liste des Réservations Actives", title_style))
        elements.append(Paragraph(f"Exporté le {date.today().strftime('%d/%m/%Y')}", normal_style))
        elements.append(Paragraph("<br/><br/>", normal_style))

        self.cursor.execute("""
            SELECT r.id, v.modele, c.nom || ' ' || c.prenom, 
                r.date_debut, r.jours, r.cout_total, r.payment_percentage
            FROM reservations r
            JOIN voitures v ON r.voiture_id = v.id
            JOIN clients c ON r.client_id = c.id
            WHERE r.statut = 'Active'
        """)
        
        data = [["ID", "Véhicule", "Client", "Date Début", "Jours", "Total (DA)", "% Payé"]]
        
        for row in self.cursor.fetchall():
            # ← PRÉPARER CHAQUE CELLULE AVEC TEXTE ARABE
            processed_row = []
            for i, cell in enumerate(row):
                if cell and isinstance(cell, str):
                    # Vérifier si le texte contient de l'arabe
                    if any('\u0600' <= c <= '\u06FF' for c in cell):
                        processed_row.append(prepare_arabic_text(cell))
                    else:
                        processed_row.append(cell)
                elif isinstance(cell, float):
                    # Colonne 5 (cout_total) : afficher en DA
                    if i == 5:
                        processed_row.append(f"{cell:.2f}")
                    # Colonne 6 (payment_percentage) : afficher en %
                    elif i == 6:
                        processed_row.append(f"{cell}%")
                    else:
                        processed_row.append(f"{cell:.2f}")
                else:
                    processed_row.append(str(cell) if cell else "")
            
            data.append(processed_row)

        table = Table(data, colWidths=[50, 100, 120, 80, 60, 80, 60])
        
        # ← STYLE AVEC POLICE ARABE
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,1), (-1,-1), 9),
        ]
        
        if has_arabic:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Arabic'),
                ('FONTNAME', (0,1), (-1,-1), 'Arabic'),
            ])
        else:
            table_style.extend([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ])
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        doc.build(elements)
        QMessageBox.information(self, "Succès", "Réservations exportées en PDF avec succès.")

    def change_login_credentials(self):
        new_user = self.new_username.text().strip()
        new_pass = self.new_password.text()

        if not new_user and not new_pass:
            QMessageBox.warning(self, "Attention", "Veuillez remplir au moins un champ.")
            return

        if new_user:
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('login_username', ?)", (new_user,))
        
        if new_pass:
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('login_password', ?)", (new_pass,))

        self.conn.commit()
        QMessageBox.information(self, "Succès", 
            f"Identifiants mis à jour !\n"
            f"Nouveau utilisateur : {new_user if new_user else '(inchangé)'}\n"
            f"Mot de passe : {'●●●●●●●●' if new_pass else '(inchangé)'}\n\n"
            f"Les nouveaux identifiants seront requis au prochain redémarrage.")
        
        # Vider les champs
        self.new_username.clear()
        self.new_password.clear()


    def save_settings(self):
        # Sauvegarde les infos de l'agence
        self.cursor.execute("UPDATE settings SET value = ? WHERE key = 'nom_agence'", (self.settings_nom_agence.text().strip(),))
        self.cursor.execute("UPDATE settings SET value = ? WHERE key = 'proprietaire'", (self.settings_proprietaire.text().strip(),))
        self.cursor.execute("UPDATE settings SET value = ? WHERE key = 'telephone'", (self.settings_telephone.text().strip(),))
        self.cursor.execute("UPDATE settings SET value = ? WHERE key = 'adresse'", (self.settings_adresse.text().strip(),))

        # Sauvegarde les identifiants de connexion (si tu as ajouté la section sécurité)
        if hasattr(self, 'new_username') and self.new_username.text().strip():
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('login_username', ?)", (self.new_username.text().strip(),))
        
        if hasattr(self, 'new_password') and self.new_password.text():
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('login_password', ?)", (self.new_password.text(),))

        self.conn.commit()
        self.load_settings()

        # Mise à jour du dashboard (titre agence)
        self.update_dashboard_stats()

        QMessageBox.information(self, "Succès", "Tous les paramètres ont été enregistrés avec succès !")



    def backup_database(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder Base de Données", "rentcar_backup.db", "SQLite Database (*.db)")
        if file_path:
            self.conn.commit()
            shutil.copy("rentcar.db", file_path)
            QMessageBox.information(self, "Succès", "Base de données sauvegardée avec succès.")

    def reset_database(self):
        reply = QMessageBox.question(self, "Confirmer", "Voulez-vous réinitialiser la base de données ? Tous les données seront perdues.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.conn.close()
            db_path = get_db_path()
            if os.path.exists(db_path):
                os.remove(db_path)
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            initialize_database(self.conn, self.cursor)  # ← Correction : appeler la fonction globale
            self.load_settings()
            self.load_voitures()
            self.load_clients()
            self.load_locations()
            self.load_reservations()
            self.load_frais()
            self.load_factures()
            self.update_dashboard_stats()
            QMessageBox.information(self, "Succès", "Base de données réinitialisée.")

    def show_dashboard(self):
        self.content_stack.setCurrentIndex(0)
        self.update_dashboard_stats()
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["dashboard"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_voitures(self):
        self.content_stack.setCurrentIndex(1)
        self.load_voitures()
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["voitures"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_clients(self):
        self.content_stack.setCurrentIndex(2)
        self.load_clients()
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["clients"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_location(self):
        self.content_stack.setCurrentIndex(3)
        self.update_car_statuses()
        self.load_locations()
        self.load_voitures_combo(self.location_voiture_combo)  # Ajout: Recharge les voitures disponibles
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["location"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_reservations(self):
        self.content_stack.setCurrentIndex(4)
        self.update_car_statuses()
        self.load_reservations()
        self.load_voitures_combo(self.res_voiture_combo)  # Ajout: Recharge pour réservations (ajuste le nom du combo si différent)# Ajout: Recharge les voitures disponibles
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["reservations"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_frais(self):
        self.content_stack.setCurrentIndex(5)
        self.load_frais()
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["frais"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_factures(self):
        self.content_stack.setCurrentIndex(6)
        self.load_factures()
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["factures"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def show_parametres(self):
        self.content_stack.setCurrentIndex(7)
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        self.sidebar_buttons["parametres"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")

    def adjust_ui_size(self):
        # Cette fonction ajuste l'UI pour qu'elle ait la même taille relative sur différentes résolutions
        # Elle est appelée dans __init__ et dans resizeEvent si nécessaire
        # Exemples d'ajustements (étendre à tous les éléments si besoin)
        self.sidebar.setFixedWidth(self.scale(260))
        # Ajuster les fonts et tailles pour d'autres éléments (ex: dans dashboard)
        # Note: Dans les setup_... , j'ai déjà remplacé les nombres fixes par self.scale(...)
        # Si plus d'ajustements dynamiques sont nécessaires, les ajouter ici

    def resizeEvent(self, event):
        self.adjust_ui_size()
        return super().resizeEvent(event)

    def setup_stats_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background:#ffffff; border:none; }")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(30))
        layout.setSpacing(self.scale(20))

        # Title
        title = QLabel("Statistiques Financières")
        title.setStyleSheet(f"font-size:{self.scale_font(26)}px; font-weight:800; color:#111827;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Filter Section
        filter_widget = QWidget()
        filter_widget.setStyleSheet(f"""
            QWidget {{
                background:white; 
                border-radius:{self.scale(16)}px; 
                padding:{self.scale(20)}px; 
                border:1px solid #e5e7eb;
            }}
        """)

        filter_layout = QGridLayout(filter_widget)
        filter_layout.setSpacing(self.scale(15))

        # Car Selector
        self.stats_car_combo = QComboBox()
        self.stats_car_combo.setStyleSheet(f"padding: {self.scale(12)}px; border: 1px solid #d1d5db; border-radius: {self.scale(8)}px; font-size: {self.scale_font(14)}px;")
        self.load_voitures_combo(self.stats_car_combo)
        self.stats_car_combo.insertItem(0, "📊 TOUTES LES VOITURES", None)
        self.stats_car_combo.setCurrentIndex(0)

        # Date Pickers
        date_style = f"padding: {self.scale(12)}px; border: 1px solid #d1d5db; border-radius: {self.scale(8)}px; font-size: {self.scale_font(14)}px;"
        
        self.stats_date_start = QDateEdit()
        self.stats_date_start.setCalendarPopup(True)
        self.stats_date_start.setDate(QDate.currentDate().addMonths(-1))
        self.stats_date_start.setStyleSheet(date_style)

        self.stats_date_end = QDateEdit()
        self.stats_date_end.setCalendarPopup(True)
        self.stats_date_end.setDate(QDate.currentDate())
        self.stats_date_end.setStyleSheet(date_style)

        # Calculate Button
        calc_btn = QPushButton("Calculer")
        calc_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: #2563eb; color: white; font-weight: bold; 
                padding: {self.scale(12)}px {self.scale(24)}px; 
                border-radius: {self.scale(8)}px; 
                font-size: {self.scale_font(14)}px; 
            }}
            QPushButton:hover {{ background: #1d4ed8; }}
        """)
        calc_btn.clicked.connect(self.calculate_stats)

        # Add to Grid
        l1 = QLabel("Voiture :")
        l1.setStyleSheet(f"font-size:{self.scale_font(14)}px; font-weight:bold;")
        filter_layout.addWidget(l1, 0, 0)
        filter_layout.addWidget(self.stats_car_combo, 0, 1)
        
        l2 = QLabel("Du :")
        l2.setStyleSheet(f"font-size:{self.scale_font(14)}px; font-weight:bold;")
        filter_layout.addWidget(l2, 0, 2)
        filter_layout.addWidget(self.stats_date_start, 0, 3)
        
        l3 = QLabel("Au :")
        l3.setStyleSheet(f"font-size:{self.scale_font(14)}px; font-weight:bold;")
        filter_layout.addWidget(l3, 0, 4)
        filter_layout.addWidget(self.stats_date_end, 0, 5)
        
        filter_layout.addWidget(calc_btn, 1, 0, 1, 6, alignment=Qt.AlignCenter)

        layout.addWidget(filter_widget)

        # Results Section (Cards)
        results_widget = QWidget()
        results_layout = QGridLayout(results_widget)
        results_layout.setSpacing(self.scale(20))

        # Helper to create cards
        def create_card(title, color, icon_text):
            card = QWidget()
            card.setStyleSheet(f"""
                QWidget {{ background: white; border-bottom: {self.scale(4)}px solid {color}; border-radius: {self.scale(12)}px; }}
            """)
            card.setMinimumHeight(self.scale(140))
            
            l = QVBoxLayout(card)
            l.setContentsMargins(self.scale(20), self.scale(20), self.scale(20), self.scale(20))
            
            header = QLabel(title)
            # border:none added to prevent inheriting border from parent QWidget selector
            header.setStyleSheet(f"color: #6b7280; font-size: {self.scale_font(14)}px; font-weight: 600; text-transform: uppercase; border:none; background:transparent;")
            
            value = QLabel("0.00 DA")
            value.setStyleSheet(f"color: {color}; font-size: {self.scale_font(32)}px; font-weight: 900; margin-top: {self.scale(10)}px; border:none; background:transparent;")
            value.setAlignment(Qt.AlignRight)
            
            l.addWidget(header)
            l.addWidget(value)
            return card, value

        self.card_revenus, self.lbl_revenus = create_card("Revenus Locations", "#059669", "💰")
        self.card_rep, self.lbl_rep = create_card("Coût Réparations", "#dc2626", "🔧")
        self.card_fuel, self.lbl_fuel = create_card("Coût Carburant", "#d97706", "⛽")
        self.card_profit, self.lbl_profit = create_card("Bénéfice Net", "#2563eb", "📈")

        results_layout.addWidget(self.card_revenus, 0, 0)
        results_layout.addWidget(self.card_rep, 0, 1)
        results_layout.addWidget(self.card_fuel, 1, 0)
        results_layout.addWidget(self.card_profit, 1, 1)

        layout.addWidget(results_widget)
        layout.addStretch()

        self.content_stack.addWidget(scroll)

    def calculate_stats(self):
        voiture_id = self.stats_car_combo.currentData()
        start_date = self.stats_date_start.date().toString("yyyy-MM-dd")
        end_date = self.stats_date_end.date().toString("yyyy-MM-dd")

        try:
            # Base Where clauses
            where_loc = "date(date_heure_location) BETWEEN ? AND ?"
            where_rep = "date(date_completion) BETWEEN ? AND ?"
            where_fuel = "date(date) BETWEEN ? AND ?"
            params = [start_date, end_date]

            # If a specific car is selected, add filter
            if voiture_id is not None:
                where_loc = "voiture_id = ? AND " + where_loc
                where_rep = "voiture_id = ? AND " + where_rep
                where_fuel = "voiture_id = ? AND " + where_fuel
                params.insert(0, voiture_id)

            # 1. Revenus
            self.cursor.execute(f"SELECT SUM(cout_total) FROM locations WHERE {where_loc}", tuple(params))
            res = self.cursor.fetchone()
            revenus = res[0] if res and res[0] else 0.0

            # 2. Réparations
            self.cursor.execute(f"SELECT SUM(cout) FROM reparations WHERE {where_rep}", tuple(params))
            res = self.cursor.fetchone()
            reparations = res[0] if res and res[0] else 0.0

            # 3. Carburant
            self.cursor.execute(f"SELECT SUM(montant) FROM fuel_costs WHERE {where_fuel}", tuple(params))
            res = self.cursor.fetchone()
            carburant = res[0] if res and res[0] else 0.0

            profit = revenus - (reparations + carburant)

            self.lbl_revenus.setText(f"{revenus:,.2f} DA")
            self.lbl_rep.setText(f"{reparations:,.2f} DA")
            self.lbl_fuel.setText(f"{carburant:,.2f} DA")
            self.lbl_profit.setText(f"{profit:,.2f} DA")
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du calcul : {str(e)}")

    def show_stats(self):
        self.content_stack.setCurrentIndex(8)
        for key, btn in self.sidebar_buttons.items():
            btn.setStyleSheet("color: white;  padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")
        if "stats" in self.sidebar_buttons:
            self.sidebar_buttons["stats"].setStyleSheet("color: white; background-color: #1d4ed8; padding: 10px; margin: 5px; border-radius: 5px; font-size: 16px;")


if __name__ == '__main__':
    import ctypes
    import hashlib
    import platform

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # ==================== HIGH DPI SCALING SUPPORT (FIXED) ====================
    # Disable auto scaling to force physical pixels usage (1920x1080)
    # This ensures consistent layout on laptops with 125%/150% scaling
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    if hasattr(Qt, 'AA_DisableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
    
    # Force 1.0 scale factor to ignore Windows scaling settings
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # -------------------------------------------------------------------
    #                 🔐 SIMPLE PC-LOCKED ACTIVATION SYSTEM
    # -------------------------------------------------------------------

    LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".proloc_license.dat")
    VALID_CODES = ["DMC345SDSD1111", "X9Y8Z7", "K5M3P1"]

    def get_pc_id():
        base = f"{platform.node()}{platform.processor()}{os.getenv('USERNAME', '')}"
        return hashlib.sha256(base.encode()).hexdigest()[:32]

    def is_activated():
        if not os.path.exists(LICENSE_FILE):
            return False
        try:
            with open(LICENSE_FILE, "r") as f:
                saved = f.read().strip()
            pcid = get_pc_id()
            for code in VALID_CODES:
                if hashlib.sha256(f"{pcid}|{code}".encode()).hexdigest() == saved:
                    return True
        except:
            return False
        return False

    def save_activation(code):
        try:
            with open(LICENSE_FILE, "w") as f:
                f.write(hashlib.sha256(f"{get_pc_id()}|{code}".encode()).hexdigest())
            return True
        except:
            return False

    def show_activation_dialog():
        dlg = QDialog()
        dlg.setWindowTitle("Activation Requise")
        dlg.setFixedSize(self.scale(420), self.scale(300))
        dlg.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: white;
                border-radius: 20px;
            }
            QLabel {
                color: #94a3b8;
                font-size: 16px;
            }
            QLineEdit {
                padding: 4px;
                background: #1e293b;
                border: 2px solid #1e293b;
                border-radius: 14px;
                color: white;
                font-size: 16px;
            }
            QPushButton {
                background: #3b82f6;
                color: white;
                padding: 8px;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #60a5fa;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("PROLOC")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 48px; color: #60a5fa; font-weight: 900; letter-spacing: 2px;")
        layout.addWidget(title)

        subtitle = QLabel("Activation du logiciel requise")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px; color: #94a3b8;")
        layout.addWidget(subtitle)

        # Input
        code_inp = QLineEdit()
        code_inp.setPlaceholderText("Exemple : 147345")
        layout.addWidget(code_inp)

        # Button
        btn = QPushButton("Activer")
        layout.addWidget(btn)

        # Error label
        error = QLabel("")
        error.setAlignment(Qt.AlignCenter)
        error.setStyleSheet("color:#ff4444; font-size:15px;")
        layout.addWidget(error)

        def activate():
            code = code_inp.text().strip().upper()

            if code not in VALID_CODES:
                error.setText("Code d'activation invalide")
                return

            if save_activation(code):
                QMessageBox.information(dlg, "Succès", "Activation réussie !")
                dlg.accept()
            else:
                error.setText("Erreur lors de la sauvegarde")

        btn.clicked.connect(activate)

        return dlg.exec_() == QDialog.Accepted


    # ---- CHECK ACTIVATION BEFORE ANYTHING ELSE ----
    if not is_activated():
        if not show_activation_dialog():
            sys.exit(0)



    # -------------------------------------------------------------------
    #                   DATABASE CREATION (ORIGINAL)
    # -------------------------------------------------------------------

    if not os.path.exists(get_db_path()):
        conn_temp = sqlite3.connect(get_db_path())
        cur_temp = conn_temp.cursor()
        initialize_database(conn_temp, cur_temp)
        conn_temp.close()

    os.makedirs(os.path.dirname(get_db_path()), exist_ok=True)

    # -------------------------------------------------------------------
    #              APP ICON + WINDOWS TASKBAR IDENTIFIER
    # -------------------------------------------------------------------

    logo = resource_path("logo.png")
    if os.path.exists(logo):
        app.setWindowIcon(QIcon(logo))
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ProLoc.RentCar.2025")
        except:
            pass


    # Helper function for global scaling
    def scale_value(val):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        base_width = 1920
        base_height = 1080
        scale_factor = min(screen.width() / base_width, screen.height() / base_height)
        scale_factor = max(0.5, scale_factor)
        return int(val * scale_factor)

    # -------------------------------------------------------------------
    #                          SPLASH SCREEN
    # -------------------------------------------------------------------

    splash = QLabel()
    splash.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    splash.setStyleSheet("background:black;")
    splash.setFixedSize(scale_value(900), scale_value(506))
    splash.setAlignment(Qt.AlignCenter)

    gif = resource_path("splashh.gif")
    movie = QMovie(gif) if os.path.exists(gif) else None
    if movie and movie.isValid():
        movie.setScaledSize(splash.size())
        splash.setMovie(movie)
        movie.start()

    screen = QGuiApplication.primaryScreen().availableGeometry()
    splash.move((screen.width() - scale_value(900)) // 2, (screen.height() - scale_value(506)) // 2)
    splash.show()


    # -------------------------------------------------------------------
    #                          LOGIN WINDOW
    # -------------------------------------------------------------------

    class LoginForm(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("ProLoc - Connexion")
            self.setFixedSize(scale_value(420), scale_value(520))
            self.setStyleSheet("background:#0f172a; color:white; border-radius:20px;")

            layout = QVBoxLayout(self)
            layout.setContentsMargins(40, 40, 40, 40)
            layout.setSpacing(25)

            title = QLabel("PROLOC", self)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("font-size:52px; color:#60a5fa; font-weight:900; letter-spacing:2px;")
            layout.addWidget(title)

            subtitle = QLabel("Connexion Administrateur", self)
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setStyleSheet("color:#94a3b8; font-size:18px;")
            layout.addWidget(subtitle)

            self.user = QLineEdit()
            self.user.setPlaceholderText("Nom d'utilisateur")
            self.user.setStyleSheet(
                "padding:16px; background:#1e293b; border:2px solid #1e293b; "
                "border-radius:14px; color:white; font-size:16px;"
            )

            self.passwd = QLineEdit()
            self.passwd.setPlaceholderText("Mot de passe")
            self.passwd.setEchoMode(QLineEdit.Password)
            self.passwd.setStyleSheet(self.user.styleSheet())

            btn = QPushButton("Se connecter")
            btn.setStyleSheet("background:#3b82f6; color:white; padding:18px; border-radius:16px; font-size:18px; font-weight:bold;")
            btn.clicked.connect(self.check)

            self.error = QLabel("")
            self.error.setAlignment(Qt.AlignCenter)
            self.error.setStyleSheet("color:#ff4444; font-size:15px;")

            layout.addWidget(self.user)
            layout.addWidget(self.passwd)
            layout.addWidget(btn)
            layout.addWidget(self.error)

        def check(self):
            conn = sqlite3.connect(get_db_path())
            cur = conn.cursor()

            cur.execute("SELECT value FROM settings WHERE key='login_username'")
            u = cur.fetchone()
            cur.execute("SELECT value FROM settings WHERE key='login_password'")
            p = cur.fetchone()
            conn.close()

            username = (u[0] if u else "admin")
            password = (p[0] if p else "admin")

            if self.user.text() == username and self.passwd.text() == password:
                self.accept()
            else:
                self.error.setText("Identifiants incorrects")


    # -------------------------------------------------------------------
    #                      LAUNCH MAIN APPLICATION
    # -------------------------------------------------------------------

    def start_app():
        if movie:
            movie.stop()
        splash.close()

        login = LoginForm()
        if login.exec_() == QDialog.Accepted:
            win = RentCarApp()
            win.showMaximized()
        else:
            app.quit()

    if movie and movie.isValid():
        movie.frameChanged.connect(lambda f: movie.frameCount() - 1 == f and start_app())
    else:
        QTimer.singleShot(1000, start_app)

    sys.exit(app.exec_())
