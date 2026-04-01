import serial
import json
import requests
import time
import random
import config
import re
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
                            # On lit la ligne, la décode en UTF-8, et on enlève les espaces vides
                            line = ser.readline().decode('utf-8', errors='replace').strip()
                            if not line: 
                                continue
                            
                            # --- 1. DÉTECTION DU MESSAGE RFID (TEXTE BRUT) ---
                            # On cherche le format : "Message reçu du node X : XX XX XX..."
                            rfid_match = re.search(r"Message reçu du node (\d+)\s*:\s*(.*)", line)
                            
                            if rfid_match:
                                node_id = rfid_match.group(1)
                                rfid_tag_brut = rfid_match.group(2).strip().upper()
                                

                                # --- DÉécodage du double héxadéciamal pour avoir le bon RFID ---
                                try:
                                    # 1. On transforme "46 41 34" en "FA4"
                                    tag_lettres = "".join([chr(int(x, 16)) for x in rfid_tag_brut.split()])
                                    # 2. On remet les espaces tous les 2 caractères pour avoir "FA 48 8D 2E"
                                    rfid_tag = " ".join([tag_lettres[i:i+2] for i in range(0, len(tag_lettres), 2)])
                                except Exception:
                                    # Sécurité : si un jour l'antenne envoie le bon format direct, on ne plante pas
                                    rfid_tag = rfid_tag_brut 

                                print(f"[RFID DÉTECTÉ] Node: {node_id} | Tag: {rfid_tag}")
                                # On envoie le tag à main.py pour traitement et sauvegarde JSON
                                self.rfid_signal.emit(rfid_tag)
                                continue # On passe à la ligne suivante, pas besoin de tester le JSON

                            # --- 2. DÉTECTION DES DONNÉES GPS/BATTERIE (JSON) ---
                            # On ne tente le JSON que si la ligne commence par une accolade
                            if line.startswith('{'):
                                try:
                                    data = json.loads(line)
                                    print(f"[LORA RECU] {data}")
                                    
                                    # Signal GPS
                                    if 'lat' in data and 'lon' in data:
                                        self.position_signal.emit(float(data['lat']), float(data['lon']), str(data.get('id', '1')))
                                    
                                    # Signal Batterie
                                    if 'batterie' in data:
                                        self.battery_signal.emit(f"{data['batterie']}%")
                                    
                                    # Signal RFID (si envoyé sous forme de JSON par une autre balise)
                                    if 'rfid' in data:
                                        self.rfid_signal.emit(str(data['rfid']))

                                    # Envoi vers la base de données (API Docker)
                                    self._send_api(data)
                                    
                                except json.JSONDecodeError:
                                    print(f"[ERREUR JSON] Ligne corrompue : {line}")
                            else:
                                # Si ce n'est ni du RFID connu, ni du JSON, c'est un message de debug
                                print(f"[DEBUG ESP32] {line}")

                            # Petite pause pour ne pas surcharger le processeur
                            time.sleep(0.05)

                        except Exception as e:
                            print(f"Erreur de traitement ligne: {e}")
                    time.sleep(0.01) # Fréquence d'écoute du port série
            
            # CE BLOC ÉTAIT MANQUANT
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