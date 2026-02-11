# Projet_course_orientation_150h
Ce projet est le projet final réalisé pour les STABS afin que le superviseur gère les scénarios de courses avec des balises sur un logiciel Windows programmé en python



# Cahier des charges technique

## Projet : Course d’Orientation Connectée
Responsable de la partie logicielle : Tom Le Beuze Date : 26 janvier 2026

## Présentation du projet 

### 1.1 Contexte :

Le département STAPS de l’Université Champollion souhaite automatiser la gestion des courses d'orientation. Le projet vise à remplacer le pointage manuel par une solution numérique temps réel utilisant la technologie LoRa pour garantir une couverture totale, même en zone blanche (forêt).

### 1.2 Inventaire des outils et matériels nécessaires : 

Matériel sur le Terrain : Smartphones Android avec une puce NFC (pour chaques équipes) + Balises LILYGO TTGO (ESP32, LoRa, GPS, RFID) faisant office de modem LoRa via Bluetooth.

Matériel de Réception : Passerelle LoRa/USB connectée au PC de supervision.

Environnement de développement : Python 3, Framework mobile (Android ou Web App), Visual Studio Code, Git/GitHub, SQLite.

Système d'exploitation cible : Windows 10/11 (PC de course).

Analyse du fonctionnement du système

### 2.1 Fonctionnement Radio et Connectivité ("Smartphone + LoRa")
Le système utilise une architecture hybride pour s'affranchir de la dépendance au réseau 4G 
Pointage : Le coureur utilise le NFC du smartphone pour scanner le tag de la balise.
Liaison locale : Le smartphone transmet l'information en Bluetooth au module LILYGO porté par l'équipe.
Liaison longue portée : Le module LILYGO envoie la trame de validation en LoRa vers le PC de course.
Format de la trame des données : Les échanges seront structurés sous formes de trames en CSV qui sont compactes pour minimiser le temps d’occupation du canal LoRa. Voici un exemple : [ID_Equipe;ID_Balise;Timestamp;Batterie]. 
Un mécanisme d'Accusé de Réception sera mis en place entre le PC et le mobile pour garantir la délivrance du message.
### 2.2 Localisation et Cartographie en temps réel
Côté Coureur : L'application Android affiche une carte (OpenStreetMap) avec la position de l'équipe grâce au GPS du téléphone. Pour fonctionner en forêt, les tuiles de la carte sont pré-chargées (mode hors-ligne).
Côté Organisateur : Le logiciel PC centralise les positions de toutes les équipes reçues par LoRa et les projette sur une interface globale.
### 2.3 Scénarios de course
Mode linéaire : Validation des balises dans un ordre imposé parle créateur de la course.
Mode Score : Ordre libre, chaque balise rapporte un nombre de points défini.
### 2.4 Gestion de l’Énergie (Batterie)
L'application et le logiciel PC extraient le niveau de batterie des modules LILYGO et des balises pour afficher une alerte si l'autonomie descend en dessous de 20%.
### 2.5 Gestion des Cas Dégradés
En cas de rupture de la liaison LoRa (la zone qui est trop dense), le smartphone stockera les données de pointage dans une base SQLite locale. Dès que le signal est rétabli ou que le coureur arrive à portée du PC, une synchronisation automatique renverra les données manquantes.

Besoins Réseaux et Cybersécurité
Intégrité : Ajout d'un Checksum (CRC) sur les trames LoRa pour éviter la corruption des scores.
Confidentialité : Accès à l'interface organisateur protégé par mot de passe.
Traçabilité : Envoi des logs d'événements (connexions, validations, erreurs) vers le serveur d'analyse Wazuh du groupe.
Nature des logs envoyé a wazuh : Le logiciel agira comme un agent de sécurité : il remontera vers Wazuh toute anomalie réseau (perte de paquet excessive) ou tentative de connexion non autorisée sur l'application mobile.

### Liste des tâches
#### PHASE 1 : ANALYSE & CONCEPTION LOGICIELLE (Semaines 1 & 2)
Semaine 1- J1 à J3 : Étude des protocoles de communication série. Analyse du format des trames reçues de la passerelle LoRa.
Semaine 1- J4 à J5 : Choix et installation de l'environnement (Python, PyQt6, PySerial). Étude de la bibliothèque tkintermapview pour la cartographie.
Semaine 2- J1 à J3 : Modélisation UML spécifique au logiciel PC :
Diagramme de Classes (Gestion des coureurs, des balises et des alertes).
Diagramme d'États (États de la course : En attente, En cours, Terminé).
Semaine 2 - J4 à J5 : Définition de l'interface utilisateur (Mockup/Maquettes IHM) pour le tableau de bord de l'organisateur.
revue de projet 1 le 9 février
#### PHASE 2 : ACQUISITION RADIO & TRAITEMENT (Semaines 3 à 5)
Semaine 3-J1 à J5 : Développement du module de communication série (PySerial). Lecture du flux de données provenant de la passerelle USB/LoRa.
Semaine 4-J1 à J5 : Algorithme de décodage (Parsing) : Transformation des trames CSV reçues en objets Python exploitables.
Semaine 5-J1 à J5 : Logique de gestion de course (Côté PC) :
Vérification du passage aux balises (Mode Linéaire).
Calcul des points en temps réel (Mode Score).
Déclenchement des alertes (Inactivité prolongée, batterie basse).
#### PHASE 3 : IHM & CARTOGRAPHIE (Semaines 6 à 8)
Semaine 6-J1 à J5 : Développement de l'IHM avec PyQt6 : Tableau de bord principal avec liste des participants et chronomètres.
Semaine 7-J1 à J5 : Intégration de la carte :
Affichage de la carte et placement des balises (coordonnées GPS).
Mise à jour dynamique de la position des coureurs sur la carte.
Semaine 8-J1 à S9-J2 : Gestion du mode hors-ligne : Script de mise en cache (téléchargement) des tuiles de la carte pour une utilisation en forêt sans internet.
revue de projet 2 le 31 mars
#### PHASE 4 : CYBERSÉCURITÉ & INTÉGRATION SIEM (Semaine 9 & 10)
Semaine 9-J3 à J5 : Sécurisation logicielle :
Implémentation du calcul de Checksum/CRC pour vérifier que les trames radio n'ont pas été corrompues.
Audit de sécurité des bibliothèques tierces utilisées.
Semaine 10-J1 à J5 : Exportation des logs et métriques (Projet de groupe) :
Génération de fichiers de logs au format JSON.
Configuration du transfert des logs de sécurité vers le serveur Wazuh (géré par l'étudiant 1).
#### PHASE 5 : VALIDATION & LIVRABLES (Semaines 11 & 12)
- Semaine 11-J1 à J3 : Tests de charge : Simulation de réception massive de trames pour tester la stabilité de l'IHM.
- Semaine 11-J4 à J5 : Recette technique : Test de portée et de réception en conditions réelles (forêt).
- Semaine 12-J1 à J3 : Rédaction de la documentation technique et du Manuel Utilisateur (destiné à l'organisateur de la course).
- Semaine 12-J4 à J5 : Packaging final : Création de l'exécutable .exe de l'application (avec PyInstaller).

## 5. Validation et Livrables
- Livrable 1 : Logiciel de supervision Windows (.exe) pour l'organisateur.
- Livrable 2 : Dépôt GitHub avec le code source et la documentation technique.
- Livrable 3 : Manuel utilisateur "Coureur" et "Organisateur".
- revue de projet 3 le 19 mai

