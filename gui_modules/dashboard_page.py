import math
import requests
import config
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QFrame, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from gui_modules.map_page import MapPage

class StatusCard(QFrame):
    def __init__(self, text): 
        super().__init__()
        self.setFixedSize(160, 90)
        self.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 10px; } QLabel { border: none; background: transparent; }")
        layout = QVBoxLayout(self)
        self.lbl_text = QLabel(text)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_text.setStyleSheet("font-weight: bold; font-size: 13px; color: #334155;")
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(5)
        self.status_bar.setStyleSheet("background-color: #cbd5e1; border-radius: 2px; border: none;")
        layout.addWidget(self.lbl_text)
        layout.addWidget(self.status_bar)
        

    def set_status(self, is_ok):
        color = "#27ae60" if is_ok else "#e74c3c"
        self.status_bar.setStyleSheet(f"background-color: {color}; border-radius: 2px; border: none;")


class Cartemeteo(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(350)
        self.setFixedHeight(120)
        self.setStyleSheet("""
            QFrame { 
                background-color: #34C25A; 
                border-radius: 8px; 
                color: white;
                margin: 2px;
            }
            QLabel { border: none; background: transparent; color: white; }
        """)
        
        layout = QHBoxLayout(self)
        
        # Section Gauche : Icone et Température
        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(self.lbl_temp)

        # Section Droite : Détails de la météo
        details_layout = QVBoxLayout()
        self.lbl_city = QLabel("Météo à Rodez")
        self.lbl_city.setStyleSheet("font-weight: bold; font-size: 18px;")
        self.lbl_desc = QLabel("Chargement...")
        self.lbl_desc.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_wind = QLabel("Vent: -- km/h")
        self.lbl_wind.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_hum = QLabel("Humidité: --%")
        self.lbl_hum.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        details_layout.addWidget(self.lbl_city)
        details_layout.addWidget(self.lbl_desc)
        details_layout.addWidget(self.lbl_wind)
        details_layout.addWidget(self.lbl_hum)
        layout.addLayout(details_layout)

class DashboardPage(QWidget):
    # Permet d'envoyer les logs à la page Historique globale !
    nouveau_log_signal = pyqtSignal(str, str, str, str)

    def __init__(self):
        super().__init__()
        self.last_map_update = 0
        self.setStyleSheet("background-color: #f4f7f6;") 
        self.ancrage_position = None  
        self.distance_limite = 20.0   
        self.team_rows = {}           
        self.balise_cards = {} 
        self.current_balise_widgets = []
        
        self.equipes_etat_precedent = {} 
        self.alertes_mouvement = {}      
        self.alertes_batterie = {}       

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        
        left_panel_container = QWidget()
        left_panel_container.setFixedWidth(380) 
        left_layout = QVBoxLayout(left_panel_container)
        left_layout.setContentsMargins(0, 0, 10, 0)

        header_h = QHBoxLayout()
        lbl_dash = QLabel("Live Monitoring")
        lbl_dash.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")
        
        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px; border: none; } QPushButton:hover { background-color: #2980b9; }")
        self.btn_refresh.clicked.connect(self.charger_balises_api)
        
        header_h.addWidget(lbl_dash)
        header_h.addStretch()
        header_h.addWidget(self.btn_refresh)
        left_layout.addLayout(header_h)
        left_layout.addSpacing(10)

        self.weather_card = Cartemeteo()  # ajout de la meteo
        left_layout.addWidget(self.weather_card)
        left_layout.addSpacing(15)


        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: transparent;")
        self.left_grid = QGridLayout(self.grid_widget)
        self.left_grid.setContentsMargins(0, 0, 0, 0)
        self.left_grid.setSpacing(12)
        

        self.scroll_area.setWidget(self.grid_widget)
        left_layout.addWidget(self.scroll_area)
        top_layout.addWidget(left_panel_container)

        map_container = QFrame()
        map_container.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 12px;")
        map_l = QVBoxLayout(map_container)
        map_l.setContentsMargins(5, 5, 5, 5)
        
        self.map_widget = MapPage()
        map_l.addWidget(self.map_widget)
        
        top_layout.addWidget(map_container, stretch=1)
        main_layout.addWidget(top_section, stretch=2)

        # Section du bas avec l'intégration du bouton
        bottom_section = QWidget()
        bottom_layout = QHBoxLayout(bottom_section)

        self.table_team = self.create_table(["Equipe/Balise", "Latitude", "Longitude", "Batterie", "Scenario"])
        vbox1 = QVBoxLayout()
        
        header_tables = QHBoxLayout()
        header_tables.addWidget(QLabel("Dernieres coordonnees", styleSheet="font-weight:bold; color:#334155"))
        header_tables.addStretch()
        
        self.btn_refresh_bottom = QPushButton("Actualiser les tableaux")
        self.btn_refresh_bottom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_bottom.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #219653; }")
        self.btn_refresh_bottom.clicked.connect(self.charger_donnees_tableaux)
        header_tables.addWidget(self.btn_refresh_bottom)
        
        vbox1.addLayout(header_tables)
        vbox1.addWidget(self.table_team)
        
        self.table_log = self.create_table(["Heure", "Source", "Evenement", "Detail"])
        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Journal local", styleSheet="font-weight:bold; color:#334155"))
        vbox2.addWidget(self.table_log)

        bottom_layout.addLayout(vbox1, stretch=1)
        bottom_layout.addLayout(vbox2, stretch=1)
        main_layout.addWidget(bottom_section, stretch=1)

        self.charger_balises_api()
        self.charger_donnees_tableaux() # Chargement au lancement

        self.mise_a_jour_meteo() # Lance la météo immédiatement
        self.timer_meteo = QTimer(self)
        self.timer_meteo.timeout.connect(self.mise_a_jour_meteo)
        self.timer_meteo.start(3600000) # Mise à jour toutes les heures (3600s * 1000ms)

        self.ajouter_log(datetime.now().strftime("%H:%M:%S"), "Système", "Démarrage", "Dashboard initialisé avec succès", "#3498db")

    def create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setRowCount(0)
        table.setStyleSheet("QHeaderView::section { background-color: #f8fafc; color: #475569; padding: 8px; font-weight: bold; border: none; border-bottom: 3px solid #27ae60; } QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; color: #1e293b; }")
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def ajouter_log(self, heure, source, evenement, detail, couleur="#1e293b"):
        self.table_log.insertRow(0)
        self.table_log.setItem(0, 0, QTableWidgetItem(heure))
        self.table_log.setItem(0, 1, QTableWidgetItem(source))
        item_evt = QTableWidgetItem(evenement)
        item_evt.setForeground(QColor(couleur))
        self.table_log.setItem(0, 2, item_evt)
        self.table_log.setItem(0, 3, QTableWidgetItem(detail))
        if self.table_log.rowCount() > 50:
            self.table_log.removeRow(50)
            
        #On envoie ce log vers la page Historique globale 
        self.nouveau_log_signal.emit(source, evenement, detail, couleur)


    def mise_a_jour_meteo(self):
        api_key = "a6f6fef1470f473cb0694459230605"
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q=Rodez&lang=fr"
        
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                curr = data['current']
                
                self.weather_card.lbl_temp.setText(f"{curr['temp_c']}°C")
                self.weather_card.lbl_desc.setText(curr['condition']['text'])
                self.weather_card.lbl_wind.setText(f"Vent: {curr['wind_kph']} km/h")
                self.weather_card.lbl_hum.setText(f"Humidité: {curr['humidity']}%")
        except Exception as e:
            print(f"Erreur météo: {e}")


    def charger_balises_api(self):
        for card in self.current_balise_widgets:
            self.left_grid.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
            
        self.current_balise_widgets.clear()
        self.balise_cards.clear()
        
        url = f"{config.API_URL}/api/balises"
        headers = {"Authorization": f"ApiKey {config.API_KEY}"}
        self.btn_refresh.setText("Chargement...")
        self.btn_refresh.setEnabled(False)

        balises_recues = []
        try:
            reponse = requests.get(url, headers=headers, timeout=2, proxies={"http": None, "https": None})
            if reponse.status_code == 200:
                balises_recues = reponse.json()
        except Exception:
            pass 

        try:
            reponse = requests.get(url, headers=headers, timeout=2, proxies={"http": None, "https": None})
            if reponse.status_code == 200:
                balises_recues = reponse.json()
                
                # --- Envoi à la carte ---
                if hasattr(self.map_widget, 'afficher_balises'):
                    self.map_widget.afficher_balises(balises_recues)
                # ----------------------------------
                
        except Exception:
            pass
            
        lignes_a_afficher = max(3, len(balises_recues))

        for index in range(lignes_a_afficher):
            if index < len(balises_recues):
                b = balises_recues[index]
                nom = b.get("nom_balise", f"Balise {index+1}")
                lora_id = str(b.get("lora_id", f"ID-{index}"))
                
                card_balise = StatusCard(f"{nom}\n({lora_id})\nHors ligne")
                
                card_status = StatusCard("Statut\nEn attente")
                card_status.status_bar.setStyleSheet("background-color: #cbd5e1; border-radius: 2px; border: none;")

                # On sauvegarde les DEUX widgets dans notre dictionnaire
                self.balise_cards[lora_id] = {
                    "widget": card_balise, 
                    "widget_status": card_status, 
                    "nom": nom
                }

            else:
                card_balise = StatusCard(f"Balise {index+1}\n(Non configuree)")
                
                card_balise.status_bar.setStyleSheet("background-color: #cbd5e1; border-radius: 2px; border: none;")
                
                card_status = StatusCard("-\n-")
                card_status.status_bar.setStyleSheet("background-color: #cbd5e1; border-radius: 2px; border: none;")

            # Ajout dans la grille (colonne 0 = gauche, colonne 1 = droite)
            self.left_grid.addWidget(card_balise, index, 0)
            self.left_grid.addWidget(card_status, index, 1)

            # Ajout des deux à la liste pour pouvoir les nettoyer plus tard
            self.current_balise_widgets.extend([card_balise, card_status])

        self.btn_refresh.setText("Actualiser")
        self.btn_refresh.setEnabled(True)

    # Remise au bon niveau d'indentation (aligné avec les autres "def")
    def charger_donnees_tableaux(self):
        """Récupère les données de l'API avec des requêtes GET pour remplir les tableaux du bas."""
        headers = {"Authorization": f"ApiKey {config.API_KEY}"}
        
        # 1. Remplir le tableau de GAUCHE (Dernières coordonnées via /api/balises)
        try:
            r_balises = requests.get(f"{config.API_URL}/api/balises", headers=headers, timeout=5)
            if r_balises.status_code == 200:
                balises = r_balises.json()
                self.table_team.setRowCount(0) # Vider le tableau
                self.team_rows.clear()
                
                for b in balises:
                    row = self.table_team.rowCount()
                    self.table_team.insertRow(row)
                    
                    nom = b.get("nom_balise", f"Balise {b.get('id', '?')}")
                    lora_id = str(b.get("lora_id", b.get("id", "?")))
                    lat = b.get("latitude")
                    lon = b.get("longitude")
                    bat = b.get("status_batterie")
                    scenario_api = b.get("nom_course")
                    
                    lat_str = f"{lat:.5f}" if lat is not None else "--"
                    lon_str = f"{lon:.5f}" if lon is not None else "--"
                    bat_str = f"{bat}%" if bat is not None else "--"
                    
                    self.team_rows[lora_id] = row
                    
                    self.table_team.setItem(row, 0, QTableWidgetItem(nom))
                    self.table_team.setItem(row, 1, QTableWidgetItem(lat_str))
                    self.table_team.setItem(row, 2, QTableWidgetItem(lon_str))
                    self.table_team.setItem(row, 3, QTableWidgetItem(bat_str))
                    self.table_team.setItem(row, 4, QTableWidgetItem(scenario_api))
        except Exception as e:
            print(f"Erreur API (Balises) : {e}")

        # 2. Remplir le tableau de DROITE (Journal local via /api/etat-course)
        ID_COURSE_ACTUELLE = 22 
        
        try:
            r_etat = requests.get(f"{config.API_URL}/api/etat-course/course/{ID_COURSE_ACTUELLE}", headers=headers, timeout=5)
            if r_etat.status_code == 200:
                etats = r_etat.json()
                self.table_log.setRowCount(0) # Vider le journal
                
                for etat in etats[-30:]:
                    heure_brute = etat.get("created_at", datetime.now().strftime("%H:%M:%S"))
                    heure = heure_brute.split("T")[1][:8] if "T" in heure_brute else heure_brute
                    
                    equipe = f"Équipe {etat.get('id_equipe', '?')}"
                    balise = f"Balise {etat.get('id_balise', '?')}"
                    valide = etat.get("valide", False)
                    
                    evenement = "Passage validé" if valide else "Passage invalidé"
                    couleur = "#27ae60" if valide else "#e74c3c"
                    
                    self.ajouter_log(heure, equipe, evenement, balise, couleur)
        except Exception as e:
            print(f"Erreur API (Etat Course) : {e}")

    def update_dashboard_data(self, lat, lon, bat_level, balise_id):
        now = datetime.now().strftime("%H:%M:%S")
        str_id = str(balise_id)

        if str_id in self.balise_cards:
            card_info = self.balise_cards[str_id]
            card_widget = card_info["widget"]
            status_widget = card_info["widget_status"]
            
            card_widget.set_status(True) 
            bat_text = f"Bat: {bat_level}%" if bat_level is not None else "En ligne"
            card_widget.lbl_text.setText(f"{card_info['nom']}\n({str_id})\n{bat_text}")

            status_lines = []
            is_status_ok = True

            if bat_level is not None:
                if bat_level < 30:
                    status_lines.append(f"Alerte Batterie à ({bat_level}%)")
                    is_status_ok = False
                    if not self.alertes_batterie.get(str_id, False):
                        self.ajouter_log(now, f"Balise {str_id}", "Batterie Faible", f"{bat_level}% restants", "#e74c3c")
                        self.alertes_batterie[str_id] = True
                else:
                    status_lines.append("Batterie OK")
                    self.alertes_batterie[str_id] = False

            if lat is not None and lon is not None:
                # Mise à jour de la carte (On n'a plus besoin de le refaire à la fin !)
                self.map_widget.update_position(lat, lon, balise_id) 
                
                if self.ancrage_position is None:
                    self.ancrage_position = (lat, lon)
                    status_lines.append("Ancrage Fixe")
                else:
                    dist = distance_balise(self.ancrage_position[0], self.ancrage_position[1], lat, lon)
                    if dist > self.distance_limite:
                        status_lines.append("Alerte mouvement")
                        is_status_ok = False
                        if not self.alertes_mouvement.get(str_id, False):
                            self.ajouter_log(now, f"Balise {str_id}", "Alerte Deplacement", f"{int(dist)} metres du point", "#e74c3c")
                            self.alertes_mouvement[str_id] = True
                    else:
                        status_lines.append("Mouvement OK")
                        self.alertes_mouvement[str_id] = False

            status_widget.lbl_text.setText("\n".join(status_lines))
            status_widget.set_status(is_status_ok)

        scenario_text = "En attente API..."
        scenario_color = QColor("#64748b") 
        ID_COURSE_ACTUELLE = 1

        try:
            url = f"{config.API_URL}/api/etat-course/course/{ID_COURSE_ACTUELLE}" 
            reponse = requests.get(url, headers={"Authorization": f"ApiKey {config.API_KEY}"}, timeout=2, proxies={"http": None, "https": None})
            if reponse.status_code == 200:
                donnees_course = reponse.json()
                etat_equipe = None
                if isinstance(donnees_course, list):
                    for etat in donnees_course:
                        if str(etat.get("id_equipe")) == str_id:
                            etat_equipe = etat
                            break
                elif isinstance(donnees_course, dict) and str(donnees_course.get("id_equipe")) == str_id:
                    etat_equipe = donnees_course

                if etat_equipe:
                    est_termine = etat_equipe.get("termine") == True or etat_equipe.get("statut") == "termine"
                    cible_actuelle = "Terminee" if est_termine else etat_equipe.get("prochaine_etape", f"Balise {etat_equipe.get('id_balise', '?')}")
                    
                    if est_termine:
                        scenario_text = "Course Terminee"
                        scenario_color = QColor("#27ae60") 
                    else:
                        scenario_text = f"Vers {cible_actuelle}"
                        scenario_color = QColor("#f39c12") 

                    cible_precedente = self.equipes_etat_precedent.get(str_id)
                    if cible_precedente is not None and cible_precedente != cible_actuelle:
                        if est_termine:
                            self.ajouter_log(now, f"Equipe {str_id}", "Course Terminee", "Toutes les balises sont validees !", "#27ae60")
                        else:
                            self.ajouter_log(now, f"Equipe {str_id}", "Balise Validee", f"Nouvel objectif : {cible_actuelle}", "#27ae60")
                    self.equipes_etat_precedent[str_id] = cible_actuelle
                else:
                    scenario_text = "Equipe non trouvee"
        except:
            pass

        lat_str = f"{lat:.5f}" if lat else "--"
        lon_str = f"{lon:.5f}" if lon else "--"
        bat_str = f"{bat_level}%" if bat_level else "--"

        if str_id not in self.team_rows:
            self.team_rows[str_id] = self.table_team.rowCount()
            self.table_team.insertRow(self.team_rows[str_id])
            self.table_team.setItem(self.team_rows[str_id], 0, QTableWidgetItem(str_id))

        row = self.team_rows[str_id]
        if lat: 
            self.table_team.setItem(row, 1, QTableWidgetItem(lat_str))
            self.table_team.setItem(row, 2, QTableWidgetItem(lon_str))
        if bat_level:
            self.table_team.setItem(row, 3, QTableWidgetItem(bat_str))
        
        item_scen = QTableWidgetItem(scenario_text)
        item_scen.setForeground(scenario_color)
        self.table_team.setItem(row, 4, item_scen)

