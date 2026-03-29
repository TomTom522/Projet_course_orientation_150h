import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineCore import QWebEngineProfile

# Importation de tes modules
from gui_modules.dashboard_page import DashboardPage
from gui_modules.config_page import ConfigPage  
from gui_modules.history_page import HistoryPage
from gui_modules.equipe_page import EquipePage
from gui_modules.scenario_page import ScenarioPage
from mon_lora import LoraThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Supervision LoRa - Logiciels de supervision")
        self.resize(1280, 800)
        
        # --- STYLE GLOBAL ---
        self.setStyleSheet("""
            QMainWindow { background-color: #f4f7f6; }
            QFrame#Header { 
                background-color: white; 
                border-bottom: 2px solid #e2e8f0; 
            }
            QPushButton#NavBtn {
                background-color: transparent;
                color: #64748b;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border: none;
                border-bottom: 3px solid transparent;
                border-radius: 0px;
            }
            QPushButton#NavBtn:hover {
                color: #27ae60;
                background-color: #f1f8f5;
            }
            QPushButton#NavBtn:checked {
                color: #27ae60;
                border-bottom: 3px solid #27ae60;
                background-color: transparent;
            }
        """)

        # Widget Principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. HEADER (Menu de navigation) ---
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        # Logo / Titre à gauche
        logo = QLabel("Charles Carnus LoRa")
        logo.setStyleSheet("font-weight: 900; color: #1e293b; font-size: 18px; margin-right: 20px;")
        h_layout.addWidget(logo)
        
        h_layout.addStretch()

        # Boutons de navigation
        self.btn_config = QPushButton("Configuration Balises")
        self.btn_equipe = QPushButton("Inscriptions Équipes")
        self.btn_scenario = QPushButton("Scénarios")
        self.btn_dash = QPushButton("Dashboard Live")
        self.btn_history = QPushButton("Historique")

        # Liste des boutons pour appliquer le style et la logique
        self.nav_buttons = [self.btn_config, self.btn_equipe,self.btn_scenario, self.btn_dash, self.btn_history]

        for btn in self.nav_buttons:
            btn.setObjectName("NavBtn")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedWidth(220)
            btn.setFixedHeight(68) # Presque toute la hauteur du header
            h_layout.addWidget(btn)

        h_layout.addStretch()
        main_layout.addWidget(header)

        # --- 2. STACKED WIDGET ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Initialisation des pages
        self.page_config = ConfigPage()     
        self.page_equipe = EquipePage()
        self.page_scenario = ScenarioPage()
        self.page_dashboard = DashboardPage()
        self.page_history = HistoryPage()
        self.page_dashboard.nouveau_log_signal.connect(self.page_history.add_log)
        
        # Ajout au stack (L'ordre définit l'index)
        self.stack.addWidget(self.page_config)    # Index 0
        self.stack.addWidget(self.page_equipe)    # Index 1
        self.stack.addWidget(self.page_scenario)  # index 2
        self.stack.addWidget(self.page_dashboard) # Index 3
        self.stack.addWidget(self.page_history)   # Index 4

        # --- 3. CONNEXIONS DES BOUTONS ---
        self.btn_config.clicked.connect(lambda: self.switch_page(0))
        self.btn_equipe.clicked.connect(lambda: self.switch_page(1))
        self.btn_scenario.clicked.connect(lambda: self.switch_page(2))
        self.btn_dash.clicked.connect(lambda: self.switch_page(3))
        self.btn_history.clicked.connect(lambda: self.switch_page(4))

        # Page par défaut au démarrage (Dashboard Live)
        self.switch_page(3)

        # --- 4. LANCEMENT DU THREAD LORA ---
        self.start_lora_communication()

    def switch_page(self, index):
        """Change la page affichée et gère l'apparence des boutons"""
        self.stack.setCurrentIndex(index)
        
        # Désactive tous les boutons sauf celui cliqué
        self.btn_config.setChecked(index == 0)
        self.btn_equipe.setChecked(index == 1)
        self.btn_scenario.setChecked(index == 2)
        self.btn_dash.setChecked(index == 3)
        self.btn_history.setChecked(index == 4)

    def start_lora_communication(self):
        """Initialise et lance la lecture du port série via le thread"""
        self.thread = LoraThread()
        self.thread.position_signal.connect(self.handle_gps)
        self.thread.battery_signal.connect(self.handle_battery)
        self.thread.status_signal.connect(self.handle_status)
        
        # --- Connexion du signal RFID ---
        self.thread.rfid_signal.connect(self.handle_rfid)
        
        # --- Pré-remplir le formulaire de création de balise ---
        self.thread.position_signal.connect(self.page_config.pre_remplir_donnees_lora)
        
        self.thread.start()

    # --- HANDLERS ---
    def handle_gps(self, lat, lon, balise_id):
        # 1. Mise à jour du Dashboard
        self.page_dashboard.update_dashboard_data(lat, lon, None, balise_id)
        # 2. Ajout dans l'historique (Couleur bleue)
        self.page_history.add_log(balise_id, "Position GPS", f"Lat: {lat:.5f}, Lon: {lon:.5f}", "#2980b9")

    def handle_battery(self, val_str):
        try:
            val_int = int(val_str.replace("%", "").strip())
            # 1. Mise à jour du Dashboard
            self.page_dashboard.update_dashboard_data(None, None, val_int, "Balise")
            
            # 2. Ajout dans l'historique (Couleur orange/rouge si faible, vert si ok)
            color = "#e67e22" if val_int < 30 else "#27ae60"
            self.page_history.add_log("Balise", "Niveau Batterie", f"{val_int}% restants", color)
        except:
            pass
            
    def handle_status(self, text, color):
        if hasattr(self.page_dashboard, 'card_deco'):
            status = "CONNECTÉ" in text
            self.page_dashboard.card_deco.set_status(status)
            self.page_dashboard.card_deco.lbl_text.setText("Connecté (USB)" if status else "Déconnecté")
            
            # Ajout dans l'historique (Couleur noire/grise)
            self.page_history.add_log("Système", "Statut USB LoRa", text, "#7f8c8d")

    # --- Réception du badge RFID ---
    def handle_rfid(self, code_rfid):
        # 1. On sauvegarde le code et on l'envoie à l'interface Équipe
        self.page_equipe.dernier_rfid_recu = code_rfid
        self.page_equipe.remplir_rfid() # Déclenche l'affichage visuel
        
        # 2. Ajout dans l'historique (Couleur Violette pour bien le voir)
        self.page_history.add_log("Scanner LoRa", "Lecture Badge RFID", f"Code scanné : {code_rfid}", "#8e44ad")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpUserAgent("CourseDorientationBTSCIEL/1.0 (wederel412@qvmao.com)")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())