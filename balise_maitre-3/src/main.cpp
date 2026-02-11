#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <XPowersLib.h> // Assure-toi d'avoir la lib dans platformio.ini

// --- PINS T-BEAM V1.2 ---
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 23
#define DIO0 26

// Fréquence Europe (868 MHz)
#define BAND 868E6

// CORRECTION 1 : On utilise la classe spécifique
XPowersAXP2101 PMU;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("--- DEMARRAGE RECEPTEUR ---");

  // 1. ALLUMAGE ELECTRIQUE
  Wire.begin(21, 22);
  if (!PMU.begin(Wire, AXP2101_SLAVE_ADDRESS, 21, 22)) {
    Serial.println("ERREUR: AXP2101 introuvable");
  } else {
    // CORRECTION 2 : Fonctions spécifiques ALDO2
    PMU.setALDO2Voltage(3300);
    PMU.enableALDO2();
    Serial.println("Alimentation LoRa OK");
  }

  // 2. CONFIGURATION LORA
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(BAND)) {
    Serial.println("ECHEC demarrage LoRa !");
    while (1);
  }
  Serial.println("En attente de paquets...");
}

void loop() {
  // Vérifie si un paquet est arrivé
  int packetSize = LoRa.parsePacket();
  
  if (packetSize) {
    String receivedData = "";
    
    // Lecture du paquet complet
    while (LoRa.available()) {
      receivedData += (char)LoRa.read();
    }

    // CORRECTION 3 : IMPORTANT POUR PYTHON
    // On n'envoie QUE les données brutes (le JSON).
    // Pas de "Recu:", pas de "RSSI", sinon Python plante.
    Serial.println(receivedData);
  }
}