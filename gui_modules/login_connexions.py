import requests
import json
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
import config

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connexion au Serveur")
        
        # Fenêtre un peu plus grande pour respirer avec le nouveau design
        self.setFixedSize(380, 360) 
        
        # --- STYLE GLOBAL (THÈME MODERNE & VERT) ---
        self.setStyleSheet("""
            QDialog { 
                background-color: #f4f7f6; 
                font-family: 'Segoe UI'; 
            }
            QLabel { 
                font-weight: bold; 
                color: #2c3e50; 
                font-size: 14px; 
            }
            QLabel#Title { 
                color: #27ae60; 
                font-size: 22px; 
                font-weight: 900; 
                margin-bottom: 15px; 
            }
            QLineEdit { 
                background-color: white; 
                padding: 10px; 
                border: 2px solid #cbd5e1; 
                border-radius: 8px; 
                font-size: 14px; 
                color: #334155;
            }
            QLineEdit:focus { 
                border: 2px solid #27ae60; 
            }
            QPushButton { 
                background-color: #27ae60; 
                color: white; 
                font-size: 15px; 
                font-weight: bold; 
                padding: 12px; 
                border-radius: 8px; 
                border: none; 
                margin-top: 15px;
            }
            QPushButton:hover { 
                background-color: #219653; 
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        # Titre
        lbl_title = QLabel("Supervision LoRa")
        lbl_title.setObjectName("Title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # Champ Utilisateur
        self.lbl_user = QLabel("Nom d'utilisateur")
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ex: admin")
        layout.addWidget(self.lbl_user)
        layout.addWidget(self.txt_user)

        # Champ Mot de passe
        self.lbl_pass = QLabel("Mot de passe")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("••••••••")
        layout.addWidget(self.lbl_pass)
        layout.addWidget(self.txt_pass)

        # Bouton Connexion
        self.btn_login = QPushButton("Se connecter")
        self.btn_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_login.clicked.connect(self.tenter_connexion)
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
        
        # connexions a l'api pour le login de l'organisateur
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"ApiKey {config.API_KEY}" 
        } 
        
        payload = {"username": user, "password": pwd}
        
        try:
            rep = requests.post(url, json=payload, headers=headers, timeout=5)
            if rep.status_code == 200:
                data = rep.json()
                
                # Le serveur nous donne le JWT, on le stocke
                config.JWT_TOKEN = data.get("accessToken") 
                
                # On sauvegarde le refreshToken pour l'auto-login
                refresh_token = data.get("refreshToken")
                if refresh_token:
                    try:
                        with open("session.json", "w", encoding="utf-8") as f:
                            json.dump({"refreshToken": refresh_token}, f)
                    except Exception as e:
                        print(f"Impossible de sauvegarder la session : {e}")
                
                self.accept() # On ferme la fenêtre
            else:
                QMessageBox.warning(self, "Accès refusé", "Identifiants ou mot de passe incorrects.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de se connecter au serveur API :\n{e}")
        finally:
            # On réactive le bouton en cas d'erreur pour que l'utilisateur puisse réessayer
            self.btn_login.setText("Se connecter")
            self.btn_login.setEnabled(True)