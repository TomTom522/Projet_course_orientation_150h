import serial
import json
import requests
import time
import random
import config
import re
import os
from PyQt6.QtCore import QThread, pyqtSignal

class LoraThread(QThread):
    # signaux recuperé pour que (main.py) les entende et réagisse
    status_signal = pyqtSignal(str, str) # texte + couleur
    battery_signal = pyqtSignal(str, str) # niveau batt + couleur
    position_signal = pyqtSignal(float, float, str) # Lat, Lon, id_balise
    rfid_signal = pyqtSignal(str, str) # code RFID lu
    scan_result_signal = pyqtSignal(str, str, bool, str) #scan resultat final
    
    def charger_donnees_api(self):
        """Charge ou rafraîchit la liste des équipes depuis l'API"""
        url = f"{config.API_URL.rstrip('/')}/api/equipes"
        headers = {"Authorization": f"Bearer {config.JWT_TOKEN}"}
        try:
            r = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
            if r.status_code == 200:
                self.equipes_locales = r.json()
                print(f"[LORA] {len(self.equipes_locales)} équipes chargées.")
        except Exception as e:
            print(f"[LORA ERREUR] API injoignable : {e}")


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
                self.battery_signal.emit(f"{data['batterie']}%", str(data['id']))
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
                                        self.battery_signal.emit(f"{val_bat}%", str(node_id))
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
                                        self.battery_signal.emit(f"{data['batterie']}%", id_emetteur)
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
            # 1. Récupérer tous les badges pour trouver l'ID correspondant au tag physique
            resp_badges = requests.get(f"{base_url}/api/badges", headers=headers).json()
            if not isinstance(resp_badges, list): return
            
            tag_nettoye = rfid_tag.replace(' ', '').upper()
            
            badge_trouve = next((b for b in resp_badges if b.get('tag_rfid', '').replace(' ', '').upper() == tag_nettoye), None)
            
            if not badge_trouve:
                print(f"[ARBITRE] Tag {tag_nettoye} non trouvé dans la base de données badges")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), "Inconnu", False, "Badge non enregistré")
                return

            badge_id_technique = badge_trouve['id']

            # 2. On cherche l'équipe liée à cet ID de badge
            resp_equipes = requests.get(f"{base_url}/api/equipes", headers=headers).json()

            print(f"[DEBUG ARBITRE] Badge cherché (technique): {badge_id_technique} (type: {type(badge_id_technique)})")
            for e in resp_equipes:
                print(f"[DEBUG ARBITRE] Equipe: {e.get('nom_equipe')} | id_badge={e.get('id_badge')} (type: {type(e.get('id_badge'))})")

            equipe = next((e for e in resp_equipes if str(e.get('id_badge')) == str(badge_id_technique)), None)
            
            # 3. Vérification de l'attribution
            if not equipe:
                print(f"[ARBITRE] Aucune équipe n'est liée au badge technique n°{badge_id_technique} ({tag_nettoye})")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), "Inconnu", False, "Badge non attribué")
                return

            nom_eq = equipe.get('nom_equipe', "Équipe sans nom")
            id_course = equipe.get('id_course_actuelle')

            # 4. Vérification de la course active
            if not id_course:
                print(f"[ARBITRE] {nom_eq} est bien reconnue mais n'a pas de course active.")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), nom_eq, False, "Équipe sans course")
                return

            # 5. Résoudre le node_id LoRa → id_sql de la balise
            resp_balises = requests.get(f"{base_url}/api/balises", headers=headers).json()
            
            # DEBUG TEMPORAIRE - à supprimer une fois résolu
            print(f"[DEBUG BALISES] Node reçu : '{id_balise}' (type: {type(id_balise)})")
            for b in resp_balises:
                print(f"[DEBUG BALISES] BDD → lora_id='{b.get('lora_id')}' (type: {type(b.get('lora_id'))}) | id_sql={b.get('id')}")
            
            balise_sql = next(
                (b for b in resp_balises if str(b.get('lora_id')) == str(id_balise)),
                None
            )
            
            if not balise_sql:
                print(f"[ARBITRE] Node LoRa '{id_balise}' non trouvé dans les balises configurées")
                self._envoyer_ordre_lora(f'{{"target": {id_balise}, "status": "ERR"}}\n')
                self.scan_result_signal.emit(str(id_balise), nom_eq, False, "Balise non configurée dans le système")
                return
            
            id_balise_sql = balise_sql.get('id') or balise_sql.get('id_balise')
            print(f"[ARBITRE] Node LoRa {id_balise} → ID SQL balise : {id_balise_sql}")

            # 6. Envoi de la validation à l'API avec l'ID SQL de la balise
            payload = {"id_course": id_course, "id_equipe": equipe['id']}
            url_validation = f"{base_url}/api/validation/{id_balise_sql}"
            response = requests.post(url_validation, json=payload, headers=headers, timeout=3)
            
            if response.status_code == 201:
                print(f"[ARBITRE API] Balise {id_balise_sql} (node {id_balise}) validée pour {nom_eq} !")
                self._envoyer_ordre_lora(id_balise, "OK")
                self.scan_result_signal.emit(str(id_balise), nom_eq, True, "Validé")
            else:
                msg = response.json().get('error', 'Refusé')
                print(f"[ARBITRE API] Erreur validation: {msg}")
                self._envoyer_ordre_lora(id_balise, "ERR")
                self.scan_result_signal.emit(str(id_balise), nom_eq, False, msg)

        except Exception as e: 
            print(f"[ERREUR CRITIQUE ARBITRE] : {e}")

    def _envoyer_ordre_lora(self, id_balise, status):
        """
        1. Génère le fichier local envoie_donnee.json avec la trame.
        2. Envoie l'acquittement en message UART en direct à la passerelle.
            """
        # --- ÉTAPE 1 : GÉNÉRATION DU FICHIER JSON ---
        try:
            chemin_fichier = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'envoie_donnee.json')
            donnee = {"target": int(id_balise), "status": str(status)}
                
            with open(chemin_fichier, 'w', encoding='utf-8') as f:
                json.dump(donnee, f, indent=4)
            print(f"[FICHIER] envoie_donnee.json mis à jour : {donnee}")
        except Exception as e:
                print(f"[ERREUR FICHIER] Impossible de générer envoie_donnee.json : {e}")

        # --- ÉTAPE 2 : TRANSMISSION DIRECTE UART VIA LE PORT SÉRIE ---
        try:
            if hasattr(self, 'ser') and self.ser.is_open:
                # Trame JSON brute envoyée sur l'UART avec un retour à la ligne
                message_uart = f'{{"target": {id_balise}, "status": "{status}"}}\n'
                self.ser.write(message_uart.encode('utf-8'))
                self.ser.flush()  # Force l'envoi immédiat du buffer
                print(f"[UART -> PASSERELLE] Envoyé avec succès : {message_uart.strip()}")
            else:
                print("[UART ATTENTION] Impossible d'envoyer la trame, le port série n'est pas ouvert.")
        except Exception as e:
            print(f"[ERREUR UART] Échec de la transmission série de l'acquittement : {e}")