import serial
import json
import re
import os
from datetime import datetime

# --- CONFIGURATION ---
PORT_SERIE = 'COM3'  # Vérifie que c'est bien ton port
BAUD_RATE = 115200
FICHIER_JSON = r'transfer\donnees_rfid.json'

def parse_lora_to_dict(ligne_brute):
    """Extrait les données et retourne un dictionnaire Python"""
    match = re.search(r"Message reçu du node (\d+)\s*:\s*(.*)", ligne_brute)
    
    if match:
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "node_id": int(match.group(1)),
            "rfid_tag": match.group(2).strip().upper() # .upper() pour mettre en majuscules (FA 48...)
        }
    return None

def sauvegarder_json(nouvelle_donnee):
    """Ajoute la nouvelle donnée dans le fichier JSON"""
    donnees_existantes = []
    
    # On lit le fichier s'il existe déjà pour ne pas écraser l'historique
    if os.path.exists(FICHIER_JSON):
        try:
            with open(FICHIER_JSON, 'r', encoding='utf-8') as f:
                donnees_existantes = json.load(f)
        except json.JSONDecodeError:
            pass # Si le fichier est vide ou corrompu, on repart de zéro

    # On ajoute la nouvelle lecture à la liste
    donnees_existantes.append(nouvelle_donnee)
    
    # On sauvegarde tout dans le fichier
    with open(FICHIER_JSON, 'w', encoding='utf-8') as f:
        json.dump(donnees_existantes, f, indent=4, ensure_ascii=False)
    
    print(f"-> Donnée sauvegardée dans {FICHIER_JSON}")

def main():
    try:
        ser = serial.Serial(PORT_SERIE, BAUD_RATE, timeout=1)
        print(f"Écoute sur {PORT_SERIE} à {BAUD_RATE} bauds...")
        print("En attente de badges RFID...\n")
        
        while True:
            if ser.in_waiting > 0:
                ligne = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if ligne:
                    donnees_dict = parse_lora_to_dict(ligne)
                    
                    if donnees_dict:
                        print(f"\nBadge détecté ! Node: {donnees_dict['node_id']} | Tag: {donnees_dict['rfid_tag']}")
                        sauvegarder_json(donnees_dict)
                    else:
                        print(f"Info système ESP32 : {ligne}")

    except serial.SerialException:
        print(f"Erreur : Impossible d'ouvrir le port {PORT_SERIE}. Ferme le moniteur série Arduino !")
    except KeyboardInterrupt:
        print("\nArrêt du script.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    main()