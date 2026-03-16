import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # HTML de base pour Leaflet (OpenStreetMap)
        # On crée une carte centrée sur la France par défaut
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

                // Fonction appelée par Python
                function updateMarker(lat, lon, id) {
                    // Si le marqueur existe déjà, on le bouge
                    if (markers[id]) {
                        markers[id].setLatLng([lat, lon]);
                        markers[id].bindPopup(id).openPopup();
                    } else {
                        // Sinon on le crée
                        var newMarker = L.marker([lat, lon]).addTo(map);
                        newMarker.bindPopup(id).openPopup();
                        markers[id] = newMarker;
                    }
                    // Centrer la carte sur le dernier point
                    map.panTo([lat, lon]);
                }
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(self.html_content)

    def update_position(self, lat, lon, text="Cible"):
        """Appelle la fonction Javascript définie dans le HTML ci-dessus"""
        # On injecte l'appel JS
        js_code = f"updateMarker({lat}, {lon}, '{text}');"
        self.web_view.page().runJavaScript(js_code)