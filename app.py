import os
import requests
import re
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CHAVES DO COFRE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# --- LISTA NEGRA (FRANQUIAS GIGANTES) ---
# Adicione ou remova nomes aqui se quiser bloquear outras marcas no futuro.
BLACKLIST = ["mcdonald", "burger king", "subway", "bob's", "bobs", "madero", "kfc", "giraffas", "outback", "habib"]

def normalize_name(name):
    # Limpa o nome para agrupar unidades da mesma rede (ex: tira " - Leme" do final)
    name = re.split(r'[-|,]', name)[0]
    return name.strip().lower()

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
    print(f"[SISTEMA MAC] {len(raw_leads)} alvos totais capturados. Iniciando Triagem 2.0...")

    # 1. TRIAGEM E AGRUPAMENTO
    grouped_leads = defaultdict(list)
    leads_descartados = 0

    for lead in raw_leads:
        name = lead.get('title', 'Sem Nome')
        
        # Filtro da Lista Negra (Destrói se for mega-franquia)
        if any(bad in name.lower() for bad in BLACKLIST):
            leads_descartados += 1
            continue
            
        norm_name = normalize_name(name)
        grouped_leads[norm_name].append(lead)

    # 2. MONTANDO O DOSSIÊ VISUAL ESTRATÉGICO
    redes_locais = {k: v for k, v in grouped_leads.items() if len(v) > 1}
    unidades_unicas = {k: v for k, v in grouped_leads.items() if len(v) == 1}

    html_content = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #000; border-bottom: 2px solid #004aad; padding-bottom: 5px;">Relatório de Expansão (Bullet Prospector 2.0)</h2>
        <p>Varredura concluída. Foram analisados <b>{len(raw_leads)} alvos</b> brutos.</p>
        <p>A inteligência artificial filtrou o ruído e descartou <b>{leads_descartados} operações de mega-franquias</b>.</p>
        <br>
    """

    # BLOCO 1: REDES LOCAIS (ALTO POTENCIAL)
    if redes_locais:
        html_content += f"""
        <div style="background-color: #ffebee; padding: 10px; border-left: 5px solid #d32f2f; margin-bottom: 20px;">
            <h3 style="color: #d32f2f; margin: 0;">🚨 REDES LOCAIS DETECTADAS (ALTO POTENCIAL)</h3>
            <p style="margin: 5px 0 0 0; font-size: 14px;">Operações já validadas com 2 ou mais unidades na mesma região.</p>
        </div>
        """
        for rede_name, unidades in redes_locais.items():
            nome_formatado = unidades[0].get('title').split('-')[0].split(',')[0].strip().upper()
            html_content += f"<h4 style='color: #000; margin-bottom: 5px;'>🏢 {nome_formatado} ({len(unidades)} Unidades)</h4>"
            for lead in unidades:
                phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone'))
                address = lead.get('address', 'Endereço não cadastrado')
                rating = lead.get('totalScore', 'N/A')
                website = lead.get('website', 'Sem site')
                html_content += f"""
                <div style="background-color: #fff; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; margin-left: 15px;">
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📍 Unidade:</strong> {address}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📞 Tel:</strong> {phone} | <strong>⭐ Nota:</strong> {rating}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>🌐 Site/Insta:</strong> <a href="{website}" style="color: #004aad;">{website}</a></p>
                </div>
                """
        html_content += "<hr style='border: 1px solid #eee; margin: 30px 0;'>"

    # BLOCO 2: UNIDADES INDIVIDUAIS
    html_content += f"""
    <h3 style="color: #004aad;">📍 Unidades Individuais Independentes</h3>
    <p style="font-size: 14px; margin-bottom: 15px;">Possíveis candidatos para conversão de bandeira ou expansão primária.</p>
    """
    for lead_list in unidades_unicas.values():
        lead = lead_list[0]
        name = lead.get('title', 'Sem nome')
        phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone'))
        address = lead.get('address', 'Endereço não cadastrado')
        rating = lead.get('totalScore', 'N/A')
        website = lead.get('website', 'Sem site')
        html_content += f"""
        <div style="background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; border-left: 4px solid #004aad;">
            <h4 style="margin-top: 0; margin-bottom: 5px; color: #000;">{name}</h4>
            <p style="margin: 2px 0; font-size: 14px;"><strong>📞 Tel:</strong> {phone} | <strong>📍 End:</strong> {address}</p>
            <p style="margin: 2px 0; font-size: 14px;"><strong>⭐ Nota:</strong> {rating} | <strong>🌐 Site:</strong> <a href="{website}">{website}</a></p>
        </div>
        """

    html_content += """
        <br>
        <p style="font-size: 11px; color: #777; border-top: 1px solid #ddd; padding-top: 10px;">
            Inteligência de Expansão | Bullet Prospector 2.0
        </p>
    </body>
    </html>
    """

    # 3. O BYPASS (Túnel Apify)
    try:
        apify_mail_url = f"https://api.apify.com/v2/acts/apify~send-mail/runs?token={APIFY_TOKEN}"
        mail_payload = {
            "to": EMAIL_RECEIVER,
            "subject": f"🔥 Dossiê 2.0: {len(redes_locais)} Redes + {len(unidades_unicas)} Individuais capturadas",
            "html": html_content
        }
        requests.post(apify_mail_url, json=mail_payload)
        print("[SISTEMA MAC] Dossiê 2.0 ejetado com sucesso!")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha no Bypass: {e}")
        return jsonify({"error": "Falha no envio"}), 500

    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
