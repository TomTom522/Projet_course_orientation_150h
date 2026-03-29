import requests
import config
# N'oubliez pas que j'ai rajouté QTableWidget, QHeaderView et QTableWidgetItem ici !
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QListWidget, QAbstractItemView, QListWidgetItem,
                             QApplication, QComboBox, QTableWidget, QHeaderView, QTableWidgetItem)
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt

class ScenarioPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- STYLE GLOBAL HARMONISE EN VERT ---
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; background-color: #f4f7f6; }
            QFrame#Card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
            QLineEdit, QComboBox { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; color: black; }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #27ae60; background-color: #ffffff; }
            
            QPushButton { font-weight: bold; border-radius: 6px; border: none; color: white; background-color: #64748b; padding: 6px 15px; }
            QPushButton:disabled { background-color: #bdc3c7; color: #ecf0f1; }
            
            QPushButton#ActionBtn { background-color: #27ae60; padding: 12px; font-size: 15px; }
            QPushButton#ActionBtn:hover:!disabled { background-color: #219653; }
            
            QPushButton#MoveBtn { background-color: #3498db; padding: 10px; font-size: 16px; }
            QPushButton#MoveBtn:hover:!disabled { background-color: #2980b9; }
            
            /* Bouton Rouge pour retirer/supprimer */
            QPushButton#RemoveBtn { background-color: #e74c3c; padding: 10px; font-size: 16px; }
            QPushButton#RemoveBtn:hover:!disabled { background-color: #c0392b; }
            
            QPushButton#RefreshBtn { background-color: #27ae60; padding: 10px; }
            QPushButton#RefreshBtn:hover:!disabled { background-color: #219653; }
            
            QListWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #f1f5f9; }
            QListWidget::item:selected { background-color: #e8f8f5; color: #27ae60; font-weight: bold; border-radius: 4px; }
            
            /* Ajout du style pour le tableau du bas */
            QTableWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
            QHeaderView::section { background-color: #f8fafc; color: #475569; padding: 12px; font-weight: bold; border: none; border-bottom: 3px solid #27ae60; }
            QTableWidget::item:selected { background-color: #27ae60; color: white; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # --- TITRE & RECHARGEMENT ---
        header_layout = QHBoxLayout()
        title = QLabel("Creation d'une Course et d'un Parcours")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("Actualiser les donnees API")
        self.btn_refresh.setObjectName("RefreshBtn")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.clicked.connect(self.charger_donnees_api)
        header_layout.addWidget(self.btn_refresh)
        
        main_layout.addLayout(header_layout)

        # --- CONFIGURATION COURSE ET EQUIPE ---
        config_frame = QFrame()
        config_frame.setObjectName("Card")
        config_layout = QHBoxLayout(config_frame)
        
        # Champ: Nom de la course
        config_layout.addWidget(QLabel("<b>Nom Course :</b>"))
        self.in_nom_course = QLineEdit()
        self.in_nom_course.setPlaceholderText("Ex: Course Alpha")
        self.in_nom_course.textChanged.connect(self.verifier_etat_boutons)
        config_layout.addWidget(self.in_nom_course, stretch=2)

        # Menu Deroulant: Choix de l'equipe
        config_layout.addWidget(QLabel("<b>Equipe cible :</b>"))
        self.cb_equipes = QComboBox()
        self.cb_equipes.currentIndexChanged.connect(self.verifier_etat_boutons)
        config_layout.addWidget(self.cb_equipes, stretch=2)

        # Champ: Code de la course
        config_layout.addWidget(QLabel("<b>Code Secret :</b>"))
        self.in_code_course = QLineEdit()
        self.in_code_course.setPlaceholderText("Ex: 1234")
        self.in_code_course.textChanged.connect(self.verifier_etat_boutons)
        config_layout.addWidget(self.in_code_course, stretch=1)
        
        main_layout.addWidget(config_frame)

        # --- ZONE DOUBLE LISTE (Balises Dispos <-> Parcours) ---
        lists_layout = QHBoxLayout()
        
        # 1. Liste des balises disponibles
        dispo_layout = QVBoxLayout()
        dispo_layout.addWidget(QLabel("<b>Balises Disponibles :</b>"))
        self.liste_dispo = QListWidget()
        self.liste_dispo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.liste_dispo.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.liste_dispo.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.liste_dispo.itemSelectionChanged.connect(self.verifier_etat_boutons)
        dispo_layout.addWidget(self.liste_dispo)
        lists_layout.addLayout(dispo_layout, stretch=2)
        
        # 2. Boutons de transfert
        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_add = QPushButton("Ajouter >>")
        self.btn_add.setObjectName("MoveBtn")
        self.btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add.clicked.connect(self.ajouter_au_parcours)
        
        self.btn_remove = QPushButton("<< Retirer")
        self.btn_remove.setObjectName("RemoveBtn")
        self.btn_remove.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_remove.clicked.connect(self.retirer_du_parcours)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        lists_layout.addLayout(btn_layout, stretch=1)
        
        # 3. Liste du Parcours Final
        parcours_layout = QVBoxLayout()
        parcours_layout.addWidget(QLabel("<b>Ordre du Parcours :</b>"))
        self.liste_parcours = QListWidget()
        self.liste_parcours.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.liste_parcours.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.liste_parcours.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.liste_parcours.itemSelectionChanged.connect(self.verifier_etat_boutons)
        self.liste_parcours.model().rowsInserted.connect(self.verifier_etat_boutons)
        self.liste_parcours.model().rowsRemoved.connect(self.verifier_etat_boutons)
        parcours_layout.addWidget(self.liste_parcours)
        lists_layout.addLayout(parcours_layout, stretch=2)

        main_layout.addLayout(lists_layout, stretch=2)

        # --- BOUTON DE SAUVEGARDE ---
        self.btn_save = QPushButton("Enregistrer la Course et le Parcours")
        self.btn_save.setObjectName("ActionBtn")
        self.btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save.clicked.connect(self.enregistrer_course_api)
        main_layout.addWidget(self.btn_save)

        # ==============================================================
        # NOUVELLE ZONE : TABLEAU DES COURSES (POUR POUVOIR SUPPRIMER)
        # ==============================================================
        recap_frame = QFrame()
        recap_frame.setObjectName("Card")
        recap_layout = QVBoxLayout(recap_frame)
        recap_layout.setContentsMargins(15, 15, 15, 15)
        
        recap_header = QHBoxLayout()
        lbl_recap = QLabel("<b>Liste des Courses :</b>")
        lbl_recap.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        recap_header.addWidget(lbl_recap)
        recap_header.addStretch()
        
        # Bouton rouge pour supprimer
        self.btn_delete_course = QPushButton("Supprimer la course sélectionnée")
        self.btn_delete_course.setObjectName("RemoveBtn") # On utilise le même rouge que "Retirer"
        self.btn_delete_course.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete_course.clicked.connect(self.supprimer_course)
        recap_header.addWidget(self.btn_delete_course)
        
        recap_layout.addLayout(recap_header)

        # Tableau des courses
        self.table_courses = QTableWidget(0, 2)
        self.table_courses.setHorizontalHeaderLabels(["ID Course", "Nom de la Course"])
        self.table_courses.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_courses.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_courses.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_courses.verticalHeader().setVisible(False) 
        # Hauteur maximale limiter
        self.table_courses.setMinimumHeight(200)

        recap_layout.addWidget(self.table_courses)
        main_layout.addWidget(recap_frame, stretch=2)
        # ==============================================================

        self.verifier_etat_boutons()
        self.charger_donnees_api()


    # ==========================================
    # LOGIQUE DE L'INTERFACE
    # ==========================================
    def verifier_etat_boutons(self):
        self.btn_add.setEnabled(bool(self.liste_dispo.currentItem()))
        self.btn_remove.setEnabled(bool(self.liste_parcours.currentItem()))
        
        nom_valide = bool(self.in_nom_course.text().strip())
        code_valide = bool(self.in_code_course.text().strip())
        equipe_valide = self.cb_equipes.currentData() is not None
        parcours_valide = self.liste_parcours.count() > 0
        
        self.btn_save.setEnabled(nom_valide and code_valide and equipe_valide and parcours_valide)

    def ajouter_au_parcours(self):
        item_selectionne = self.liste_dispo.currentItem()
        if item_selectionne:
            row = self.liste_dispo.row(item_selectionne)
            item = self.liste_dispo.takeItem(row)
            self.liste_parcours.addItem(item)
            self.verifier_etat_boutons()

    def retirer_du_parcours(self):
        item_selectionne = self.liste_parcours.currentItem()
        if item_selectionne:
            row = self.liste_parcours.row(item_selectionne)
            item = self.liste_parcours.takeItem(row)
            self.liste_dispo.addItem(item)
            self.verifier_etat_boutons()

    # ==========================================
    # COMMUNICATIONS AVEC L'API DOCKER
    # ==========================================
    def charger_donnees_api(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Chargement...")
        
        headers = {"Authorization": f"ApiKey {config.API_KEY}"}
        
        # 1. Chargement des balises
        self.liste_dispo.clear()
        self.liste_parcours.clear()
        try:
            url_balises = f"{config.API_URL}/api/balises"
            rep_balises = requests.get(url_balises, headers=headers, timeout=5, proxies={"http": None, "https": None})
            if rep_balises.status_code == 200:
                balises = rep_balises.json()
                for b in balises:
                    id_sql = b.get("id") or b.get("id_balise")
                    nom = b.get("nom_balise", "Sans nom")
                    item = QListWidgetItem(f"{nom} (SQL ID: {id_sql})")
                    item.setData(Qt.ItemDataRole.UserRole, id_sql) 
                    self.liste_dispo.addItem(item)
        except Exception as e:
            print(f"Erreur balises : {e}")

        # 2. Chargement des equipes
        self.cb_equipes.clear()
        self.cb_equipes.addItem("-- Selectionner une equipe --", None)
        try:
            url_equipes = f"{config.API_URL}/api/equipes"
            rep_equipes = requests.get(url_equipes, headers=headers, timeout=5, proxies={"http": None, "https": None})
            if rep_equipes.status_code == 200:
                equipes = rep_equipes.json()
                for eq in equipes:
                    id_eq = eq.get("id") or eq.get("id_equipe")
                    nom_eq = eq.get("nom_equipe", f"Equipe #{id_eq}")
                    self.cb_equipes.addItem(nom_eq, id_eq)
        except Exception as e:
            print(f"Erreur equipes : {e}")
            
        # 3. Chargement des COURSES (NOUVEAU) pour le tableau de suppression
        try:
            url_courses = f"{config.API_URL}/api/courses"
            rep_courses = requests.get(url_courses, headers=headers, timeout=5, proxies={"http": None, "https": None})
            if rep_courses.status_code == 200:
                courses = rep_courses.json()
                self.table_courses.setRowCount(0)
                for c in courses:
                    row = self.table_courses.rowCount()
                    self.table_courses.insertRow(row)
                    
                    id_sql = c.get("id") or c.get("id_course")
                    nom = c.get("nom_course", "Sans nom")
                    
                    item_id = QTableWidgetItem(str(id_sql))
                    item_id.setData(Qt.ItemDataRole.UserRole, id_sql) # On cache l'ID SQL dans l'élément
                    
                    self.table_courses.setItem(row, 0, item_id)
                    self.table_courses.setItem(row, 1, QTableWidgetItem(str(nom)))
        except Exception as e:
            print(f"Erreur chargement courses : {e}")

        QApplication.restoreOverrideCursor()
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("Actualiser les donnees API")
        self.verifier_etat_boutons()


    # =======================================================
    # NOUVELLE FONCTION : SUPPRIMER UNE COURSE
    # =======================================================
    def supprimer_course(self):
        row = self.table_courses.currentRow()
        
        # Si l'utilisateur n'a rien sélectionné
        if row < 0:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord cliquer sur la course que vous souhaitez supprimer dans le tableau.")
            return
            
        # On récupère les infos de la course sélectionnée
        item_id = self.table_courses.item(row, 0)
        id_sql = item_id.data(Qt.ItemDataRole.UserRole)
        nom_course = self.table_courses.item(row, 1).text()

        # --- NOUVEAU : Fenêtre de confirmation 100% en français ---
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText(f"Voulez-vous vraiment supprimer la course '{nom_course}' ?\nCela supprimera aussi son parcours et ses codes.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Ajout des boutons en français
        btn_oui = msg_box.addButton("Oui", QMessageBox.ButtonRole.YesRole)
        btn_non = msg_box.addButton("Non", QMessageBox.ButtonRole.NoRole)
        
        # On affiche la boîte
        msg_box.exec()
        
        # Si l'utilisateur a cliqué sur le bouton "Oui"
        if msg_box.clickedButton() == btn_oui:
            url = f"{config.API_URL}/api/courses/{id_sql}"
            headers = {"Authorization": f"ApiKey {config.API_KEY}"}
            
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                # On envoie l'ordre de suppression (DELETE) à l'API
                res = requests.delete(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
                
                if res.status_code in [200, 204]:
                    QMessageBox.information(self, "Succès", "La course a bien été supprimée.")
                    self.charger_donnees_api() # On rafraîchit la page
                else:
                    QMessageBox.critical(self, "Erreur", f"Le serveur a refusé la suppression (Code {res.status_code}).\n{res.text}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur réseau", f"Impossible de joindre le serveur : {e}")
            finally:
                QApplication.restoreOverrideCursor()

    # =======================================================
    def enregistrer_course_api(self):
        nom_course = self.in_nom_course.text().strip()
        code_course = self.in_code_course.text().strip()
        id_equipe_choisie = self.cb_equipes.currentData()
        
        headers = {"Authorization": f"ApiKey {config.API_KEY}", "Content-Type": "application/json"}
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.btn_save.setEnabled(False)
        self.btn_save.setText("Enregistrement en cours...")
        
        try:
            # ETAPE 1 : Creer la course
            url_course = f"{config.API_URL}/api/courses"
            payload_course = {"nom_course": nom_course}
            
            reponse_course = requests.post(url_course, json=payload_course, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            if reponse_course.status_code not in [200, 201]:
                QMessageBox.critical(self, "Erreur API (Course)", f"Impossible de creer la course.\nCode: {reponse_course.status_code}\nDetail: {reponse_course.text}")
                return
                
            donnees_course = reponse_course.json()
            
            # Extraction ULTRA ROBUSTE de l'ID de la course
            id_course = None
            if "id" in donnees_course:
                id_course = donnees_course["id"]
            elif "id_course" in donnees_course:
                id_course = donnees_course["id_course"]
            elif "course" in donnees_course and isinstance(donnees_course["course"], dict):
                id_course = donnees_course["course"].get("id") or donnees_course["course"].get("id_course")
            elif "data" in donnees_course and isinstance(donnees_course["data"], dict):
                id_course = donnees_course["data"].get("id") or donnees_course["data"].get("id_course")
                
            if not id_course:
                QMessageBox.critical(self, "Erreur ID Course", f"La course a ete creee, mais impossible d'extraire son ID.\\nReponse serveur : {donnees_course}")
                return

            # ETAPE 2 : Associer l'ordre des balises
            url_ordre = f"{config.API_URL}/api/ordre-balises"
            for index in range(self.liste_parcours.count()):
                item = self.liste_parcours.item(index)
                id_balise_sql = item.data(Qt.ItemDataRole.UserRole)
                
                payload_ordre = {
                    "id_course": id_course,
                    "id_equipe": id_equipe_choisie, 
                    "id_balise": id_balise_sql,
                    "position_balise": index + 1
                }
                
                rep_ordre = requests.post(url_ordre, json=payload_ordre, headers=headers, timeout=5, proxies={"http": None, "https": None})
                if rep_ordre.status_code not in [200, 201]:
                    QMessageBox.warning(self, "Erreur Ordre Balises", f"Erreur lors de l'association de la balise.\nAPI: {rep_ordre.text}")
                    return

            # ETAPE 3 : Creer le code secret
            url_code = f"{config.API_URL}/api/codes"
            payload_code = {
                "nomcode": f"Code pour {nom_course}",
                "valeur_code": code_course,
                "id_course": id_course,
                "id_equipe": id_equipe_choisie 
            }
            
            reponse_code = requests.post(url_code, json=payload_code, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            if reponse_code.status_code not in [200, 201]:
                QMessageBox.warning(self, "Erreur Code Secret", f"Course et parcours crees, mais le code a echoue.\\nCode: {reponse_code.status_code}\\nDetail: {reponse_code.text}")
            else:
                QMessageBox.information(self, "Succes", "La course, le parcours et le code secret ont ete crees avec succes !")
                
            self.in_nom_course.clear()
            self.in_code_course.clear()
            self.cb_equipes.setCurrentIndex(0)
            self.charger_donnees_api() # Cela va rafraîchir le nouveau tableau des courses en bas !

        except Exception as e:
            QMessageBox.critical(self, "Erreur Systeme", f"Impossible d'enregistrer la course : {e}")
            
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_save.setText("Enregistrer la Course et le Parcours dans la Base de donnees")
            self.verifier_etat_boutons()