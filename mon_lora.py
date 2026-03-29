import serial
import json
import requests
import time
import random
import config
from PyQt6.QtCore import QThread, pyqtSignal

# LoraThread hérite de QThread. C'est un processus qui tourne en parallèle de ton interface.
# S'il n'y avait pas ça, le logiciel gèlerait complètement en attendant des données.
class LoraThread(QThread):
    # Création des "Signaux". C'est comme des petits messages que ce thread peut crier
    # pour que l'interface graphique (main.py) les entende et réagisse.
    status_signal = pyqtSignal(str, str) # Envoie un texte et une couleur
    battery_signal = pyqtSignal(str) # Envoie le niveau de batterie en texte
    position_signal = pyqtSignal(float, float, str) # Envoie lat, lon et l'ID de la balise
    rfid_signal = pyqtSignal(str) # Envoie le code RFID lu

    # La fonction 'run' contient le code qui va tourner en boucle dans l'arrière-plan
    def run(self):
        print(f"[*] Démarrage de la connexion sur : {config.SERIAL_PORT}")
        
        # ==========================================
        # MODE SIMULATION (SANS ANTENNE)
        # Pratique quand tu développes sur ton PC sans le vrai matériel
        # ==========================================
        if config.SERIAL_PORT == "SIMULATEUR": 
            
            # Position de départ (Centre de Rodez)
            lat, lon = 44.350000, 2.570000 
            
            # Boucle infinie
            while True:
                # On fait bouger la balise aléatoirement (un petit peu à chaque fois)
                lat = round(lat + random.uniform(-0.00001, 0.0001), 6)
                lon = round(lon + random.uniform(-0.00001, 0.0001), 6)
                
                # Création d'un faux paquet de données (ID 11)
                data = {
                    "id": 11, 
                    "lat": lat, 
                    "lon": lon, 
                    "batterie": random.randint(70, 100) # Batterie aléatoire
                }
                print(f"[SIMULATION] Nouvelles coordonnées : {data}")
                
                # 1. Envoi à l'interface (PyQt6) : On "émet" les signaux
                self.position_signal.emit(float(data['lat']), float(data['lon']), str(data['id']))
                self.battery_signal.emit(f"{data['batterie']}%")
                
                # 2. Envoi à l'API backend Node.js
                self._send_api(data)
                
                # Pause de 3 secondes avant de simuler le prochain point
                time.sleep(3)

        # ==========================================
        # MODE RÉEL (AVEC LA VRAIE ANTENNE USB)
        # ==========================================
        else:
            try:
                # Ouverture du port USB (COMx sur Windows, /dev/ttyUSBx sur Linux)
                ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)
                # On prévient l'interface que c'est connecté !
                self.status_signal.emit("CONNECTÉ", "#2CC985")
                
                while True:
                    # S'il y a des données qui attendent dans le port USB
                    if ser.in_waiting > 0:
                        try:
                            # On lit la ligne, la décode en UTF-8, et on enlève les espaces vides (.strip())
                            line = ser.readline().decode('utf-8', errors='replace').strip()
                            if not line: continue
                            
                            # On transforme le texte JSON reçu du microcontrôleur en dictionnaire Python
                            data = json.loads(line)
                            print(f"[LORA RECU] {data}")
                             
                            # Si le dico contient 'lat' et 'lon', on émet le signal GPS
                            if 'lat' in data and 'lon' in data:
                                self.position_signal.emit(float(data['lat']), float(data['lon']), str(data.get('id', '1')))
                            
                            # Si le dico contient 'batterie', on émet le signal batterie
                            if 'batterie' in data:
                                self.battery_signal.emit(f"{data['batterie']}%")
                            
                            # Si le dico contient 'rfid', on émet le signal RFID
                            if 'rfid' in data:
                                self.rfid_signal.emit(str(data['rfid']))

                            # On envoie également ces données vers la base de données via l'API
                            self._send_api(data)

                            # Petite pause pour ne pas surcharger le processeur
                            time.sleep(0.1)
                        except Exception as e:
                            print(f"Erreur ligne: {e}")
                    time.sleep(0.1)
            except Exception as e:
                # Si le port n'est pas trouvé (antenne débranchée par ex.)
                self.status_signal.emit("ERREUR PORT", "red")
                print(f"Erreur critique Serial: {e}")

    # Fonction pour envoyer les données LoRa vers l'API externe (Docker)
    def _send_api(self, data):
        """Envoie les trames décodées vers l'API backend"""
        try:
            # Sécurité via clé API présente dans config.py
            headers = {"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"}
            id_b = int(data.get('id', 1)) # On récupère l'ID, par défaut 1
            
            if 'batterie' in data:
                url = f"{config.API_URL}/api/releves-batterie"
                # Requête POST pour enregistrer un nouveau niveau de batterie
                requests.post(url, json={"id_balise": id_b, "niveau_batterie": int(data['batterie'])}, headers=headers, timeout=2)
                
            elif 'lat' in data and 'lon' in data:
                url = f"{config.API_URL}/api/balises/{id_b}"
                # Requête PUT pour modifier la position actuelle de la balise dans la BDD
                requests.put(url, json={"latitude": float(data['lat']), "longitude": float(data['lon'])}, headers=headers, timeout=2)
        except Exception as e:
            pass # On ignore les erreurs API 