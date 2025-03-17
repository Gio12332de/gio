from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ API de scraping AVEC JavaScript rendering prête. Utilise /scrape?url=..."

@app.route("/scrape")
def scrape():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "❌ Paramètre 'url' manquant."}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)  # 30 secondes max

            # Attente du chargement complet du contenu JS
            page.wait_for_load_state("networkidle")

            # Récupération du texte visible après JS
            content = page.content()
            text = page.inner_text("body")  # Texte brut visible dans <body>
            browser.close()

            return jsonify({
                "url": url,
                "scraping_result": text[:5000]  # limite de 5000 caractères
            })

    except Exception as e:
        return jsonify({"error": f"❌ Erreur scraping JS : {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
