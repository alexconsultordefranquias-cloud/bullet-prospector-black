import os
import requests
import re
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CHAVES DO COFRE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# --- A GRANDE MURALHA (BLACKLIST MULTI-SETORIAL) ---
BLACKLIST = [
    # Alimentação e Fast Food
    "mcdonald", "burger king", "subway", "bob's", "bobs", "madero", "kfc", "giraffas", "outback", "habib",
    "cacau show", "china in box", "spoleto", "dominos", "domino's", "pizza hut", "coco bambu", "jerônimo", "jeronimo",
    
    # Educação
    "microlins", "kumon", "wizard", "fisk", "ccaa", "yázigi", "yazigi", "cna", "minds", "influx", 
    "senai", "senac", "sesi", "fatec", "etec", "grau técnico", "grau tecnico", "cebrac", "embelleze",
    "prepara", "faculdade", "universidade", "unip", "estácio", "estacio", "anhanguera", "mackenzie", "myrobot",
    
    # Estética, Beleza e Academias
    "smart fit", "smartfit", "skyfit", "bluefit", "panobianco", "pratique", "selfit", "gavioes", "gaviões",
    "espaço laser", "espaçolaser", "laser fast", "emagrecentro", "giorgio", "sobrancelhas design", "giolaser", "onodera",
    
    # Perfumaria
    "boticário", "boticario", "natura", "avon", "quem disse", "água de cheiro", "agua de cheiro", "l'occitane", "loccitane",
    
    # Sorveterias
    "chiquinho", "bacio di latte", "oggi", "sr sorvete", "los paleteros", "ice cream roll",
    
    # Lavanderias
    "5asec", "5àsec", "lavateria", "dryclean usa", "prima clean", "quality lavanderia",
    
    # Tintas
    "coral", "suvinil", "decor colors", "tintas mc", "lukscolor",
    
    # Pet Shop
    "petz", "cobasi", "petland", "zee.dog", "zeedog",
    
    # Energia
    "hcc energia", "portal solar", "blue sol", "solar prime",
    
    # Automotivos, Barbearia e Serviços Gerais
    "bosch", "localiza", "unidas", "movida", "mercadocar", "dpk", "porto seguro", "getninjas", "corleone", "seu elias"
]

# --- LISTA NEGRA 2: FILTRO SEMÂNTICO (CONCEITOS) ---
TERMOS_FRANQUIA = ["franquia", "franchising", "franqueado", "seja um franqueado"]

def normalize_name(name):
    name = re.split(r'[-|,]', name)[0]
    return name.strip().lower()

def gerar_link_whatsapp(phone_str):
    if not phone_str or phone_str == 'Sem telefone' or phone_str == 'Sem telefone no mapa':
        return None
    numeros = re.sub(r'\D', '', phone_str)
    if len(numeros) >= 10:
        if not numeros.startswith('55'):
            numeros = f"55{numeros}"
        return f"https://wa.me/{numeros}"
    return None

def buscar_decisor(nome_empresa):
    termo_busca = nome_empresa.replace(' ', '+')
    url_busca = f"https://minhareceita.org/{termo_busca}"
    try:
        resposta = requests.get(url_busca, timeout=3)
        if resposta.status_code == 200:
            dados = resposta.json()
            if isinstance(dados, list) and len(dados) > 0:
                qsa = dados[0].get('qsa', [])
                if qsa:
                    nomes_socios = [socio.get('nome_socio', '').title() for socio in qsa]
                    return f"🕵️‍♂️ Sócios (Receita): {', '.join(nomes_socios)}"
            return "🕵️‍♂️ Sócios: Dados não abertos no portal público."
        else:
            return "🕵️‍♂️ Sócios: Requer chave de API premium para busca avançada."
    except requests.exceptions.Timeout:
        return "🕵️‍♂️ Sócios: Base da Receita lenta. Busca abortada para salvar o Dossiê."
    except Exception as e:
        return "🕵️‍♂️ Sócios: Falha no radar de CNPJ."

@app.route('/webhook/apify', methods=['POST'])
def apify_webhook():
    data = request.json
    resource = data.get('resource', {})
    default_dataset_id = resource.get('defaultDatasetId')
    
    if not default_dataset_id:
        return jsonify({"error": "Dataset ID ausente"}), 400

    url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_TOKEN}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return jsonify({"error": "Falha no Apify"}), 500

    raw_leads = response.json()
    grouped_leads = defaultdict(list)
    leads_descartados = 0

    for lead in raw_leads:
        name = lead.get('title', 'Sem Nome')
        description = lead.get('description', '') or ''
        
        # FILTRO 1: Destrói se o NOME estiver na Blacklist
        if any(bad in name.lower() for bad in BLACKLIST):
            leads_descartados += 1
            continue
            
        # FILTRO 2: Destrói se a DESCRIÇÃO ou NOME contiver indícios de ser franquia
        texto_analise = (name + " " + description).lower()
        if any(termo in texto_analise for termo in TERMOS_FRANQUIA):
            leads_descartados += 1
            continue

        norm_name = normalize_name(name)
        grouped_leads[norm_name].append(lead)

    # ISOLAMENTO DE DIAMANTES: Ignora completamente as unidades únicas
    redes_locais = {k: v for k, v in grouped_leads.items() if 1 < len(v) <= 4}

    if not redes_locais:
         return jsonify({"status": "Nenhum diamante encontrado nesta varredura."}), 200

    html_content = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #000; border-bottom: 2px solid #000; padding-bottom: 5px;">Relatório Black (Foco Exclusivo)</h2>
        <p>Varredura hiperfocada. <b>{leads_descartados} leads sujos (franquias e ruídos) incinerados.</b></p>
        <p>Abaixo, apenas as operações que possuem entre 2 e 4 unidades:</p>
        <br>
    """

    if redes_locais:
        html_content += """
        <div style="background-color: #000; padding: 10px; border-left: 5px solid #d4af37; margin-bottom: 20px;">
            <h3 style="color: #d4af37; margin: 0;">💎 DIAMANTES DETECTADOS</h3>
        </div>
        """
        for rede_name, unidades in redes_locais.items():
            nome_formatado = unidades[0].get('title').split('-')[0].split(',')[0].strip().upper()
            html_content += f"<h4 style='color: #000; margin-bottom: 5px;'>🏢 {nome_formatado} ({len(unidades)} Unidades)</h4>"
            
            decisor = buscar_decisor(nome_formatado)
            html_content += f"<p style='margin: 0 0 10px 15px; font-size: 13px; color: #8b0000; font-weight: bold;'>{decisor}</p>"

            for lead in unidades:
                phone = lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone'))
                address = lead.get('address', 'Endereço não cadastrado')
                rating = lead.get('totalScore', 'N/A')
                website = lead.get('website', 'Sem site')
                
                wpp_link = gerar_link_whatsapp(phone)
                wpp_btn = f"<a href='{wpp_link}' style='background-color: #25D366; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 10px;'>💬 Chamar no Whats</a>" if wpp_link else ""

                html_content += f"""
                <div style="background-color: #fff; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; margin-left: 15px;">
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📍 Unidade:</strong> {address}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>📞 Tel:</strong> {phone} {wpp_btn}</p>
                    <p style="margin: 2px 0; font-size: 14px;"><strong>⭐ Nota:</strong> {rating} | <strong>🌐 Link:</strong> <a href="{website}">{website}</a></p>
                </div>
                """

    html_content += """
    </body>
    </html>
    """

    try:
        apify_mail_url = f"https://api.apify.com/v2/acts/apify~send-mail/runs?token={APIFY_TOKEN}"
        mail_payload = {
            "to": EMAIL_RECEIVER,
            "subject": f"💎 Dossiê BLACK: {len(redes_locais)} Diamantes Detectados",
            "html": html_content
        }
        requests.post(apify_mail_url, json=mail_payload)
        print("[SISTEMA MAC] Dossiê Black focado ejetado com sucesso!")
    except Exception as e:
        return jsonify({"error": "Falha no envio"}), 500

    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
