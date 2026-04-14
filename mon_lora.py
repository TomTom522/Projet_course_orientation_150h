import serial
import json
import requests
import time
import random
import config
import re
from PyQt6.QtCore import QThread, pyqtSignal

class LoraThread(QThread):
    status_signal = pyqtSignal(str, str) 
    battery_signal = pyqtSignal(str) 
    position_signal = pyqtSignal(float, float, str) 
    rfid_signal = pyqtSignal(str, str) 
    
    scan_result_signal = pyqtSignal(str, str, bool, str)

    def stop(self):
        self.is_running = False
        if hasattr(self, 'ser') and self.ser.is_open:
            try: self.ser.close()
            except: pass
        self.quit()
        self.wait()

    def run(self):
        self.is_running = True
        print(f"[*] Démarrage de la connexion sur : {config.SERIAL_PORT}")
        
        if config.SERIAL_PORT == "SIMULATEUR": 
            lat, lon = 44.350000, 2.570000 
            while self.is_running:
                lat = round(lat + random.uniform(-0.00001, 0.0001), 6)
                lon = round(lon + random.uniform(-0.00001, 0.0001), 6)
                data = {"id": 1, "lat": lat, "lon": lon, "batterie": random.randint(70, 100)}
                self.position_signal.emit(float(data['lat']), float(data['lon']), str(data['id']))
                self.battery_signal.emit(f"{data['batterie']}%")
                self.envoie_api(data)
                for _ in range(35):
                    if not self.is_running: break
                    time.sleep(0.1)
        else:
            try:
                self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)
                self.status_signal.emit("CONNECTÉ", "#2CC985")
                while self.is_running:
                    if self.ser.in_waiting > 0:
                        try:
                            line = self.ser.readline().decode('utf-8', errors='replace').strip()
                            if not line: continue
                            
                            rfid_match = re.search(r"Message reçu du node (\d+)\s*:\s*(.*)", line)
                            
                            if rfid_match:
                                node_id = rfid_match.group(1)
                                raw_hex_payload = rfid_match.group(2).strip()
                                
                                # ÉTAPE 1 : DÉCODAGE
                                try:
                                    texte_decode = "".join([chr(int(x, 16)) for x in raw_hex_payload.split() if len(x) == 2])
                                except:
                                    texte_decode = raw_hex_payload
                                texte_decode = texte_decode.upper()

                                # ÉTAPE 2 : TRI DU MESSAGE

                                # --- A. CAS DU GPS (Texte avec virgule et point) ---
                                if "," in texte_decode and "." in texte_decode:
                                    try:
                                        parts = texte_decode.split(',')
                                        lat = float(re.sub(r'[^0-9.-]', '', parts[0]))
                                        lon = float(re.sub(r'[^0-9.-]', '', parts[1]))
                                        
                                        # On ignore si le GPS cherche encore son signal (0.0, 0.0)
                                        if lat == 0.0 and lon == 0.0:
                                            continue
                                            
                                        self.position_signal.emit(lat, lon, str(node_id))
                                        self.envoie_api({"id": node_id, "lat": lat, "lon": lon})
                                        continue # C'était un GPS, on arrête là !
                                    except ValueError:
                                        pass

                                clean_content = re.sub(r'[^A-Z0-9%]', '', texte_decode)

                                # --- B. CAS DE LA BATTERIE ---
                                if "BAT" in clean_content or "%" in clean_content:
                                    val_bat = "".join(filter(str.isdigit, clean_content))
                                    if val_bat:
                                        self.battery_signal.emit(f"{val_bat}%")
                                        self.envoie_api({"id": node_id, "batterie": val_bat})
                                    continue

                                # --- C. CAS DU BADGE RFID ---
                                # Un vrai badge ne contient que des lettres de A à F et des chiffres.
                                clean_rfid = re.sub(r'[^A-F0-9]', '', texte_decode)
                                
                                # Sécurité : Si le code est trop court, on l'ignore
                                if len(clean_rfid) < 6:
                                    continue

                                # On remet de jolis espaces pour l'interface
                                rfid_tag = " ".join([clean_rfid[i:i+2] for i in range(0, len(clean_rfid), 2)])

                                print(f"[RFID DÉTECTÉ] Node: {node_id} | Tag: {rfid_tag}")
                                self.rfid_signal.emit(str(node_id), rfid_tag)
                                
                                # On lance la vérification API
                                self.enregistrer_scan_et_valider(node_id, rfid_tag)
                                continue

                            # --- DÉTECTION DU FORMAT JSON NORMAL ---
                            if line.startswith('{'):
                                try:
                                    data = json.loads(line)
                                    id_emetteur = str(data.get('id', '1'))
                                    if 'lat' in data and 'lon' in data:
                                        self.position_signal.emit(float(data['lat']), float(data['lon']), id_emetteur)
                                    if 'batterie' in data:
                                        self.battery_signal.emit(f"{data['batterie']}%")
                                    if 'rfid' in data:
                                        tag = str(data['rfid'])
                                        self.rfid_signal.emit(id_emetteur, tag)
                                        self.enregistrer_scan_et_valider(id_emetteur, tag)
                                    self.envoie_api(data)
                                except json.JSONDecodeError: pass

                        except Exception as e: print(f"Erreur de lecture ligne: {e}")
                    time.sleep(0.01)
            except Exception as e:
                self.status_signal.emit("ERREUR PORT", "red")

    def envoie_api(self, data):
        try:
            headers = {"Authorization": f"Bearer {config.JWT_TOKEN}", "Content-Type": "application/json"}
            id_b = int(data.get('id', 1))
            if 'batterie' in data:
                requests.post(f"{config.API_URL}/api/releves-batterie", json={"id_balise": id_b, "niveau_batterie": int(data['batterie'])}, headers=headers, timeout=2)
            elif 'lat' in data and 'lon' in data:
                requests.put(f"{config.API_URL}/api/balises/{id_b}", json={"latitude": float(data['lat']), "longitude": float(data['lon'])}, headers=headers, timeout=2)
        except: pass

    def enregistrer_scan_et_valider(self, id_balise, rfid_tag):
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}", "Content-Type": "application/json"}
        base_url = config.API_URL
        
        try:
            resp_badges = requests.get(f"{base_url}/api/badges", headers=headers).json()
            if not isinstance(resp_badges, list): return
            
            badge_id = next((b['id'] for b in resp_badges if b.get('tag_rfid', '').replace(' ', '') == rfid_tag.replace(' ', '')), None)
            
            if not badge_id:
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), "Inconnu", False, "Badge non enregistré")
                return

            resp_equipes = requests.get(f"{base_url}/api/equipes", headers=headers).json()
            equipe = next((e for e in resp_equipes if e.get('id_badge') == badge_id), None)
            
            if not equipe or not equipe.get('id_course_actuelle'):
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), "Inconnu", False, "Équipe sans course")
                return

            id_equipe = equipe['id']
            id_course = equipe['id_course_actuelle']
            nom_eq = equipe.get('nom_equipe', f"Équipe {id_equipe}")

            payload = {"id_course": id_course, "id_equipe": id_equipe}
            url_validation = f"{base_url}/api/validation/{id_balise}"
            response = requests.post(url_validation, json=payload, headers=headers, timeout=3)
            
            if response.status_code == 201:
                print(f"[ARBITRE API] ✅ Balise {id_balise} validée pour l'équipe {nom_eq} !")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "OK"}}\n')
                self.scan_result_signal.emit(str(id_balise), nom_eq, True, "Balise validée !")
                
            elif response.status_code == 409:
                data = response.json()
                erreur_msg = data.get('error', 'Ordre incorrect')
                print(f"[ARBITRE API] ❌ Balise {id_balise} refusée ! ({erreur_msg})")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), nom_eq, False, erreur_msg)

        except Exception as e: 
            print(f"[ERREUR] : {e}")

    def _envoyer_ordre_lora(self, message_str):
        try:
            if hasattr(self, 'ser') and self.ser.is_open:
                self.ser.write(message_str.encode('utf-8'))
        except: pass