#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <XPowersLib.h> 
#include <ArduinoJson.h>

// --- PINS T-BEAM V1.2 ---
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 23
#define DIO0 26

// Fréquence Europe (868 MHz)
#define BAND 868E6

// On instancie la classe spécifique pour l'AXP2101
XPowersAXP2101 PMU;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("--- DEMARRAGE ENVOYEUR ---");

  // 1. ALLUMAGE ELECTRIQUE (AXP2101)
  Wire.begin(21, 22);
  
  if (!PMU.begin(Wire, AXP2101_SLAVE_ADDRESS, 21, 22)) {
    Serial.println("ERREUR: AXP2101 introuvable !");
  } else {
    // --- CORRECTION ICI ---
    // On utilise les fonctions spécifiques ALDO2 (LoRa)
    // Au lieu des fonctions génériques protégées
    
    PMU.setALDO2Voltage(3300); // Règle le voltage à 3.3V
    PMU.enableALDO2();         // Active le canal ALDO2
    
    Serial.println("Alimentation LoRa (ALDO2) activee.");
  }

  // 2. CONFIGURATION LORA
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(BAND)) {
    Serial.println("ECHEC demarrage LoRa !");
    while (1);
  }
  Serial.println("LoRa Initialise OK !");
}

void loop() {
  // Création du paquet de données
  StaticJsonDocument<200> doc;
  doc["id_equipe"] = 10;
  doc["type"] = "balise";
  doc["valeur"] = random(0, 100); 
  doc["timestamp"] = millis();

  String jsonString;
  serializeJson(doc, jsonString);

  // Envoi LoRa
  Serial.print("Envoi du paquet : ");
  Serial.println(jsonString);

  LoRa.beginPacket();
  LoRa.print(jsonString);
  LoRa.endPacket();

  delay(5000); 
}