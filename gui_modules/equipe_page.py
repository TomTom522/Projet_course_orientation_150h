import requests
import config
import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QFrame, QLabel, QLineEdit, QPushButton, QTableWidget, 
                             QHeaderView, QTableWidgetItem, QMessageBox, QApplication)
from PyQt6.QtGui import QIntValidator, QCursor
from PyQt6.QtCore import Qt

class EquipePage(QWidget):
    def __init__(self):
        super().__init__()
        self.dernier_rfid_recu = ""

        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; background-color: #f4f7f6; }
            QFrame#Card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
            QLineEdit { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; color: black; }
            QLineEdit:focus { border: 2px solid #27ae60; background-color: #ffffff; }
            QPushButton#ActionBtn { background-color: #27ae60; color: white; font-weight: bold; padding: 12px; border-radius: 6px; border: none; }
            QPushButton#ActionBtn:hover { background-color: #219653; }
            QPushButton#ScanBtn { background-color: #3498db; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }
            QPushButton#ScanBtn:hover { background-color: #2980b9; }
            QPushButton#RefreshBtn { background-color: #3498db; color: white; font-weight: bold; padding: 10px; font-size: 14px; border-radius: 6px; border: none; }
            QPushButton#RefreshBtn:hover { background-color: #2980b9; }
            QPushButton#DeleteBtn { background-color: #e74c3c; color: white; font-weight: bold; padding: 10px; font-size: 14px; border-radius: 6px; border: none; }
            QPushButton#DeleteBtn:hover { background-color: #c0392b; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
            QHeaderView::section { background-color: #f8fafc; padding: 12px; font-weight: bold; border-bottom: 3px solid #27ae60; }
                           
            QTableWidget::item:selected { background-color: #27ae60; color: white; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # --- FORMULAIRE ---
        self.form_frame = QFrame()
        self.form_frame.setObjectName("Card")
        form_layout = QVBoxLayout(self.form_frame)
        
        lbl_new = QLabel("Inscription Nouvelle Equipe")
        lbl_new.setStyleSheet("font-weight: bold; font-size: 18px; color: #27ae60; border: none;")
        form_layout.addWidget(lbl_new)

        grid = QGridLayout()
        self.in_id_equipe = QLineEdit()
        self.in_id_equipe.setValidator(QIntValidator(0, 999))
        self.in_id_equipe.setPlaceholderText("Ex: 1")
        self.in_nom_equipe = QLineEdit()
        self.in_nom_equipe.setPlaceholderText("Ex: Equipe Alpha")

        self.in_rfid = QLineEdit()
        self.in_rfid.setPlaceholderText("ID du badge RFID")
        self.in_rfid.setStyleSheet("background-color: #edf2f7; font-weight: bold; color: #2d3748;")

        self.btn_scan = QPushButton("Lire dernier RFID")
        self.btn_scan.setObjectName("ScanBtn")
        self.btn_scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scan.clicked.connect(self.remplir_rfid)

        grid.addWidget(QLabel("ID Equipe (Optionnel) :"), 0, 0)
        grid.addWidget(self.in_id_equipe, 0, 1)
        grid.addWidget(QLabel("Nom Equipe :"), 0, 2)
        grid.addWidget(self.in_nom_equipe, 0, 3)
        grid.addWidget(QLabel("Badge RFID :"), 1, 0)
        grid.addWidget(self.in_rfid, 1, 1, 1, 2)
        grid.addWidget(self.btn_scan, 1, 3)

        form_layout.addLayout(grid)

        self.btn_add = QPushButton("Créer l'équipe")
        self.btn_add.setObjectName("ActionBtn")
        self.btn_add.clicked.connect(self.ajouter_equipe)
        form_layout.addWidget(self.btn_add)

        main_layout.addWidget(self.form_frame)

        # --- TABLEAU ---
        recap_frame = QFrame()
        recap_frame.setObjectName("Card")
        recap_layout = QVBoxLayout(recap_frame)
        recap_layout.setContentsMargins(20, 20, 20, 20)
        
        recap_header = QHBoxLayout()
        lbl_recap = QLabel("Liste des Équipes")
        lbl_recap.setStyleSheet("color: #334155; font-weight: bold; font-size: 18px; border: none; background: transparent;")
        recap_header.addWidget(lbl_recap)
        recap_header.addStretch()
        
        # NOUVEAU BOUTON SUPPRIMER
        self.btn_delete = QPushButton("Supprimer la sélection")
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.clicked.connect(self.supprimer_equipe)
        recap_header.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Actualiser la liste")
        self.btn_refresh.setObjectName("RefreshBtn")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.clicked.connect(self.charger_equipes_api)
        recap_header.addWidget(self.btn_refresh)
        
        recap_layout.addLayout(recap_header)

        self.table_equipes = QTableWidget(0, 3)
        self.table_equipes.setHorizontalHeaderLabels(["ID (Base de données)", "Nom", "ID Badge attribué"])
        self.table_equipes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_equipes.verticalHeader().setDefaultSectionSize(35)
        self.table_equipes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_equipes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_equipes.verticalHeader().setVisible(False)

        recap_layout.addWidget(self.table_equipes)
        main_layout.addWidget(recap_frame)

        self.charger_equipes_api()

    def remplir_rfid(self):
        chemin_fichier = r'C:\Users\Admin\Desktop\projet_150h\Projet_5_py6ql\supervision\transfer\donnees_rfid.json'
        
        # 1. On va chercher le fichier JSON
        if os.path.exists(chemin_fichier):
            try:
                with open(chemin_fichier, 'r', encoding='utf-8') as f:
                    donnees = json.load(f)
                
                # 2. On parcourt la liste à l'envers (du plus récent au plus ancien)
                for derniere_lecture in reversed(donnees):
                    dernier_badge = derniere_lecture.get("rfid_tag", "")
                    
                    # FILTRE INTELLIGENT : On ignore ce qui ressemble à du GPS ou du JSON
                    # Un vrai badge RFID ne contient ni point (.), ni virgule (,), ni accolade ({)
                    if dernier_badge and "." not in dernier_badge and "," not in dernier_badge and "{" not in dernier_badge:
                        
                        self.in_rfid.setText(dernier_badge)
                        self.in_rfid.setStyleSheet("border: 2px solid #2ecc71; background-color: #e8f8f5; color: black; padding: 10px; border-radius: 6px; font-weight: bold;")
                        return # Succès, on a trouvé un vrai badge, on quitte la fonction !
                        
            except Exception as e:
                print(f"Erreur JSON : {e}")

        # Si on arrive ici, c'est que le fichier est vide ou ne contient aucun vrai badge
        QMessageBox.information(self, "Scan introuvable", "Aucun vrai badge RFID trouvé dans l'historique récent.\nVeuillez passer un badge devant la balise LoRa.")
    
    def capter_nouveau_badge(self, rfid_lu):
        self.dernier_rfid_recu = rfid_lu
        self.remplir_rfid() 

    def charger_equipes_api(self):
        url = f"{config.API_URL}/api/equipes"
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Chargement...")
        
        try:
            reponse = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
            if reponse.status_code == 200:
                equipes = reponse.json()
                self.table_equipes.setRowCount(0)
                for eq in equipes:
                    row = self.table_equipes.rowCount()
                    self.table_equipes.insertRow(row)
                    
                    id_sql = eq.get("id") or eq.get("id_equipe")
                    id_eq_str = str(id_sql)
                    nom = str(eq.get("nom_equipe", "Sans nom"))
                    badge = str(eq.get("id_badge", "N/A"))
                    
                    item_id = QTableWidgetItem(id_eq_str)
                    item_id.setData(Qt.ItemDataRole.UserRole, id_sql) # Stockage invisible de l'ID pour la suppression
                    
                    self.table_equipes.setItem(row, 0, item_id)
                    self.table_equipes.setItem(row, 1, QTableWidgetItem(nom))
                    self.table_equipes.setItem(row, 2, QTableWidgetItem(badge))
        except:
            pass
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("Actualiser la liste")

    def ajouter_equipe(self):
        nom_eq = self.in_nom_equipe.text().strip()
        rfid = self.in_rfid.text().strip()
        if not nom_eq or not rfid:
            QMessageBox.warning(self, "Champs manquants", "Veuillez remplir le nom et scanner un badge RFID.")
            return

        headers = {
            "Authorization": f"Bearer {config.JWT_TOKEN}", 
            "Content-Type": "application/json"
        }
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            url_badge = f"{config.API_URL}/api/badges"
            reponse_badge = requests.post(url_badge, json={"tag_rfid": rfid}, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            if reponse_badge.status_code == 409:
                QMessageBox.warning(self, "Erreur", "Ce badge RFID est déjà assigné à une autre équipe !")
                return
            elif reponse_badge.status_code not in [200, 201]:
                return
                
            id_badge_serveur = reponse_badge.json().get("id") or reponse_badge.json().get("id_badge")

            url_equipe = f"{config.API_URL}/api/equipes"
            reponse_equipe = requests.post(url_equipe, json={"nom_equipe": nom_eq, "id_badge": id_badge_serveur}, headers=headers, timeout=5, proxies={"http": None, "https": None})
            
            if reponse_equipe.status_code in [200, 201]: 
                self.in_nom_equipe.clear()
                self.in_rfid.clear()
                self.dernier_rfid_recu = "" 
                self.charger_equipes_api()
        except:
            pass
        finally:
            QApplication.restoreOverrideCursor()

    # FONCTION DE SUPPRESSION
    def supprimer_equipe(self):
        row = self.table_equipes.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord cliquer sur l'équipe que vous souhaitez supprimer dans le tableau.")
            return
            
        item_id = self.table_equipes.item(row, 0)
        id_sql = item_id.data(Qt.ItemDataRole.UserRole)
        nom_eq = self.table_equipes.item(row, 1).text()

        reponse = QMessageBox.question(self, "Confirmation", f"Voulez-vous vraiment supprimer l'équipe '{nom_eq}' ?\nCette action est irréversible.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reponse == QMessageBox.StandardButton.Yes:
            url = f"{config.API_URL}/api/equipes/{id_sql}"
            headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                res = requests.delete(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
                if res.status_code in [200, 204]:
                    QMessageBox.information(self, "Succès", "L'équipe a bien été supprimée.")
                    self.charger_equipes_api()
                else:
                    QMessageBox.critical(self, "Erreur", f"Le serveur a refusé la suppression (Code {res.status_code}).\nL'équipe est peut-être liée à une course active.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur réseau", str(e))
            finally:
                QApplication.restoreOverrideCursor()