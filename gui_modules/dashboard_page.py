import math
import requests
import config
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QFrame, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QCursor
from gui_modules.map_page import MapPage

def distance_balise(lat1, lon1, lat2, lon2):
    """
    Calcule la distance en mètres entre deux coordonnées GPS 
    (Formule de Haversine)
    """
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
        
    R = 6371000  # Rayon de la Terre en mètres
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(dlambda / 2)**2
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c # Distance en mètres

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
        self.donnees_forecast = []
        self.jour_selectionne = 0
        # Coordonnées par défaut (Rodez)
        self.lat_actuelle = 44.35
        self.lon_actuelle = 2.57
        self.ville_actuelle = "Rodez"

        self.setObjectName("MeteoCard")
        self.setStyleSheet("""
            QFrame#MeteoCard { background-color: #34C25A; border-radius: 8px; margin: 2px; }
            QLabel { border: none; background: transparent; color: white; }
            QPushButton#JourBtn {
                background-color: rgba(255,255,255,0.25);
                color: white; font-weight: bold; font-size: 11px;
                padding: 4px 8px; border-radius: 5px; border: none;
            }
            QPushButton#JourBtn:checked { background-color: white; color: #27ae60; }
            QPushButton#JourBtn:hover { background-color: rgba(255,255,255,0.4); }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        # Boutons de sélection du jour
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        self.btn_jours = []
        for i, nom in enumerate(["Auj.", "Demain", "J+2"]):
            btn = QPushButton(nom)
            btn.setObjectName("JourBtn")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, idx=i: self.changer_jour(idx))
            self.btn_jours.append(btn)
            btn_layout.addWidget(btn)
        self.btn_jours[0].setChecked(True)
        main_layout.addLayout(btn_layout)

        # Température + détails
        info_layout = QHBoxLayout()
        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setStyleSheet("font-size: 25px; font-weight: bold; color: white;")
        info_layout.addWidget(self.lbl_temp)

        details_layout = QVBoxLayout()
        self.lbl_city = QLabel("Météo à Rodez")
        self.lbl_city.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        self.lbl_desc = QLabel("Chargement...")
        self.lbl_desc.setStyleSheet("font-size: 12px; color: white;")
        self.lbl_wind = QLabel("Vent: -- km/h")
        self.lbl_wind.setStyleSheet("font-size: 12px; color: white;")
        self.lbl_hum = QLabel("Humidité: --%")
        self.lbl_hum.setStyleSheet("font-size: 12px; color: white;")
        self.lbl_soleil = QLabel("🌅 --:-- | 🌇 --:--")
        self.lbl_soleil.setStyleSheet("font-size: 12px; color: white; font-weight: bold;")
        details_layout.addWidget(self.lbl_city)
        details_layout.addWidget(self.lbl_desc)
        details_layout.addWidget(self.lbl_wind)
        details_layout.addWidget(self.lbl_hum)
        details_layout.addWidget(self.lbl_soleil)
        info_layout.addLayout(details_layout)
        main_layout.addLayout(info_layout)

        # Indicateur course
        self.lbl_course = QLabel("Chargement de l'analyse...")
        self.lbl_course.setWordWrap(True)
        self.lbl_course.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_course.setStyleSheet("""
            color: white; font-weight: bold; font-size: 12px;
            background-color: rgba(0,0,0,0.2);
            border-radius: 5px; padding: 4px 8px;
        """)
        main_layout.addWidget(self.lbl_course)

    def changer_jour(self, index):
        self.jour_selectionne = index
        for i, btn in enumerate(self.btn_jours):
            btn.setChecked(i == index)
        if self.donnees_forecast:
            self.afficher_jour(index)

    def afficher_jour(self, index):
        if index >= len(self.donnees_forecast):
            return
        day = self.donnees_forecast[index]

        if index == 0 and hasattr(self, '_current_data'):
            cur = self._current_data
            self.lbl_temp.setText(f"{cur['temp_c']}°C")
            self.lbl_desc.setText(cur['condition']['text'])
            self.lbl_wind.setText(f"Vent: {cur['wind_kph']} km/h")
            self.lbl_hum.setText(f"Humidité: {cur['humidity']}%")
        else:
            d = day['day']
            self.lbl_temp.setText(f"{d['mintemp_c']}°C / {d['maxtemp_c']}°C")
            self.lbl_desc.setText(d['condition']['text'])
            self.lbl_wind.setText(f"Vent max: {d['maxwind_kph']} km/h")
        
        # Mise à jour du soleil
        astro = day.get('astro', {})
        lever = astro.get('sunrise', '--')
        coucher = astro.get('sunset', '--')
        self.lbl_soleil.setText(f"🌅 {lever}  |  🌇 {coucher}")

        self._evaluer_course(day)

    def _evaluer_course(self, day):
        d = day['day']
        vent = d['maxwind_kph']
        pluie_chance = d.get('daily_chance_of_rain', 0)
        pluie_mm = d.get('totalprecip_mm', 0)
        vis = d.get('avgvis_km', 10)

        problemes = []
        if vent > 50:
            problemes.append(f"vent fort ({vent:.0f} km/h)")
        if pluie_chance > 60:
            problemes.append(f"risque pluie ({pluie_chance}%)")
        if pluie_mm > 5:
            problemes.append(f"fortes précipitations ({pluie_mm:.0f}mm)")
        if vis < 3:
            problemes.append(f"visibilité faible ({vis:.0f}km)")

        if not problemes:
            self.lbl_course.setText("Conditions favorables pour une course !")
        elif len(problemes) == 1:
            self.lbl_course.setText(f"Attention : {problemes[0]}")
        else:
            self.lbl_course.setText(f"Déconseillé : {', '.join(problemes)}")

    def mettre_a_jour_position(self, lat, lon, nom_balise="Position"):
        self.lat_actuelle = lat
        self.lon_actuelle = lon
        self.ville_actuelle = nom_balise
        self.lbl_city.setText(f"Météo à {nom_balise}")

    def mettre_a_jour(self, current_data, forecast_days):
        self._current_data = current_data
        self.donnees_forecast = forecast_days
        self.afficher_jour(self.jour_selectionne)


class DashboardPage(QWidget):
    nouveau_log_signal = pyqtSignal(str, str, str, str)

    def __init__(self):
        super().__init__()

        self.dernieres_positions = {}
        self.last_map_update = 0
        self.setStyleSheet("background-color: #f4f7f6;") 
        
        # --- CORRECTION ANCRAGE INDIVIDUEL ---
        self.ancrage_positions = {}   # Un dictionnaire pour stocker le départ de CHAQUE balise
        #self.compteurs_ancrage = {}    # Compte les messages avant de valider l'ancrage
        self.distance_limite = 80.0    # Seuil d'alerte (augmenté un peu pour la précision GPS)
        # -------------------------------------
        
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
        
        self.btn_refresh = QPushButton("🔄 Actualiser")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; color: white; font-weight: bold; 
                padding: 6px 12px; border-radius: 6px; border: none; 
            } 
            QPushButton:hover { background-color: #2980b9; }
        """)
        # cela active le bouton :
        self.btn_refresh.clicked.connect(self.rafraichir_tout)
        
        header_h.addWidget(lbl_dash)
        header_h.addStretch()
        
        header_h.addWidget(self.btn_refresh)

        self.btn_reset_ancrage = QPushButton("Reset Ancrages")
        self.btn_reset_ancrage.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_ancrage.setStyleSheet("""
            QPushButton { 
                background-color: #e67e22; color: white; font-weight: bold; 
                padding: 6px 12px; border-radius: 6px; border: none; 
            } 
            QPushButton:hover { background-color: #d35400; }
        """)
        self.btn_reset_ancrage.clicked.connect(self.reset_tous_les_ancrages)
        header_h.addWidget(self.btn_reset_ancrage)
        left_layout.addLayout(header_h)
        left_layout.addSpacing(10)

        self.weather_card = Cartemeteo()
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

        bottom_section = QWidget()
        bottom_section.setMinimumHeight(250)
        bottom_layout = QHBoxLayout(bottom_section)

        self.table_team = self.create_table(["Balise", "Latitude", "Longitude", "Batterie", "Scenario"])
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
        self.charger_donnees_tableaux()
        self.mise_a_jour_meteo()
        
        self.timer_meteo = QTimer(self)
        self.timer_meteo.timeout.connect(self.mise_a_jour_meteo)
        self.timer_meteo.start(3600000)

        self.timer_live = QTimer(self)
        self.timer_live.timeout.connect(self.actualiser_donnees_live)
        self.timer_live.start(70000)

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
        self.nouveau_log_signal.emit(source, evenement, detail, couleur)

    def reset_tous_les_ancrages(self):
        """ Réinitialise les points de référence de toutes les balises """
        self.ancrage_positions.clear()
        #self.compteurs_ancrage.clear()
        self.alertes_mouvement.clear()
        self.ajouter_log(datetime.now().strftime("%H:%M:%S"), "Système", "Reset Manuel", "Toutes les positions de référence ont été effacées", "#e67e22")

    def mise_a_jour_meteo(self):
        api_key = "a6f6fef1470f473cb0694459230605"
        coords = f"{self.weather_card.lat_actuelle},{self.weather_card.lon_actuelle}"
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={coords}&lang=fr&days=4"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.weather_card.mettre_a_jour(data['current'], data['forecast']['forecastday'])
        except: pass

    def actualiser_donnees_live(self):
        self.charger_balises_api()
        self.charger_donnees_tableaux()

    def rafraichir_tout(self):
        """ Actualise UNIQUEMENT les cartes des balises en haut """
        
        # 1. On efface visuellement les anciennes cartes de l'écran
        while self.left_grid.count():
            item = self.left_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # 2. On vide la mémoire des cartes du haut
        self.balise_cards.clear()

        # 3. On va chercher les infos sur l'API pour recréer les cartes en haut
        self.charger_balises_api()


    def charger_balises_api(self):
        for card in self.current_balise_widgets:
            self.left_grid.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
            
        self.current_balise_widgets.clear()
        self.balise_cards.clear()
        
        url = f"{config.API_URL}/api/balises"
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
        self.btn_refresh.setText("Chargement...")
        self.btn_refresh.setEnabled(False)

        balises_recues = []
        try:
            reponse = requests.get(url, headers=headers, timeout=2, proxies={"http": None, "https": None})
            if reponse.status_code == 200:
                balises_recues = reponse.json()
                if hasattr(self.map_widget, 'afficher_balises'):
                    self.map_widget.afficher_balises(balises_recues)
        except Exception: pass
            
        lignes_a_afficher = max(3, len(balises_recues))
        for index in range(lignes_a_afficher):
            if index < len(balises_recues):
                b = balises_recues[index]
                nom = b.get("nom_balise", f"Balise {index+1}")
                lora_id = str(b.get("lora_id", f"ID-{index}"))
                card_balise = StatusCard(f"{nom}\n({lora_id})\nHors ligne")
                card_status = StatusCard("Statut\nEn attente")
                self.balise_cards[lora_id] = {"widget": card_balise, "widget_status": card_status, "nom": nom}
            else:
                card_balise = StatusCard(f"Balise {index+1}\n(Non configuree)")
                card_status = StatusCard("-\n-")

            self.left_grid.addWidget(card_balise, index, 0)
            self.left_grid.addWidget(card_status, index, 1)
            self.current_balise_widgets.extend([card_balise, card_status])

        self.btn_refresh.setText("Actualiser")
        self.btn_refresh.setEnabled(True)

    def charger_donnees_tableaux(self):
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
        try:
            r_balises = requests.get(f"{config.API_URL}/api/balises", headers=headers, timeout=5)
            r_courses = requests.get(f"{config.API_URL}/api/courses", headers=headers, timeout=5)
            r_equipes = requests.get(f"{config.API_URL}/api/equipes", headers=headers, timeout=5)

            if r_balises.status_code == 200:
                balises = r_balises.json()

                # Nouvelle stratégie : on passe par les équipes et leurs courses actives
                # puis on récupère l'ordre des balises via /api/ordre-balises/course/{id}
                map_balise_course = {}
                try:
                    if r_courses.status_code == 200 and r_equipes.status_code == 200:
                        courses = r_courses.json()
                        equipes = r_equipes.json()

                        map_courses = {
                            str(c.get('id') or c.get('id_course')): c.get('nom_course', '?')
                            for c in courses
                        }

                        # Récupérer les IDs de courses actives depuis les équipes
                        ids_courses_actives = set()
                        for eq in equipes:
                            id_c = eq.get('id_course_actuelle') or eq.get('id_course')
                            if id_c:
                                ids_courses_actives.add(str(id_c))

                        # Pour chaque course active, essayer de récupérer ses balises
                        for id_c in ids_courses_actives:
                            nom_course = map_courses.get(id_c, f"Course {id_c}")
                            for route in [
                                f"/api/ordre-balises/course/{id_c}",
                                f"/api/courses/{id_c}/ordre-balises",
                                f"/api/courses/{id_c}/balises",
                                f"/api/courses/{id_c}/parcours",
                            ]:
                                try:
                                    r_o = requests.get(f"{config.API_URL}{route}", headers=headers, timeout=3)
                                    if r_o.status_code == 200:
                                        for o in r_o.json():
                                            id_b = o.get('id_balise') or o.get('id_balise_sql')
                                            if id_b is not None:
                                                map_balise_course[str(id_b)] = nom_course
                                        break
                                except Exception:
                                    continue
                except Exception as e:
                    print(f"Erreur construction map_balise_course : {e}")

                self.table_team.setRowCount(0)
                self.team_rows.clear()

                for b in balises:
                    row = self.table_team.rowCount()
                    self.table_team.insertRow(row)
                    lora_id = str(b.get("lora_id", b.get("id", "?")))
                    id_sql = str(b.get("id") or b.get("id_balise"))
                    lat, lon = b.get("latitude"), b.get("longitude")

                    nom_course = map_balise_course.get(id_sql, "--")

                    self.table_team.setItem(row, 0, QTableWidgetItem(b.get("nom_balise", "Balise")))
                    self.table_team.setItem(row, 1, QTableWidgetItem(f"{lat:.5f}" if lat else "--"))
                    self.table_team.setItem(row, 2, QTableWidgetItem(f"{lon:.5f}" if lon else "--"))
                    self.table_team.setItem(row, 3, QTableWidgetItem(f"{b.get('status_batterie')}%" if b.get('status_batterie') else "--"))
                    self.table_team.setItem(row, 4, QTableWidgetItem(nom_course))
                    self.team_rows[lora_id] = row

                if balises:
                    derniere_balise = balises[-1]
                    lat, lon = derniere_balise.get("latitude"), derniere_balise.get("longitude")
                    nom = derniere_balise.get("nom_balise", "Balise")
                    if lat and lon:
                        self.weather_card.mettre_a_jour_position(lat, lon, nom)
                        self.mise_a_jour_meteo()

        except Exception as e:
            print(f"Erreur charger_donnees_tableaux : {e}")

        ID_COURSE_ACTUELLE = 22
        try:
            r_etat = requests.get(f"{config.API_URL}/api/etat-course/course/{ID_COURSE_ACTUELLE}", headers=headers, timeout=5)
            if r_etat.status_code == 200:
                etats = r_etat.json()
                self.table_log.setRowCount(0)
                for etat in etats[-30:]:
                    heure_brute = etat.get("created_at", datetime.now().strftime("%H:%M:%S"))
                    heure = heure_brute.split("T")[1][:8] if "T" in heure_brute else heure_brute
                    self.ajouter_log(heure, f"Équipe {etat.get('id_equipe', '?')}", "Passage", f"Balise {etat.get('id_balise', '?')}")
        except:
            pass

    def update_dashboard_data(self, lat, lon, bat_level, balise_id):
        str_id = str(balise_id)
        now = datetime.now().strftime("%H:%M:%S")
        
        # Initialisation de status_lines
        status_lines = []
        is_status_ok = True

        # --- LOGIQUE D'ANCRAGE IMMÉDIAT (1 POINT) ---
        if lat is not None and lon is not None:

            nom_balise = self.balise_cards[str_id]["nom"] if str_id in self.balise_cards else f"Balise {str_id}"
            self.weather_card.mettre_a_jour_position(lat, lon, nom_balise)
            
            if str_id not in self.ancrage_positions:
                # Dès qu'on reçoit le tout premier point, on fixe l'ancre
                self.ancrage_positions[str_id] = (lat, lon)
                status_lines.append("Ancrage Fixé")
                self.ajouter_log(now, f"Balise {str_id}", "Ancrage OK", "Position validée", "#27ae60")
            else:
                # L'ancrage est déjà fixé, on surveille le mouvement
                ancrage = self.ancrage_positions[str_id]
                dist = distance_balise(ancrage[0], ancrage[1], lat, lon)
                
                if dist > self.distance_limite:
                    status_lines.append(f"ALERTE MOUV ({int(dist)}m)")
                    is_status_ok = False
                    if not self.alertes_mouvement.get(str_id, False):
                        self.ajouter_log(now, f"Balise {str_id}", "DEPLACEMENT", f"Ecart de {int(dist)}m détecté !", "#e74c3c")
                        self.alertes_mouvement[str_id] = True
                else:
                    status_lines.append("Position OK")
                    self.alertes_mouvement[str_id] = False

        # 2. MISE À JOUR DE L'INTERFACE
        if str_id in self.balise_cards:
            card_info = self.balise_cards[str_id]
            card_widget = card_info["widget"]
            status_widget = card_info["widget_status"]
            
            card_widget.set_status(True) 
            bat_text = f"Bat: {bat_level}%" if bat_level is not None else "En ligne"
            card_widget.lbl_text.setText(f"{card_info['nom']}\n({str_id})\n{bat_text}")

            # Batterie
            if bat_level is not None:
                if bat_level < 30:
                    status_lines.append(f"Batterie Faible ({bat_level}%)")
                    is_status_ok = False
                else:
                    status_lines.append("Batterie OK")

            status_widget.lbl_text.setText("\n".join(status_lines))
            status_widget.set_status(is_status_ok)

        # 3. MISE À JOUR TABLEAUX
        if str_id in self.team_rows:
            row = self.team_rows[str_id]
            if lat:
                self.table_team.setItem(row, 1, QTableWidgetItem(f"{lat:.5f}")) # Col 1
            if lon:
                self.table_team.setItem(row, 2, QTableWidgetItem(f"{lon:.5f}")) # Col 2
                
            # --- MISE À JOUR DE LA BATTERIE EN DIRECT (Col 3) ---
            if bat_level is not None:
                item_bat = QTableWidgetItem(f"{bat_level}%")
                item_bat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bat_level < 30:
                    item_bat.setForeground(QColor("#e74c3c")) # Rouge si faible
                self.table_team.setItem(row, 3, item_bat)

    