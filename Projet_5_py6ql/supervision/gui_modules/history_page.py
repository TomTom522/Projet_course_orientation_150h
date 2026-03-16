import csv
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- STYLE DE LA PAGE (Harmonise en Vert) ---
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; color: #2c3e50; }
            QLabel#Title { font-size: 24px; font-weight: bold; color: #1e293b; margin: 10px 0; }
            QTableWidget { background-color: white; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; }
            QHeaderView::section { background-color: #f8fafc; padding: 12px; font-weight: bold; border: none; color: #334155; border-bottom: 3px solid #27ae60; }
            QPushButton#ExportBtn { background-color: #27ae60; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; }
            QPushButton#ExportBtn:hover { background-color: #219653; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- En-tete (Titre + Bouton Export) ---
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Historique et Alertes Systeme", objectName="Title")
        header_layout.addWidget(lbl_title)
        
        header_layout.addStretch()
        
        btn_export = QPushButton("Exporter en CSV", objectName="ExportBtn")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.clicked.connect(self.export_csv)
        header_layout.addWidget(btn_export)
        
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

    def add_log(self, source, event_type, details, color="#1e293b"):
        """Ajoute un log directement dans le tableau"""
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
        