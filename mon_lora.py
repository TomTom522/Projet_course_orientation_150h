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
    
    # MODIFICATION ICI : On envoie maintenant deux chaînes de caractères (ID balise, Code RFID)
    rfid_signal = pyqtSignal(str, str) 

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
                self.envoie_api(data)
                
                # Pause de 3 secondes avant de simuler le prochain point
                time.sleep(3)

        # ==========================================
        # MODE RÉEL (AVEC LA VRAIE ANTENNE USB)
        # ==========================================
        else:
            try:
                # Ouverture du port USB. ATTENTION: Modifié en self.ser pour pouvoir écrire dessus plus tard
                self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)
                # On prévient l'interface que c'est connecté !
                self.status_signal.emit("CONNECTÉ", "#2CC985")
                
                while True:
                    # S'il y a des données qui attendent dans le port USB
                    if self.ser.in_waiting > 0:
                        try:
                            # On lit la ligne, la décode en UTF-8, et on enlève les espaces vides
                            line = self.ser.readline().decode('utf-8', errors='replace').strip()
                            if not line: 
                                continue
                            
                            # --- 1. DÉTECTION DU MESSAGE RFID (TEXTE BRUT) ---
                            # On cherche le format : "Message reçu du node X : XX XX XX..."
                            rfid_match = re.search(r"Message reçu du node (\d+)\s*:\s*(.*)", line)
                            
                            if rfid_match:
                                node_id = rfid_match.group(1)
                                rfid_tag_brut = rfid_match.group(2).strip().upper()
                                
                                # --- Décodage du double héxadécimal pour avoir le bon RFID ---
                                try:
                                    # 1. On transforme "46 41 34" en "FA4"
                                    tag_lettres = "".join([chr(int(x, 16)) for x in rfid_tag_brut.split()])
                                    # 2. On remet les espaces tous les 2 caractères pour avoir "FA 48 8D 2E"
                                    rfid_tag = " ".join([tag_lettres[i:i+2] for i in range(0, len(tag_lettres), 2)])
                                except Exception:
                                    # Sécurité : si un jour l'antenne envoie le bon format direct, on ne plante pas
                                    rfid_tag = rfid_tag_brut 

                                print(f"[RFID DÉTECTÉ] Node: {node_id} | Tag: {rfid_tag}")
                                
                                # On envoie l'ID ET le tag à main.py
                                self.rfid_signal.emit(str(node_id), rfid_tag)
                                
                                # NOUVEAU : On lance l'arbitre !
                                self.verifier_et_enregistrer_scan(node_id, rfid_tag)
                                
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
                                        id_emetteur = str(data.get('id', 'Inconnu'))
                                        self.rfid_signal.emit(id_emetteur, str(data['rfid']))
                                        
                                        # NOUVEAU : On lance l'arbitre ici aussi si le RFID passe par JSON
                                        if id_emetteur != 'Inconnu':
                                            self.verifier_et_enregistrer_scan(id_emetteur, str(data['rfid']))

                                    # Envoi vers la base de données (API Docker)
                                    self.envoie_api(data)
                                    
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
    def envoie_api(self, data):
        """Envoie les trames décodées vers l'API backend"""
        try:
            # Sécurité via clé API présente dans config.py
            headers = {"Authorization": f"ApiKey {config.API_KEY}", "Content-Type": "application/json"}
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

    # ==========================================
    # FONCTIONS : L'ARBITRE DE LA COURSE
    # ==========================================
    def verifier_et_enregistrer_scan(self, balise_scannee_id, rfid_tag):
        """
        Fait l'enquête en direct sur l'API pour savoir si le scan est valide ou non.
        """
        headers = {
            "Authorization": f"ApiKey {config.API_KEY}", 
            "Content-Type": "application/json"
        }
        base_url = config.API_URL

        try:
            # --- ETAPE 1 : Trouver l'ID du badge ---
            resp_badges = requests.get(f"{base_url}/api/badges", headers=headers).json()
            if type(resp_badges) is not list:
                print(f"[ARBITRE] L'API a renvoyé une erreur au lieu des badges : {resp_badges}")
                return False

            badge_id = None
            for b in resp_badges:
                if b.get('tag_rfid', '').replace(' ', '') == rfid_tag.replace(' ', ''):
                    badge_id = b['id']
                    break
            
            if not badge_id:
                print(f"[ARBITRE] Badge {rfid_tag} inconnu dans la BDD.")
                return False

            # --- ETAPE 2 : Trouver l'équipe associée ---
            resp_equipes = requests.get(f"{base_url}/api/equipes", headers=headers).json()
            equipe = None
            if type(resp_equipes) is list:
                for e in resp_equipes:
                    if e.get('id_badge') == badge_id:
                        equipe = e
                        break
            
            if not equipe:
                print(f"[ARBITRE] Aucune équipe n'utilise le badge {rfid_tag}.")
                return False

            id_equipe = equipe.get('id')
            id_course = equipe.get('id_course_actuelle')

            # SÉCURITÉ : Vérifier que l'équipe est bien rattachée à une course
            if not id_course:
                print(f"[ARBITRE] L'équipe '{equipe.get('nom_equipe')}' n'a aucune 'id_course_actuelle' définie en BDD !")
                return False

            # --- ETAPE 3 : Récupérer le scénario de l'équipe ---
            url_scenario = f"{base_url}/api/ordre-balises/course/{id_course}/equipe/{id_equipe}"
            scenario = requests.get(url_scenario, headers=headers).json()
            
            # SÉCURITÉ : Vérifier que le scénario est bien une liste et pas un message d'erreur
            if type(scenario) is not list:
                print(f"[ARBITRE] Erreur API sur le scénario (Course {id_course}, Equipe {id_equipe}) : {scenario}")
                return False

            # On s'assure que c'est bien trié par position
            scenario_trie = sorted(scenario, key=lambda x: x.get('position_balise', 0))
            ordre_attendu = [etape['id_balise'] for etape in scenario_trie]

            if len(ordre_attendu) == 0:
                print(f"[ARBITRE] Le scénario de l'équipe '{equipe.get('nom_equipe')}' est vide (aucune balise assignée) !")
                return False

            # --- ETAPE 4 : Regarder l'historique pour savoir où ils en sont ---
            url_etat = f"{base_url}/api/etat-course/course/{id_course}"
            historique = requests.get(url_etat, headers=headers).json()
            
            # On compte combien de bonnes balises cette équipe a déjà bipé
            nb_valides = 0
            if type(historique) is list:
                for passage in historique:
                    if passage.get('id_equipe') == id_equipe and passage.get('valide') == True:
                        nb_valides += 1
            else:
                print(f"[ARBITRE DEBUG] L'historique n'est pas une liste ou est vide : {historique}")

            # --- ETAPE 5 : La Comparaison ! ---
            if nb_valides >= len(ordre_attendu):
                print(f"[ARBITRE] L'équipe '{equipe.get('nom_equipe')}' a déjà fini la course !")
                est_valide = False
            else:
                balise_attendue = ordre_attendu[nb_valides]
                # On compare (en string pour éviter les soucis de int/str)
                est_valide = (str(balise_scannee_id) == str(balise_attendue))

            # --- ETAPE 6 : Enregistrement dans la BDD ---
            payload_etat = {
                "id_course": id_course,
                "id_equipe": id_equipe,
                "id_balise": int(balise_scannee_id),
                "valide": est_valide
            }
            requests.post(f"{base_url}/api/etat-course", json=payload_etat, headers=headers)

            # --- ETAPE 7 : Envoi du signal physique à l'antenne ---
            if est_valide:
                print(f"[ARBITRE] ✅ Équipe '{equipe.get('nom_equipe')}' - BONNE BALISE ({balise_scannee_id}) !")
                self._envoyer_ordre_lora(f'{{"target": {balise_scannee_id}, "status": "OK"}}\n')
            else:
                attendu = ordre_attendu[nb_valides] if nb_valides < len(ordre_attendu) else "FIN"
                print(f"[ARBITRE] ❌ Équipe '{equipe.get('nom_equipe')}' - MAUVAISE BALISE (scanné: {balise_scannee_id}, attendu: {attendu})")
                self._envoyer_ordre_lora(f'{{"target": {balise_scannee_id}, "status": "ERR", "next": {attendu}}}\n')

        except Exception as e:
            print(f"[ARBITRE ERREUR] Impossible de vérifier le badge : {e}")

    def _envoyer_ordre_lora(self, message_str):
        """Écrit sur le port série USB pour que l'antenne Master transmette à la balise"""
        try:
            # On vérifie que la connexion existe bien et est ouverte
            if hasattr(self, 'ser') and self.ser.is_open:
                self.ser.write(message_str.encode('utf-8'))
        except Exception as e:
            print(f"[ERREUR LORA] Impossible d'envoyer la commande : {e}")