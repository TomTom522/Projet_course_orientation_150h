import csv
from datetime import datetime

import requests
import config
# AJOUT DE QComboBox ICI :
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QFileDialog, QMessageBox, QInputDialog, QComboBox)
from PyQt6.QtCore import Qt, QMarginsF
from PyQt6.QtGui import QColor, QCursor, QTextDocument, QPdfWriter, QPageSize, QPageLayout

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- STYLE DE LA PAGE ---
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; color: #2c3e50; }
            QLabel#Title { font-size: 24px; font-weight: bold; color: #1e293b; margin: 10px 0; }
            QTableWidget { background-color: white; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; }
            QHeaderView::section { background-color: #f8fafc; padding: 12px; font-weight: bold; border: none; color: #334155; border-bottom: 3px solid #27ae60; }
            
            QPushButton#ExportBtn { background-color: #27ae60; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; }
            QPushButton#ExportBtn:hover { background-color: #219653; }
            
            QPushButton#PdfBtn { background-color: #8e44ad; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; }
            QPushButton#PdfBtn:hover { background-color: #9b59b6; }
            
            /* NOUVEAU : Style pour le menu de filtre */
            QComboBox { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: white; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- En-tete (Titre + Filtres + Boutons Export) ---
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Historique et Alertes Systeme", objectName="Title")
        header_layout.addWidget(lbl_title)
        
        # ==========================================
        # Menu déroulant pour filtrer l'historique
        # ==========================================
        self.combo_filtre = QComboBox()
        self.combo_filtre.addItems(["Tous les événements", "Position GPS", "Scan RFID", "Batterie", "Autre"])
        self.combo_filtre.currentTextChanged.connect(self.filtrer_historique)
        header_layout.addWidget(self.combo_filtre)
        
        header_layout.addStretch()
        
        # Bouton CSV
        btn_export = QPushButton("Exporter en CSV", objectName="ExportBtn")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.clicked.connect(self.export_csv)
        header_layout.addWidget(btn_export)

        # Bouton PDF
        btn_export_pdf = QPushButton("Générer Rapport Final (PDF)", objectName="PdfBtn")
        btn_export_pdf.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export_pdf.clicked.connect(self.exporter_rapport_pdf)
        header_layout.addWidget(btn_export_pdf)
        
        layout.addLayout(header_layout)

        # --- TABLEAU UNIQUE ---
        self.table_systeme = self.creer_tableau(["Heure", "Source / ID", "Type d'Evenement", "Details Techniques"])
        layout.addWidget(self.table_systeme)

    def creer_tableau(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return table

    # ==========================================
    # Fonction de filtrage du tableau
    # ==========================================
    def filtrer_historique(self, choix):
        """Affiche ou masque les lignes selon le filtre sélectionné"""
        for row in range(self.table_systeme.rowCount()):
            item_type = self.table_systeme.item(row, 2) # Colonne Type d'Evenement
            if item_type:
                texte_type = item_type.text()
                
                if choix == "Tous les événements" or choix == texte_type:
                    self.table_systeme.setRowHidden(row, False)
                elif choix == "Autre" and "📍" not in texte_type and "🏷️" not in texte_type and "🔋" not in texte_type:
                    self.table_systeme.setRowHidden(row, False)
                else:
                    self.table_systeme.setRowHidden(row, True)

    def add_log(self, source, event_type, details, color="#1e293b"):
        """Ajoute un log directement dans le tableau avec Auto-Détection"""
        
        # ================
        # AUTO-DÉTECTION 
        # ================
        details_min = str(details).lower()
        event_min = str(event_type).lower()
        
        if "lat" in details_min or "lon" in details_min or "gps" in event_min:
            event_type = "Position GPS"
            color = "#2980b9" # Bleu
        elif "badge" in details_min or "tag" in details_min or "rfid" in event_min:
            event_type = "Scan RFID"
            color = "#27ae60" # Vert
        elif "batterie" in details_min or "batt" in event_min:
            event_type = "Batterie"
            color = "#e67e22" # Orange
        else:
            event_type = f"{event_type}" # On ajoute une icône par défaut
            color = "#8e44ad" # Violet pour les infos diverses

        heure = datetime.now().strftime("%H:%M:%S")
            
        row = 0
        self.table_systeme.insertRow(row)
        
        self.table_systeme.setItem(row, 0, QTableWidgetItem(heure))
        self.table_systeme.setItem(row, 1, QTableWidgetItem(source))
        
        item_evt = QTableWidgetItem(event_type)
        item_evt.setForeground(QColor(color))
        item_evt.setFont(self.font())
        self.table_systeme.setItem(row, 2, item_evt)
        
        self.table_systeme.setItem(row, 3, QTableWidgetItem(details))
        
        # On s'assure que la nouvelle ligne respecte le filtre actuellement sélectionné
        self.filtrer_historique(self.combo_filtre.currentText())

    def export_csv(self):
        """Exporte le contenu du tableau dans un fichier CSV"""
        if self.table_systeme.rowCount() == 0:
            QMessageBox.warning(self, "Export impossible", "L'historique est vide.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder l'historique", "historique_systeme.csv", "Fichiers CSV (*.csv)")
        
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    
                    # Export Systeme
                    writer.writerow(["--- HISTORIQUE ET ALERTES SYSTEME ---"])
                    writer.writerow(["Heure", "Source", "Evenement", "Details"])
                    for row in range(self.table_systeme.rowCount()):
                        writer.writerow([self.table_systeme.item(row, col).text() if self.table_systeme.item(row, col) else "" for col in range(4)])
                        
                QMessageBox.information(self, "Succes", f"Historique exporte avec succes :\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export :\n{e}")

    # --- FONCTION DE GÉNÉRATION DU PDF ---
    def exporter_rapport_pdf(self):
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}

        # --- 1. SÉLECTION DE LA COURSE VIA L'API ---
        try:
            r_courses = requests.get(f"{config.API_URL}/api/courses", headers=headers, timeout=5)
            
            if r_courses.status_code == 200:
                courses = r_courses.json()
                if not courses:
                    QMessageBox.warning(self, "Attention", "Aucune course n'existe dans la base de données.")
                    return
                
                choix_courses = [f"{c['id']} - {c.get('nom_course', 'Course sans nom')}" for c in courses]
                
                item, ok = QInputDialog.getItem(self, "Sélection de la course", 
                                                "Pour quelle course voulez-vous générer le rapport ?", 
                                                choix_courses, 0, False)
                
                if not ok or not item:
                    return 
                    
                id_course_actuelle = int(item.split(" - ")[0])
                
            else:
                QMessageBox.warning(self, "Erreur API", "Impossible de récupérer la liste des courses.")
                return
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur Réseau", f"Le serveur API est injoignable :\n{e}")
            return

        # --- 2. DEMANDER OÙ SAUVEGARDER LE FICHIER PDF ---
        nom_defaut = f"Rapport_Course_{id_course_actuelle}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        chemin_fichier, _ = QFileDialog.getSaveFileName(self, "Sauvegarder le rapport PDF", nom_defaut, "Fichiers PDF (*.pdf)")
        
        if not chemin_fichier:
            return

        # --- 3. RÉCUPÉRATION DES DONNÉES DE LA COURSE DEPUIS L'API ---
        try:
            r_equipes = requests.get(f"{config.API_URL}/api/equipes", headers=headers, timeout=5)
            if r_equipes.status_code != 200:
                QMessageBox.warning(self, "Erreur API", "Impossible de récupérer les données des équipes.")
                return
            
            r_ordre = requests.get(f"{config.API_URL}/api/ordre-balises/course/{id_course_actuelle}", headers=headers, timeout=5)
            if r_ordre.status_code != 200:
                QMessageBox.warning(self, "Erreur API", "Impossible de récupérer les données de l'ordre des balises. Connection impossible")
                return

            r_etat = requests.get(f"{config.API_URL}/api/etat-course/course/{id_course_actuelle}", headers=headers, timeout=5)

            if r_etat.status_code != 200:
                if r_etat.status_code == 404:
                    donnees_etat = []
                else:
                    QMessageBox.warning(self, "Erreur API", f"Impossible de récupérer l'état de la course.\nCode HTTP : {r_etat.status_code}\nDétails : {r_etat.text}")
                    return
            else:
                donnees_etat = r_etat.json()
            
            donnees_equipes = r_equipes.json()
            donnees_ordre = r_ordre.json()
            
            # ==========================================
            # --- VÉRIFICATIONS DES DONNÉES VIDES ---
            # ==========================================
            if not donnees_ordre:
                QMessageBox.information(self, "Parcours Vide", "Aucune balise n'a été configurée pour cette course. Impossible de générer un rapport.")
                return

            if not donnees_etat:
                reponse = QMessageBox.question(self, "Course non commencée", 
                                               "Aucune balise n'a encore été validée par les équipes.\nVoulez-vous quand même générer un rapport vierge ?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reponse == QMessageBox.StandardButton.No:
                    return
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur Réseau", f"Le serveur API est injoignable :\n{e}")
            return
        
        # --- 4. TRAITEMENT ET CALCUL DU CLASSEMENT ---
        calculs_equipes = {}
        
        for eq in donnees_equipes:
            course_eq_id = eq.get('id_course_actuelle', eq.get('id_course'))
            if str(course_eq_id) == str(id_course_actuelle):
                eq_id = eq.get('id', eq.get('id_equipe'))
                if eq_id is not None:
                    calculs_equipes[eq_id] = {
                        "nom": eq.get('nom_equipe', f"Équipe {eq_id}"),
                        "total_balises": 0,
                        "balises_trouvees": 0,
                        "premier_passage": None,
                        "dernier_passage": None,
                        "penalites": 0 
                    }

        for ordre in donnees_ordre:
            id_eq = ordre.get('id_equipe')
            if id_eq in calculs_equipes:
                calculs_equipes[id_eq]['total_balises'] += 1

        for etat in donnees_etat:
            id_eq = etat.get('id_equipe')
            if etat.get('valide') == True and id_eq in calculs_equipes:
                calculs_equipes[id_eq]['balises_trouvees'] += 1
                
                date_str = etat.get('created_at', '')
                if date_str:
                    try:
                        heure_passage = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        if calculs_equipes[id_eq]['premier_passage'] is None or heure_passage < calculs_equipes[id_eq]['premier_passage']:
                            calculs_equipes[id_eq]['premier_passage'] = heure_passage
                        if calculs_equipes[id_eq]['dernier_passage'] is None or heure_passage > calculs_equipes[id_eq]['dernier_passage']:
                            calculs_equipes[id_eq]['dernier_passage'] = heure_passage
                    except ValueError:
                        pass 

        stats_course = []
        for id_eq, data in calculs_equipes.items():
            temps_str = "00:00:00"
            temps_brut = 999999 
            
            if data['premier_passage'] and data['dernier_passage']:
                duree = data['dernier_passage'] - data['premier_passage']
                temps_str = str(duree).split('.')[0] 
                temps_brut = duree.total_seconds()

            stats_course.append({
                "equipe": data['nom'],
                "temps_brut": temps_brut,
                "temps": temps_str,
                "balises_format": f"{data['balises_trouvees']}/{data['total_balises']}",
                "balises_trouvees": data['balises_trouvees'],
                "penalites": data['penalites']
            })

        stats_course.sort(key=lambda x: (-x['balises_trouvees'], x['temps_brut']))

        for index, stat in enumerate(stats_course):
            stat['position'] = index + 1

        # --- Extraction des données du tableau ---
        lignes_html = ""
        nombre_de_lignes = self.table_systeme.rowCount()

        for row in range(nombre_de_lignes):
            heure = self.table_systeme.item(row, 0).text() if self.table_systeme.item(row, 0) else ""
            equipe = self.table_systeme.item(row, 1).text() if self.table_systeme.item(row, 1) else ""
            evenement = self.table_systeme.item(row, 2).text() if self.table_systeme.item(row, 2) else ""
            details = self.table_systeme.item(row, 3).text() if self.table_systeme.item(row, 3) else ""

            # On ne met dans le rapport que les lignes importantes (Validations)
            # Tu peux ajuster le mot clé selon ce qui s'affiche dans ton tableau
            if "Validée" in evenement or "RFID" in evenement:
                lignes_html += f"""
                <tr>
                    <td style='text-align:center;'>{heure}</td>
                    <td>{equipe}</td>
                    <td style='text-align:center;'>{evenement}</td>
                    <td>{details}</td>
                </tr>
                """

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; }}
                h1 {{ color: #27ae60; text-align: center; font-size: 32px; }}
                h2 {{ color: #2c3e50; font-size: 18px; border-bottom: 2px solid #27ae60; padding-bottom: 5px; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background-color: #f8fafc; color: #475569; padding: 12px; border-bottom: 3px solid #27ae60; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                .footer {{ text-align: right; font-size: 10px; color: #7f8c8d; margin-top: 50px; }}
            </style>
        </head>
        <body>
            <h1>🏆 Rapport de Course LoRa</h1>
            <p style='text-align: center; color: #7f8c8d;'>Course ID: {id_course_actuelle} | Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            
            <h2>Classement Final</h2>
            <table>
                <thead>
                    <tr>
                        <th style='text-align:center;'>Position</th>
                        <th>Nom de l'Équipe</th>
                        <th style='text-align:center;'>Temps Chronométré</th>
                        <th style='text-align:center;'>Balises Validées</th>
                    </tr>
                </thead>
                <tbody>
                    {lignes_html}
                </tbody>
            </table>
            <div class="footer">
                Document généré automatiquement par le Logiciel de Supervision LoRa.
            </div>
        </body>
        </html>
        """

        # --- 6. CONVERSION ET SAUVEGARDE DU PDF ---
        try:
            document = QTextDocument()
            document.setHtml(html_content)

            pdf_writer = QPdfWriter(chemin_fichier)
            pdf_writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            pdf_writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

            document.print(pdf_writer)
            
            QMessageBox.information(self, "Succès", f"Le rapport PDF a été généré avec succès \n\nEnregistré sous :\n{chemin_fichier}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de générer le PDF :\n{str(e)}")