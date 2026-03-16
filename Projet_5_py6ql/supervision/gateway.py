import serial
import json
import requests
import config
import time

def start_gateway():
    print("================================================")
    print(f"[*] Gateway LoRa démarrée")
    print(f"[*] Tentative de connexion au port {config.SERIAL_PORT}...")
    print("================================================")
    
    try:
        # Ouverture du port série (T-Beam connectée en USB)
        ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)
        print(f"[V] Connecté avec succès à {config.SERIAL_PORT}")
        print(f"[*] URL de l'API : {config.API_URL}")
        
        while True:
            if ser.in_waiting > 0:
                # 1. Lire la ligne venant de l'USB
                # errors='replace' évite le crash si un caractère parasite arrive
                ligne = ser.readline().decode('utf-8', errors='replace').strip()
                
                if not ligne:
                    continue

                print(f"\n[DEBUG] Reçu brut : {ligne}")

                try:
                    # 2. Convertir le texte en objet JSON
                    data = json.loads(ligne)
                    endpoint = data.get('endpoint')
                    
                    if endpoint:
                        # 3. Envoyer vers l'API Docker
                        url = f"{config.API_URL}/{endpoint}"
                        
                        try:
                            # --- CORRECTION ICI : Ajout de l'authentification ---
                            headers = {
                                'Authorization': f"ApiKey {config.API_KEY}",
                                'Content-Type': 'application/json'
                            }
                            # ----------------------------------------------------
                            
                            reponse = requests.post(url, json=data, headers=headers, timeout=3)
                            
                            if reponse.status_code == 200 or reponse.status_code == 201:
                                print(f"[API] Succès : Envoyé vers /{endpoint} (Code {reponse.status_code})")
                            else:
                                print(f"[API] Erreur : L'API a répondu avec le code {reponse.status_code}")
                                print(f"      Détail : {reponse.text}")
                                
                        except requests.exceptions.ConnectionError:
                            print(f"[ERREUR API] Impossible de joindre {url}. Docker est-il lancé ?")
                        except Exception as e:
                            print(f"[ERREUR API] Erreur lors de l'envoi : {e}")
                            
                    else:
                        print("[IGNORE] Pas de champ 'endpoint' trouvé dans le JSON reçu.")
                    
                except json.JSONDecodeError:
                    print(f"[ERREUR JSON] Format reçu invalide (pas du JSON) : {ligne}")
            
            # Petite pause pour ne pas surcharger le processeur de l'ordinateur
            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"[ERREUR CRITIQUE] Impossible d'ouvrir le port {config.SERIAL_PORT} : {e}")
    except KeyboardInterrupt:
        print("\n[!] Arrêt manuel de la gateway.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[*] Port série fermé proprement.")

# Cette partie est indispensable pour lancer le script
if __name__ == "__main__":
    start_gateway()