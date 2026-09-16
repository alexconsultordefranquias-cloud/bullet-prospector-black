import os
import requests
import re
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CHAVES DO COFRE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
BLACKLIST = ["mcdonald", "burger king", "subway", "bob's", "bobs", "madero", "kfc", "giraffas", "outback", "habib"]

def normalize_name(name):
    name = re.split(r'[-|,]', name)[0]
    return name.strip().lower()

# --- ARMA 1: GERADOR DE LINK WHATSAPP ---
def gerar_link_whatsapp(phone_str):
    if not phone_str or phone_str == 'Sem telefone' or phone_str == 'Sem telefone no mapa':
        return None
    # Extrai apenas os números
    numeros = re.sub(r'\D', '', phone_str)
    if len(numeros) >= 10:
        # Adiciona o código do Brasil se não existir
        if not numeros.startswith('55'):
            numeros = f"55{numeros}"
        return f"https://wa.me/{numeros}"
    return None

# --- ARMA 2 (ESTRUTURA): BUSCADOR DE SÓCIOS DA RECEITA FEDERAL ---
def buscar_decisor(nome_empresa):
    """
    COMPARTIMENTO BLINDADO: A requisição HTTP para a API de CNPJ será injetada aqui.
    O compartimento já está estruturado para isolar falhas e não estourar o Timeout do Render.
    """
    # A integração da API real de CNPJ entrará no próximo passo tático.
    return "🕵️‍♂️ [Radar de Sócios Preparado para Integração]"

@app.route('/webhook/apify', methods=['POST'])
def apify_webhook():
    data = request.json
    resource = data.get('resource', {})
    default_dataset_id = resource.get('defaultDatasetId')
    
    if not default_dataset_id:
        return jsonify({"error": "Dataset ID ausente"}), 400

    print(f"[SISTEMA MAC] Extraindo dados do Dataset: {default_dataset_id}")
    
    url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_TOKEN}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return jsonify({"error": "Falha no Apify"}), 500

    raw_leads = response.json()
    print(f"[SISTEMA MAC] {len(raw_leads)} alvos processados. Aplicando enriquecimento...")

    grouped_leads = defaultdict(list)
    leads_descartados = 0

    for lead in raw_leads:
        name = lead.get('title', 'Sem Nome')
        if any(bad in name.lower() for bad in BLACKLIST):
            leads_descartados += 1
            continue
        norm_name = normalize_name(name)
        grouped_leads[norm_name].append(lead)

    redes_locais = {k: v for k, v in grouped_leads.items() if len(v) > 1}
    unidades_unicas = {k: v for k, v in grouped_leads.items() if len(v) == 1}

    html_content = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #000; border-bottom: 2px solid #004aad; padding-bottom: 5px;">Relatório de Expansão (Bullet Prospector 2.5)</h2>
        <p>A inteligência artificial filtrou <b>{leads_descartados} operações de mega-franquias</b> e enriqueceu os contatos.</p>
        <br>
    """

    # BLOCO 1: REDES LOCAIS (ALTO POTENCIAL)
    if redes_locais:
        html_content += """
        <div style="background-color: #ffebee; padding: 10px; border-left: 5px solid #d32f2f; margin-bottom: 20px;">
            <h3 style="color: #d32f2f; margin: 0;">🚨 REDES LOCAIS DETECTADAS (ALTO POTENCIAL)</h3>
        </div>
        """
        for rede_name, unidades in redes_locais.items():
            nome_formatado = unidades[0].get('title').split('-')[0].split(',')[0].strip().upper()
            html_content += f"<h4 style='color: #000; margin-bottom: 5px;'>🏢 {nome_formatado} ({len(unidades)} Unidades)</h4>"
            
            # Chamando a função de Sócio/Decisor
            decisor = buscar_decisor(nome_formatado)
            html_content += f"<p style='margin: 0 0 10px 15px; font-size: 13px; color: #555;'>{decisor}</p>"

            for lead in unidades:
                phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone'))
                address = lead.get('address', 'Endereço não cadastrado')
                rating = lead.get('totalScore', 'N/A')
                website = lead.get('website', 'Sem site')
                
                # Gerador Visual do Botão de WhatsApp
                wpp_link = gerar_link_whatsapp(phone)
                wpp_btn = f"<a href='{wpp_link}' style='background-color: #25D366; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 10px;'>💬 Chamar no Whats</a>" if wpp_link else ""

                html_content += f"""
                <div style="background-color: #fff; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; margin-left: 15px;">
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📍 Unidade:</strong> {address}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📞 Tel:</strong> {phone} {wpp_btn}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>⭐ Nota:</strong> {rating} | <strong>🌐 Site:</strong> <a href="{website}">{website}</a></p>
                </div>
                """
        html_content += "<hr style='border: 1px solid #eee; margin: 30px 0;'>"

    # BLOCO 2: UNIDADES INDIVIDUAIS
    html_content += """
    <h3 style="color: #004aad;">📍 Unidades Individuais Independentes</h3>
    """
    for lead_list in unidades_unicas.values():
        lead = lead_list[0]
        name = lead.get('title', 'Sem nome')
        phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone'))
        address = lead.get('address', 'Endereço não cadastrado')
        rating = lead.get('totalScore', 'N/A')
        website = lead.get('website', 'Sem site')
        
        wpp_link = gerar_link_whatsapp(phone)
        wpp_btn = f"<a href='{wpp_link}' style='background-color: #25D366; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 10px;'>💬 Chamar</a>" if wpp_link else ""

        html_content += f"""
        <div style="background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; border-left: 4px solid #004aad;">
            <h4 style="margin-top: 0; margin-bottom: 5px; color: #000;">{name}</h4>
            <p style="margin: 2px 0; font-size: 14px;"><strong>📞 Tel:</strong> {phone} {wpp_btn}</p>
            <p style="margin: 2px 0; font-size: 14px;"><strong>📍 End:</strong> {address}</p>
            <p style="margin: 2px 0; font-size: 14px;"><strong>⭐ Nota:</strong> {rating} | <strong>🌐 Site:</strong> <a href="{website}">{website}</a></p>
        </div>
        """

    html_content += """
        <br>
        <p style="font-size: 11px; color: #777; border-top: 1px solid #ddd; padding-top: 10px;">
            Inteligência de Expansão | Bullet Prospector
        </p>
    </body>
    </html>
    """

    try:
        apify_mail_url = f"https://api.apify.com/v2/acts/apify~send-mail/runs?token={APIFY_TOKEN}"
        mail_payload = {
            "to": EMAIL_RECEIVER,
            "subject": f"🔥 Dossiê 2.5 (Enriquecido): {len(redes_locais)} Redes + {len(unidades_unicas)} Individuais",
            "html": html_content
        }
        requests.post(apify_mail_url, json=mail_payload)
        print("[SISTEMA MAC] Dossiê 2.5 ejetado com sucesso!")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha no Bypass: {e}")
        return jsonify({"error": "Falha no envio"}), 500

    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
