import sys
import requests
import json
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QTimer, pyqtSlot, QObject, Qt

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Crypto Chart</title>
  <style>
    body { margin: 0; padding: 0; background: #fafafa; font-family: sans-serif; }
    #chart-container { 
      width: 95%; max-width: 900px; margin: 20px auto; 
      background: #fff; border: 1px solid #ccc; padding: 10px; 
      box-shadow: 0 3px 6px rgba(0,0,0,0.1); 
      position: relative; 
      height: 500px; 
    }
    h2 { text-align: center; margin: 10px 0; }
    #loading { 
      display: none; 
      position: absolute; 
      top: 50%; 
      left: 50%; 
      transform: translate(-50%, -50%); 
      font-size: 24px; 
      color: #555; 
      text-align: center; 
    }
    #myChart { display: none; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
  <div id="chart-container">
    <h2 id="chart-title">Crypto Chart</h2>
    <div id="loading">Loading...</div>
    <canvas id="myChart"></canvas>
  </div>

  <script>
    let myChart = null;

    function showLoading() {
      document.getElementById('loading').style.display = 'block';
      document.getElementById('myChart').style.display = 'none';
      if (myChart) {
        myChart.destroy();
        myChart = null;
      }
    }

    function hideLoading() {
      document.getElementById('loading').style.display = 'none';
      document.getElementById('myChart').style.display = 'block';
    }

    function updateChart(dates, prices, cryptoName) {
      const ctx = document.getElementById('myChart').getContext('2d');
      document.getElementById('chart-title').innerText = 
        "Price Evolution of " + cryptoName + " (Real Time)";

      hideLoading();

      if (myChart) {
        myChart.data.labels = dates;
        myChart.data.datasets[0].data = prices;
        myChart.data.datasets[0].label = cryptoName;
        myChart.update();
      } else {
        myChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: dates,
            datasets: [{
              label: cryptoName,
              data: prices,
              fill: false,
              borderColor: 'rgba(75, 192, 192, 1)',
              tension: 0.1
            }]
          },
          options: {
            responsive: true,
            scales: {
              x: { display: true, title: { display: true, text: 'Date' } },
              y: { display: true, title: { display: true, text: 'Price (USD)' } }
            }
          }
        });
      }
    }

    let bridgeReady = false;
    new QWebChannel(qt.webChannelTransport, function(channel) {
      window.bridge = channel.objects.bridge;
      bridgeReady = true;
      console.log("Bridge initialized.");
    });

    function setChartData(dates, prices, cryptoName) {
      if (bridgeReady && window.bridge) {
        updateChart(dates, prices, cryptoName);
      } else {
        console.error("Bridge not ready yet.");
      }
    }

    showLoading();
  </script>
</body>
</html>
"""

class Bridge(QObject):
    pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crypto Money")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        label = QLabel("Select your crypto:", self)
        top_layout.addWidget(label)

        self.combo_crypto = QComboBox(self)
        self.combo_crypto.addItems(["bitcoin", "ethereum", "binancecoin", "cardano"])
        self.combo_crypto.currentTextChanged.connect(self.start_updates)
        top_layout.addWidget(self.combo_crypto)

        self.btn_start = QPushButton("Start", self)
        self.btn_start.clicked.connect(self.start_updates)
        top_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop", self)
        self.btn_stop.clicked.connect(self.stop_updates)
        top_layout.addWidget(self.btn_stop)

        self.web_view = QWebEngineView(self)
        main_layout.addWidget(self.web_view, stretch=1)

        self.channel = QWebChannel(self.web_view.page())
        self.bridge = Bridge()
        self.channel.registerObject('bridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.web_view.setHtml(HTML_PAGE)
        self.web_view.loadFinished.connect(self.on_load_finished)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_and_display_data)
        self.update_interval = 30000

    def on_load_finished(self, ok):
        if ok:
            print("[INFO] HTML page loaded.")
        else:
            print("[ERROR] Failed to load HTML page.")

    def start_updates(self):
        crypto_name = self.combo_crypto.currentText()
        print(f"[INFO] Starting updates for {crypto_name}...")
        self.web_view.page().runJavaScript("showLoading();")
        self.timer.start(self.update_interval)

    def stop_updates(self):
        print("[INFO] Stopping updates.")
        self.timer.stop()
        self.web_view.page().runJavaScript("showLoading();")

    def load_and_display_data(self):
        crypto_name = self.combo_crypto.currentText()
        print(f"[INFO] Updating data for {crypto_name}...")

        url = f"https://api.coingecko.com/api/v3/coins/{crypto_name}/market_chart?vs_currency=usd&days=1"

        try:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()

            if "prices" not in data:
                print(f"[ERROR] Key 'prices' missing in response: {data}")
                return

            prices_list = data["prices"]
            dates = []
            prices = []
            for elem in prices_list[-10:]:
                ts = elem[0]
                price_val = elem[1]
                dt_str = datetime.datetime.utcfromtimestamp(ts / 1000).strftime("%H:%M:%S")
                dates.append(dt_str)
                prices.append(price_val)

            script = f"setChartData({json.dumps(dates)}, {json.dumps(prices)}, '{crypto_name}');"
            self.web_view.page().runJavaScript(script)

        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] HTTP Error: {e}")
            self.web_view.page().runJavaScript("showLoading();")
        except Exception as e:
            print(f"[ERROR] {e}")
            self.web_view.page().runJavaScript("showLoading();")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
