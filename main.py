import sys
import json
import os
from datetime import datetime
import serial.tools.list_ports
import config

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QStackedWidget, QLabel, 
                             QFrame, QComboBox, QDialog, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineCore import QWebEngineProfile

# Importation de tes modules
from gui_modules import login_connexions 
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
            /* Style pour le menu déroulant des ports */
            QComboBox {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: bold;
                color: #334155;
            }
            QComboBox::drop-down { border: none; }
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

        # bouton de déconnexion
        self.btn_logout = QPushButton("Déconnexion")
        self.btn_logout.setObjectName("NavBtn") 
        self.btn_logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_logout.setStyleSheet("color: #e74c3c; font-weight: bold;") # Bouton en rouge pour le différencier des autres
        
        # On le connecte à notre future fonction
        self.btn_logout.clicked.connect(self.se_deconnecter)

        # Liste des boutons pour appliquer le style et la logique
        self.nav_buttons = [self.btn_config, self.btn_equipe, self.btn_scenario, self.btn_dash, self.btn_history]

        for btn in self.nav_buttons:
            btn.setObjectName("NavBtn")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedWidth(220)
            btn.setFixedHeight(68) # Presque toute la hauteur du header
            h_layout.addWidget(btn)

        h_layout.addStretch()
        
        # --- AJOUT DU MENU DÉROULANT DES PORTS COM ---
        self.combo_ports = QComboBox()
        self.combo_ports.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_ports.setFixedWidth(150)
        h_layout.addWidget(self.combo_ports)
        
        # On remplit la liste
        self.rafraichir_ports_com()
        # On connecte le changement à notre fonction
        self.combo_ports.currentTextChanged.connect(self.changer_port_com)

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
        self.btn_config.clicked.connect(lambda: self.changer_page(0))
        self.btn_equipe.clicked.connect(lambda: self.changer_page(1))
        self.btn_scenario.clicked.connect(lambda: self.changer_page(2))
        self.btn_dash.clicked.connect(lambda: self.changer_page(3))
        self.btn_history.clicked.connect(lambda: self.changer_page(4))

        # Page par défaut au démarrage (Dashboard Live)
        self.changer_page(3)

        # --- 4. LANCEMENT DU THREAD LORA ---
        self.lancer_lora_communication()

    def rafraichir_ports_com(self):
        """Scanne les ports USB et remplit la liste déroulante"""
        # On désactive la détection le temps de remplir pour ne pas déclencher 50 fois l'événement
        self.combo_ports.blockSignals(True)
        self.combo_ports.clear()
        
        self.combo_ports.addItem("SIMULATEUR")
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)
            
        if config.SERIAL_PORT in [self.combo_ports.itemText(i) for i in range(self.combo_ports.count())]:
            self.combo_ports.setCurrentText(config.SERIAL_PORT)
            
        self.combo_ports.blockSignals(False)

    def changer_port_com(self, nouveau_port):
        """Met à jour la configuration et relance le thread"""
        if nouveau_port:
            config.SERIAL_PORT = nouveau_port
            print(f"[*] Port modifié, redémarrage sur : {nouveau_port}")
            
            # On arrête proprement le thread actuel
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.stop()
            
            # On relance (la fonction recrée le thread et reconnecte les signaux)
            self.lancer_lora_communication()

    def changer_page(self, index):
        """Change la page affichée et gère l'apparence des boutons"""
        self.stack.setCurrentIndex(index)
        
        # Désactive tous les boutons sauf celui cliqué
        self.btn_config.setChecked(index == 0)
        self.btn_equipe.setChecked(index == 1)
        self.btn_scenario.setChecked(index == 2)
        self.btn_dash.setChecked(index == 3)
        self.btn_history.setChecked(index == 4)

    def lancer_lora_communication(self):
        """Initialise et lance la lecture du port série via le thread"""
        self.thread = LoraThread()
        self.thread.position_signal.connect(self.gerer_gps)
        self.thread.battery_signal.connect(self.gerer_batterie)
        self.thread.status_signal.connect(self.gerer_status)
        
        # --- Connexion du signal RFID ---
        self.thread.rfid_signal.connect(self.gerer_rfid)
        
        # --- Pré-remplir le formulaire de création de balise ---
        self.thread.position_signal.connect(self.page_config.pre_remplir_donnees_lora)
        
        self.thread.start()

    def se_deconnecter(self):
        """Gère la déconnexion de l'utilisateur."""
        import sys
        from PyQt6.QtWidgets import QDialog
        from gui_modules import login_connexions
        
        # 1. On efface le token de la mémoire
        config.JWT_TOKEN = None
        
        # 2. On cache la fenêtre principale
        self.hide()
        
        # 3. On affiche à nouveau la fenêtre de connexion
        login_window = login_connexions()
        resultat = login_window.exec()
        
        # 4. On vérifie ce que l'utilisateur fait
        if resultat == QDialog.DialogCode.Accepted:
            # S'il se reconnecte (succès), on réaffiche le tableau de bord
            self.show()
            
            # rafraichir les tableaux pour le nouvel utilisateur connecté
            self.page_equipe.charger_equipes_api() 
        else:
            # S'il clique sur la croix rouge de la fenêtre de login, on ferme tout
            sys.exit()    

    # --- MÉTHODES DE GESTION DES SIGNAUX ---
    def gerer_gps(self, lat, lon, balise_id):
        # 1. Mise à jour du Dashboard
        self.page_dashboard.update_dashboard_data(lat, lon, None, balise_id)
        # 2. Ajout dans l'historique (Couleur bleue)
        self.page_history.add_log(balise_id, "Position GPS", f"Lat: {lat:.5f}, Lon: {lon:.5f}", "#2980b9")

    def gerer_batterie(self, val_str):
        try:
            val_int = int(val_str.replace("%", "").strip())
            # 1. Mise à jour du Dashboard
            self.page_dashboard.update_dashboard_data(None, None, val_int, "Balise")
            
            # 2. Ajout dans l'historique (Couleur orange/rouge si faible, vert si ok)
            color = "#e67e22" if val_int < 30 else "#27ae60"
            self.page_history.add_log("Balise", "Niveau Batterie", f"{val_int}% restants", color)
        except:
            pass
            
    def gerer_status(self, text, color):
        if hasattr(self.page_dashboard, 'card_deco'):
            status = "CONNECTÉ" in text
            self.page_dashboard.card_deco.set_status(status)
            self.page_dashboard.card_deco.lbl_text.setText("Connecté (USB)" if status else "Déconnecté")
            
            # Ajout dans l'historique (Couleur noire/grise)
            self.page_history.add_log("Système", "Statut USB LoRa", text, "#7f8c8d")

    # --- Réception du badge RFID ---
    def gerer_rfid(self, balise_id, code_rfid):
        # 1. Enregistrement dans le fichier JSON (Historique) de façon robuste
        dossier_courant = os.path.dirname(os.path.abspath(__file__))
        dossier_transfer = os.path.join(dossier_courant, 'transfer')
        
        # On crée le dossier 'transfer' s'il n'existe pas
        if not os.path.exists(dossier_transfer):
            os.makedirs(dossier_transfer)
            
        chemin_fichier = os.path.join(dossier_transfer, 'donnees_rfid.json')
        
        donnees = []
        if os.path.exists(chemin_fichier):
            try:
                with open(chemin_fichier, 'r', encoding='utf-8') as f:
                    donnees = json.load(f)
            except:
                pass
        
        nouvelle_lecture = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "node_id": balise_id, # On utilise le vrai ID !
            "rfid_tag": code_rfid
        }
        donnees.append(nouvelle_lecture)
        
        with open(chemin_fichier, 'w', encoding='utf-8') as f:
            json.dump(donnees, f, indent=4)

        # 2. Mise à jour de l'interface
        self.page_equipe.dernier_rfid_recu = code_rfid
        self.page_equipe.remplir_rfid()
        
        # 3. Ajout dans le tableau historique avec le vrai ID
        self.page_history.add_log(f"Balise {balise_id}", "Détection RFID", f"Badge {code_rfid} scanné", "#8e44ad")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # lance la fêntre de connexions
    login_window = login_connexions.LoginDialog()
    
    # 2. Si l'utilisateur se connecte avec succès (self.accept() a été appelé)
    if login_window.exec() == QDialog.DialogCode.Accepted:
        
        # 3. Alors on lance le tableau de bord principal
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent("CourseDorientationBTSCIEL/1.0 (wederel412@qvmao.com)")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        # Si l'utilisateur clique sur la croix rouge pour fermer le login
        sys.exit()