import requests
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
import config

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connexion au Serveur")
        self.setFixedSize(320, 220)
        self.setStyleSheet("""
            QDialog { background-color: #f4f7f6; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #2c3e50; }
            QLineEdit { padding: 8px; border: 1px solid #cbd5e1; border-radius: 5px; }
            QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        
        layout = QVBoxLayout(self)
        
        self.lbl_user = QLabel("Identifiant :")
        self.txt_user = QLineEdit()
        
        self.lbl_pass = QLabel("Mot de passe :")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.btn_login = QPushButton("Se connecter")
        self.btn_login.clicked.connect(self.tenter_connexion)
        
        layout.addWidget(self.lbl_user)
        layout.addWidget(self.txt_user)
        layout.addWidget(self.lbl_pass)
        layout.addWidget(self.txt_pass)
        layout.addSpacing(10)
        layout.addWidget(self.btn_login)

    def tenter_connexion(self):
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text().strip()
        
        if not user or not pwd:
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs.")
            return

        self.btn_login.setText("Connexion en cours...")
        self.btn_login.setEnabled(False)
        self.repaint()
        
        url = f"{config.API_URL}/api/auth/login" 
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"ApiKey {config.API_KEY}" 
        } 
        
        payload = {"username": user, "password": pwd}
        
        try:
            rep = requests.post(url, json=payload, headers=headers, timeout=5)
            if rep.status_code == 200:
                data = rep.json()
                
                # Le serveur nous donne le JWT, on le stocke !
                config.JWT_TOKEN = data.get("accessToken") 
                
                self.accept() # On ferme la fenêtre
            else:
                QMessageBox.warning(self, "Accès refusé", "Identifiants ou mot de passe incorrects.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur Serveur", f"Impossible de joindre l'API.\n{e}")
        
        self.btn_login.setText("Se connecter")
        self.btn_login.setEnabled(True)