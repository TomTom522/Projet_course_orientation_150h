import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # Système pour empêcher le crash de la carte 
        self.page_loaded = False
        self.js_queue = []
        self.web_view.loadFinished.connect(self.on_load_finished)

        # HTML de base pour Leaflet (OpenStreetMap)
        self.html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <style> body { margin: 0; padding: 0; } #map { width: 100%; height: 100vh; } </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                // Initialisation de la carte
                var map = L.map('map').setView([44.35, 2.57], 10);

                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                }).addTo(map);

                var markers = {};
                var balisesMap = {}; 

                function updateMarker(lat, lon, id) {
                    if (markers[id]) {
                        markers[id].setLatLng([lat, lon]);
                        markers[id].bindPopup(id).openPopup();
                    } else {
                        var newMarker = L.marker([lat, lon]).addTo(map);
                        newMarker.bindPopup(id).openPopup();
                        markers[id] = newMarker;
                    }
                    map.panTo([lat, lon]);
                }

                function drawBalise(lat, lon, id, nom) {
                    if (balisesMap[id]) {
                        balisesMap[id].setLatLng([lat, lon]);
                        balisesMap[id].bindPopup("<b>" + nom + "</b><br>ID LoRa: " + id);
                    } else {
                        // Icône rouge spéciale pour les balises
                        var baliseIcon = L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        });

                        var m = L.marker([lat, lon], {icon: baliseIcon}).addTo(map);
                        m.bindPopup("<b>" + nom + "</b><br>ID LoRa: " + id);
                        balisesMap[id] = m;
                    }
                }
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(self.html_content)

    def on_load_finished(self, ok):
        """Déclenché quand la carte a fini de charger son code HTML"""
        self.page_loaded = True
        # exécute tout ce qui était en attente
        for js in self.js_queue:
            self.web_view.page().runJavaScript(js)
        self.js_queue.clear()

    def run_js_safe(self, js_code):
        """Met en file d'attente le JS si la page n'est pas encore prête"""
        if self.page_loaded:
            self.web_view.page().runJavaScript(js_code)
        else:
            self.js_queue.append(js_code)

    def update_position(self, lat, lon, text="Cible"):
        js_code = f"updateMarker({lat}, {lon}, '{text}');"
        self.run_js_safe(js_code)

    def afficher_balises(self, balises):
        for b in balises:
            try:
                
                lat = float(b.get("latitude", 0))
                lon = float(b.get("longitude", 0))
                
                # Si la balise est à 0,0 , on l'ignore
                if lat == 0.0 and lon == 0.0:
                    continue

                nom = str(b.get("nom_balise", "Balise")).replace("'", "\\\"")
                lora_id = str(b.get("lora_id", b.get("id", "?"))).replace("'", "\\\"")

                js_code = f"drawBalise({lat}, {lon}, '{lora_id}', '{nom}');"
                self.run_js_safe(js_code)
            except Exception as e:
                print(f"Balise ignorée suite à une erreur: {e}")