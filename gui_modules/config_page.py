import requests
import config

# Importation des outils graphiques de PyQt6 (boutons, fenêtres, textes...)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QFrame, QLabel, QLineEdit, QPushButton, QTableWidget, 
                             QHeaderView, QTableWidgetItem, QMessageBox, QApplication)
from PyQt6.QtGui import QDoubleValidator, QCursor
from PyQt6.QtCore import Qt, QLocale

# Importation des outils pour afficher une page Web (la carte Leaflet)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage


# ==============================================================================
# CLASSE CUSTOMWEBPAGE : Sert à écouter ce qu'il se passe sur la carte
# ==============================================================================
class CustomWebPage(QWebEnginePage):
    def __init__(self, parent_config):
        super().__init__(parent_config)
        self.parent_config = parent_config

    # Cette fonction est déclenchée chaque fois que le Javascript de la carte fait un "console.log"
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Si le message commence par "COORD:" (ce qu'on a codé dans le HTML plus bas)
        if message.startswith("COORD:"):
            # On retire le mot "COORD:" et on coupe le texte à la virgule
            coords = message.replace("COORD:", "").split(",")
            
            # Si on a bien 2 éléments (Latitude et Longitude)
            if len(coords) == 2:
                # On remplit les cases de texte automatiquement en remplaçant les points par des virgules
                self.parent_config.in_lat.setText(coords[0].replace('.', ','))
                self.parent_config.in_lon.setText(coords[1].replace('.', ','))


# ==============================================================================
# CLASSE CONFIGPAGE : La page principale pour gérer les balises
# ==============================================================================
class ConfigPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. DÉFINITION DU DESIGN (Couleurs, formes des boutons...)
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; background-color: #f4f7f6; }
            QFrame#Card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
            QLineEdit { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; font-size: 14px; color: black; }
            QLineEdit:focus { border: 2px solid #27ae60; background-color: #ffffff; }
            
            /* Bouton Vert par défaut */
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 15px; padding: 12px; border-radius: 6px; border: none; }
            QPushButton:hover { background-color: #219653; }
            
            /* Bouton Bleu pour actualiser */
            QPushButton#RefreshBtn { background-color: #3498db; padding: 10px; font-size: 14px; }
            QPushButton#RefreshBtn:hover { background-color: #2980b9; }
            
            /* Bouton Rouge pour supprimer */
            QPushButton#DeleteBtn { background-color: #e74c3c; padding: 10px; font-size: 14px; }
            QPushButton#DeleteBtn:hover { background-color: #c0392b; }
            
            /* Design du tableau */
            QTableWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
            QHeaderView::section { background-color: #f8fafc; color: #475569; padding: 12px; font-weight: bold; border: none; border-bottom: 3px solid #27ae60; }
            QTableWidget::item:selected { background-color: #27ae60; color: white; }
        """)
        
        # 2. CRÉATION DU LAYOUT PRINCIPAL (Vertical : de haut en bas)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30) # Marges autour de la page
        main_layout.setSpacing(25) # Espace entre les éléments

        # --- TITRE ---
        title = QLabel("Configuration du Matériel (Balises)")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        main_layout.addWidget(title)

        # --- LA ZONE CENTRALE (Formulaire à gauche, Carte à droite) ---
        # création d'un layout Horizontal (de gauche à droite)
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(25)
        
        # Ajout le formulaire 
        self.form_frame = self.creer_formulaire_balise()
        middle_layout.addWidget(self.form_frame, stretch=1) # stretch=1 signifie qu'il prend 1 part d'espace
        
        # On ajoute la carte (créée plus bas)
        self.map_frame = self.creer_mini_map()
        middle_layout.addWidget(self.map_frame, stretch=2)  # stretch=2 signifie qu'elle est 2 fois plus grande que le formulaire
        
        # On ajoute cette zone centrale à la page principale
        main_layout.addLayout(middle_layout, stretch=2)

        # --- LA ZONE DU BAS (Tableau récapitulatif) ---
        recap_frame = QFrame()
        recap_frame.setObjectName("Card")
        recap_layout = QVBoxLayout(recap_frame)
        recap_layout.setContentsMargins(20, 20, 20, 20)
        
        # L'en-tête du tableau avec le titre et les boutons
        recap_header = QHBoxLayout()
        
        lbl_recap = QLabel("Liste des Balises Configurées")
        lbl_recap.setStyleSheet("color: #334155; font-weight: bold; font-size: 18px; border: none; background: transparent;")
        recap_header.addWidget(lbl_recap)
        
        recap_header.addStretch() # Pousse les boutons tout à droite
        
        # Bouton Supprimer
        self.btn_delete = QPushButton("Supprimer la sélection")
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.clicked.connect(self.supprimer_balise)
        recap_header.addWidget(self.btn_delete)

        # Bouton Actualiser
        self.btn_refresh = QPushButton("Actualiser la liste")
        self.btn_refresh.setObjectName("RefreshBtn")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.clicked.connect(self.charger_balises_api)
        recap_header.addWidget(self.btn_refresh)
        
        recap_layout.addLayout(recap_header)

        # Création du tableau lui-même
        self.table_balises = QTableWidget(0, 4) # 0 ligne, 4 colonnes
        self.table_balises.setHorizontalHeaderLabels(["ID LoRa", "Nom de la Balise", "Latitude", "Longitude"])
        self.table_balises.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Les colonnes s'étirent
        self.table_balises.verticalHeader().setDefaultSectionSize(35) # Hauteur des lignes
        self.table_balises.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) # On sélectionne toute la ligne d'un coup
        self.table_balises.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Empêche de modifier le texte en double-cliquant
        self.table_balises.verticalHeader().setVisible(False)

        recap_layout.addWidget(self.table_balises)
        main_layout.addWidget(recap_frame, stretch=2)

        # Hauteur maximale limiter
        self.table_balises.setMinimumHeight(200)

        # Au démarrage, on charge les balises existantes
        self.charger_balises_api()


    # ==============================================================================
    # FONCTION : Créer la boîte du formulaire
    # ==============================================================================
    def creer_formulaire_balise(self):
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel("Nouvelle Balise")
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; border: none; color: #27ae60; background: transparent;")
        layout.addWidget(lbl)
        
        # QGridLayout permet de ranger les éléments sous forme de tableau (Lignes / Colonnes)
        form = QGridLayout()
        
        # Champs de texte
        self.in_id = QLineEdit()
        self.in_id.setPlaceholderText("Ex: LORA-101")
        self.in_nom = QLineEdit()
        self.in_nom.setPlaceholderText("Balise parking de rodez")
        
        # Validateur pour forcer l'utilisateur à taper des chiffres pour les coordonnées
        v_double = QDoubleValidator(-180.0, 180.0, 8)
        v_double.setNotation(QDoubleValidator.Notation.StandardNotation)
        v_double.setLocale(QLocale(QLocale.Language.French, QLocale.Country.France))
        
        self.in_lat = QLineEdit()
        self.in_lat.setPlaceholderText("1,11")
        self.in_lat.setValidator(v_double)
        
        self.in_lon = QLineEdit()
        self.in_lon.setPlaceholderText("2,22")
        self.in_lon.setValidator(v_double)

        # Placement dans la grille : (Widget, Ligne, Colonne)
        form.addWidget(QLabel("ID LoRa :"), 0, 0)
        form.addWidget(self.in_id, 0, 1)
        form.addWidget(QLabel("Nom :"), 1, 0)
        form.addWidget(self.in_nom, 1, 1)
        form.addWidget(QLabel("Latitude :"), 2, 0)
        form.addWidget(self.in_lat, 2, 1)
        form.addWidget(QLabel("Longitude :"), 3, 0)
        form.addWidget(self.in_lon, 3, 1)
        
        layout.addLayout(form)
        layout.addStretch() # Pousse le bouton d'ajout tout en bas
        
        btn_add = QPushButton("Enregistrer la Balise")
        btn_add.clicked.connect(self.ajouter_balise_table)
        layout.addWidget(btn_add)
        
        return frame


    
    # FONCTION : Créer la carte cliquable

    def creer_mini_map(self):
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # QWebEngineView est un mini-navigateur internet intégré
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebPage(self)) # On lui attache notre classe spéciale pour écouter les clics
        
        # Voici le code source HTML d'une page web simple affichant une carte Leaflet
        html_map = """
        <!DOCTYPE html><html><head>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <style> body { margin: 0; } #map { width: 100%; height: 100vh; cursor: crosshair; }</style>
        </head><body><div id="map"></div><script>
                // On centre la carte sur la France au démarrage
                var map = L.map('map').setView([44.35, 2.57], 10);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                var marker;
                
                // Quand on clique sur la carte...
                map.on('click', function(e) {
                    var lat = e.latlng.lat.toFixed(6); 
                    var lon = e.latlng.lng.toFixed(6);
                    if (marker) { map.removeLayer(marker); } // On supprime l'ancien marqueur
                    marker = L.marker([lat, lon]).addTo(map); // On en crée un nouveau
                    
                    // On envoie le texte à Python !
                    console.log("COORD:" + lat + "," + lon);
                });
            </script></body></html>
        """
        self.web_view.setHtml(html_map)
        layout.addWidget(self.web_view)
        
        return frame


    # ==============================================================================
    # FONCTION : Télécharger les balises depuis l'API et remplir le tableau
    # ==============================================================================
    def charger_balises_api(self):
        url = f"{config.API_URL}/api/balises"
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
        
        # On change la souris pour montrer qu'on charge, et on désactive le bouton
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Chargement...")
        
        try:
            # 1. On interroge l'API
            reponse = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            # 2. Si c'est un succès
            if reponse.status_code == 200:
                balises = reponse.json()
                
                # On efface toutes les lignes actuelles du tableau
                self.table_balises.setRowCount(0) 
                
                # Pour chaque balise reçue par l'API...
                for b in balises:
                    # On crée une nouvelle ligne
                    row = self.table_balises.rowCount()
                    self.table_balises.insertRow(row)
                    
                    # On récupère les infos sécurisées (si une info manque, on met une valeur par défaut)
                    id_sql = b.get("id") or b.get("id_balise")
                    id_lora = str(b.get("lora_id", "N/A"))
                    nom = str(b.get("nom_balise", "Sans nom"))
                    lat = str(b.get("latitude", "0.0"))
                    lon = str(b.get("longitude", "0.0"))
                    
                    # On crée un objet de tableau pour l'ID LoRa, et on lui cache l'ID SQL à l'intérieur
                    # Cela nous permettra de savoir quel ID supprimer plus tard.
                    item_lora = QTableWidgetItem(id_lora)
                    item_lora.setData(Qt.ItemDataRole.UserRole, id_sql) 
                    
                    # On place les textes dans les bonnes colonnes
                    self.table_balises.setItem(row, 0, item_lora)
                    self.table_balises.setItem(row, 1, QTableWidgetItem(nom))
                    self.table_balises.setItem(row, 2, QTableWidgetItem(lat))
                    self.table_balises.setItem(row, 3, QTableWidgetItem(lon))
                    
        except Exception as e:
            # S'il y a une erreur réseau, on l'affiche dans la console
            print(f"Impossible de charger les balises : {e}")
            
        finally:
            # Dans tous les cas (succès ou erreur), on remet la souris normale et on réactive le bouton
            QApplication.restoreOverrideCursor()
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("Actualiser la liste")


    
    # FONCTION : Ajouter une balise via le formulaire
    
    def ajouter_balise_table(self):
        # 1. On récupère le texte tapé par l'utilisateur (strip() enlève les espaces en trop)
        id_lora = self.in_id.text().strip()
        nom_saisi = self.in_nom.text().strip()
        lat_text = self.in_lat.text().strip()
        lon_text = self.in_lon.text().strip()

        # 2. Sécurité : Vérifier que les champs obligatoires ne sont pas vides
        if not id_lora or not lat_text or not lon_text: 
            QMessageBox.warning(self, "Attention", "Veuillez remplir l'ID LoRa et les coordonnées.")
            return
            
        # 3. Sécurité : Convertir le texte des coordonnées en vrais nombres à virgule (float)
        try:
            lat_nombre = float(lat_text.replace(',', '.'))
            lon_nombre = float(lon_text.replace(',', '.'))
        except ValueError: 
            QMessageBox.warning(self, "Erreur", "Format de coordonnées invalide.")
            return

        # 4. On prépare les données à envoyer à l'API
        url = f"{config.API_URL}/api/balises"
        headers = {
            "Authorization": f"Bearer {config.JWT_TOKEN}", 
            "Content-Type": "application/json"
        }
        
        # Si aucun nom n'est saisi, on crée un nom par défaut "Balise LORA-101"
        nom_final = nom_saisi if nom_saisi != "" else f"Balise {id_lora}"
        
        payload = {
            "nom_balise": nom_final, 
            "lora_id": id_lora, 
            "latitude": lat_nombre, 
            "longitude": lon_nombre, 
            "status_batterie": 100, 
            "est_active": True
        }
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # 5. On envoie la requête à l'API
        try:
            reponse = requests.post(url, json=payload, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            # 6. Si l'API a créé la balise avec succès (Code 201)
            if reponse.status_code == 201:
                # On vide les champs du formulaire
                self.in_id.clear()
                self.in_nom.clear()
                self.in_lat.clear()
                self.in_lon.clear()
                
                # Et on actualise le tableau pour voir la nouvelle balise !
                self.charger_balises_api()

            elif reponse.status_code == 401 or "expir" in reponse.text.lower():
                QApplication.restoreOverrideCursor() # On remet la souris normale avant le message
                
                # On prévient l'utilisateur
                QMessageBox.warning(self, "Session expirée", "Votre session a expiré.\nVeuillez vous reconnecter.")
                
                # On déclenche la déconnexion générale du main.py !
                if hasattr(self.window(), 'se_deconnecter'):
                    self.window().se_deconnecter()
                    
                    # Une fois reconnecté, on retente l'actualisation du tableau
                    self.charger_balises_api()
                    
            # 8. Les autres erreurs (ex: Erreur 403 = Pas les droits)
            else:
                QMessageBox.critical(self, "Erreur Serveur", f"Erreur {reponse.status_code} : {reponse.text}")
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur Réseau", f"Impossible de contacter l'API : {e}")
            
        finally:
            QApplication.restoreOverrideCursor()


    def pre_remplir_donnees_lora(self, lat, lon, id_balise):
        """Remplit automatiquement le formulaire quand une donnée LoRa arrive"""

        # Si on es en train d'écrire dans la case "Nom", rien ne change
        if self.in_nom.hasFocus():
            return
        
        # On remplit l'ID
        self.in_id.setText(str(id_balise))
        
        # On remplit les coordonnées (en remplaçant le point par une virgule pour l'interface)
        self.in_lat.setText(str(lat).replace('.', ','))
        self.in_lon.setText(str(lon).replace('.', ','))
        
        print(f"Formulaire pré-rempli avec la balise {id_balise}")

    # FONCTION : Supprimer la balise sélectionnée dans le tableau
    def supprimer_balise(self):
        # 1. On regarde quelle ligne du tableau est sélectionnée
        row = self.table_balises.currentRow()
        
        if row < 0:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une balise à supprimer dans le tableau.")
            return
            
        # 2. On récupère la colonne 0 (celle de l'ID LoRa)
        item_lora = self.table_balises.item(row, 0)
        
        # Vous vous souvenez de l'astuce ? On récupère l'ID SQL qui était caché dedans !
        id_sql = item_lora.data(Qt.ItemDataRole.UserRole) 
        nom_balise = self.table_balises.item(row, 1).text()

        # 3. On demande confirmation à l'utilisateur
        reponse = QMessageBox.question(self, "Confirmation", f"Voulez-vous vraiment supprimer la balise '{nom_balise}' ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reponse == QMessageBox.StandardButton.Yes:
            url = f"{config.API_URL}/api/balises/{id_sql}"
            headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            # 4. On demande à l'API de supprimer la balise (DELETE)
            try:
                res = requests.delete(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
                
                # Succès (200 = OK, 204 = Supprimé sans contenu retourné)
                if res.status_code in [200, 204]:
                    QMessageBox.information(self, "Succès", "La balise a bien été supprimée.")
                    self.charger_balises_api() # On recharge le tableau pour la faire disparaître
                else:
                    QMessageBox.critical(self, "Erreur", f"Suppression refusée par l'API (Code {res.status_code}).\nCette balise est peut-être utilisée dans un parcours !")
                    
            except Exception as e:
                QMessageBox.critical(self, "Erreur Réseau", f"Impossible de joindre le serveur : {e}")
                
            finally:
                QApplication.restoreOverrideCursor()