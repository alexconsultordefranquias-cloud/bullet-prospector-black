import os
import requests
import smtplib
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# --- CHAVES DO COFRE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

@app.route('/webhook/apify', methods=['POST'])
def apify_webhook():
    data = request.json
    
    resource = data.get('resource', {})
    default_dataset_id = resource.get('defaultDatasetId')
    
    if not default_dataset_id:
        return jsonify({"error": "Dataset ID ausente"}), 400

    print(f"[SISTEMA MAC] Extraindo dados do Dataset: {default_dataset_id}")
    
    # 1. Sugando a lista do Apify
    url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_TOKEN}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print("[ERRO] Falha de comunicação com Apify.")
        return jsonify({"error": "Falha no Apify"}), 500

    leads = response.json()
    print(f"[SISTEMA MAC] {len(leads)} alvos confirmados. Montando Dossiê Tático...")

    # 2. Montando a estrutura visual do E-mail
    html_content = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #000; border-bottom: 2px solid #d32f2f; padding-bottom: 5px;">Relatório Tático de Caçada (Bullet Prospector)</h2>
        <p>A varredura foi concluída com sucesso. Aqui está o dossiê dos <b>{len(leads)} alvos</b> capturados:</p>
        <br>
    """

    for lead in leads:
        name = lead.get('title', 'Nome não identificado')
        phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone no mapa'))
        address = lead.get('address', 'Endereço não cadastrado')
        rating = lead.get('totalScore', 'N/A')
        reviews = lead.get('reviewsCount', 0)
        website = lead.get('website', 'Sem site')
        
        html_content += f"""
        <div style="background-color: #f9f9f9; padding: 15px; margin-bottom: 15px; border-left: 4px solid #d32f2f;">
            <h3 style="margin-top: 0; color: #000;">{name}</h3>
            <p style="margin: 5px 0;"><strong>📞 Telefone:</strong> {phone}</p>
            <p style="margin: 5px 0;"><strong>📍 Endereço:</strong> {address}</p>
            <p style="margin: 5px 0;"><strong>⭐ Nota do Local:</strong> {rating} ({reviews} avaliações)</p>
            <p style="margin: 5px 0;"><strong>🌐 Site:</strong> <a href="{website}" style="color: #004aad;">{website}</a></p>
        </div>
        """

    html_content += """
        <br>
        <p style="font-size: 11px; color: #777; border-top: 1px solid #ddd; padding-top: 10px;">
            Gerado automaticamente por Mac - Engenharia de Escala.
        </p>
    </body>
    </html>
    """

    # 3. Disparando o E-mail via SMTP do Gmail
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"🎯 Dossiê de Prospecção: {len(leads)} alvos capturados"
        
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("[SISTEMA MAC] Dossiê ejetado com sucesso para a base (E-mail)!")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao enviar dossiê: {e}")
        return jsonify({"error": "Falha no disparo do e-mail"}), 500

    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
