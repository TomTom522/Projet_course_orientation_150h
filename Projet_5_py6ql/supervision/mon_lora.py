import serial
import json
import requests
import time
import config
from PyQt6.QtCore import QThread, pyqtSignal

class LoraThread(QThread):
    status_signal = pyqtSignal(str, str)
    battery_signal = pyqtSignal(str)
    position_signal = pyqtSignal(float, float, str)
    rfid_signal = pyqtSignal(str)

    def run(self):
        print(f"[*] Thread LoRa démarré sur {config.SERIAL_PORT}")
        try:
            ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)
            self.status_signal.emit("CONNECTÉ", "#2CC985")
            while True:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='replace').strip()
                        if not line: continue
                        data = json.loads(line)
                        
                        # Transmission vers l'IHM
                        if 'lat' in data and 'lon' in data:
                            self.position_signal.emit(float(data['lat']), float(data['lon']), str(data.get('id', '1')))
                        if 'batterie' in data:
                            self.battery_signal.emit(f"{data['batterie']}%")
                        if 'rfid' in data:
                            self.rfid_signal.emit(str(data['rfid']))

                        # Envoi vers l'API Node.js
                        self._send_api(data)
                    except Exception as e:
                        print(f"Erreur boucle: {e}")
                time.sleep(0.1)
        except Exception as e:
            self.status_signal.emit("ERREUR PORT", "red")
            print(f"Erreur critique: {e}")

    def _send_api(self, data):
        try:
            url = f"{config.API_URL}/api/balises"
            headers = {
                "Authorization": f"ApiKey {config.API_KEY}", 
                "Content-Type": "application/json"
            }
            id_balise = int(data.get('id', 1)) 
            reponse = None

            if 'batterie' in data:
                url = f"{config.API_URL}/api/releves-batterie"
                payload = {"id_balise": id_balise, "niveau_batterie": int(str(data['batterie']).replace('%',''))}
                reponse = requests.post(url, json=payload, headers=headers, timeout=2)
                
            elif 'rfid' in data:
                # Ajout du préfixe /api/
                url = f"{config.API_URL}/api/etat-course"
                payload = {"id_course": 1, "id_equipe": id_balise, "id_balise": id_balise, "valide": True}
                reponse = requests.post(url, json=payload, headers=headers, timeout=2)
                
            elif 'lat' in data and 'lon' in data:
                # Ajout du préfixe /api/
                url = f"{config.API_URL}/api/balises/{id_balise}"
                payload = {"latitude": float(data['lat']), "longitude": float(data['lon'])}
                reponse = requests.put(url, json=payload, headers=headers, timeout=2)

            # Gestion des logs de succès et d'erreur
            if reponse and reponse.status_code in [200, 201]:
                print(f"[API LORA] Donnée balise {id_balise} synchronisée avec succès !")
            elif reponse:
                print(f"[ERREUR API LORA] L'API a rejeté la requête. Code: {reponse.status_code}, Détail: {reponse.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"[ERREUR LORA] Impossible de joindre l'API à l'adresse {config.API_URL}")
        except Exception as e:
            print(f"[ERREUR API LORA] : {e}")