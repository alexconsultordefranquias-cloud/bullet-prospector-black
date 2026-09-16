
import os
import requests
import re
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CHAVES DO COFRE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
# COLE A URL DO SEU MAKE.COM NA LINHA ABAIXO, MANTENDO AS ASPAS:
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/7nwto66u2xhlwtunucxwm5mzuwml3twq"

# --- A GRANDE MURALHA (BLACKLIST MULTI-SETORIAL) ---
BLACKLIST = [
    "mcdonald", "burger king", "subway", "bob's", "bobs", "madero", "kfc", "giraffas", "outback", "habib",
    "cacau show", "china in box", "spoleto", "dominos", "domino's", "pizza hut", "coco bambu", "jerônimo", "jeronimo",
    "microlins", "kumon", "wizard", "fisk", "ccaa", "yázigi", "yazigi", "cna", "minds", "influx", 
    "senai", "senac", "sesi", "fatec", "etec", "grau técnico", "grau tecnico", "cebrac", "embelleze",
    "prepara", "faculdade", "universidade", "unip", "estácio", "estacio", "anhanguera", "mackenzie", "myrobot",
    "smart fit", "smartfit", "skyfit", "bluefit", "panobianco", "pratique", "selfit", "gavioes", "gaviões",
    "espaço laser", "espaçolaser", "laser fast", "emagrecentro", "giorgio", "sobrancelhas design", "giolaser", "onodera",
    "boticário", "boticario", "natura", "avon", "quem disse", "água de cheiro", "agua de cheiro", "l'occitane", "loccitane",
    "chiquinho", "bacio di latte", "oggi", "sr sorvete", "los paleteros", "ice cream roll",
    "5asec", "5àsec", "lavateria", "dryclean usa", "prima clean", "quality lavanderia",
    "coral", "suvinil", "decor colors", "tintas mc", "lukscolor",
    "petz", "cobasi", "petland", "zee.dog", "zeedog",
    "hcc energia", "portal solar", "blue sol", "solar prime",
    "bosch", "localiza", "unidas", "movida", "mercadocar", "dpk", "porto seguro", "getninjas", "corleone", "seu elias"
]

# --- FILTROS SEMÂNTICOS ---
TERMOS_FRANQUIA = ["franquia", "franchising", "franqueado", "seja um franqueado"]
TERMOS_PUBLICOS = [
    "escola estadual", "escola municipal", " e.e ", " e.e. ", " e.m ", " e.m. ", 
    "emef", "emei", " c.e.i ", "cei ", "colegio estadual", "colégio estadual", 
    "prefeitura", "governo do estado", "centro de educação infantil"
]

def normalize_name(name):
    name = re.split(r'[-|,]', name)[0]
    return name.strip().lower()

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
        
        # Escudo de Franquias e Ruídos
        if any(bad in name.lower() for bad in BLACKLIST):
            leads_descartados += 1
            continue
            
        texto_analise = (" " + name + " " + description + " ").lower()
        if any(termo in texto_analise for termo in TERMOS_FRANQUIA) or any(termo in texto_analise for termo in TERMOS_PUBLICOS):
            leads_descartados += 1
            continue

        norm_name = normalize_name(name)
        grouped_leads[norm_name].append(lead)

    # ISOLAMENTO DE DIAMANTES (2 a 4 unidades)
    redes_locais = {k: v for k, v in grouped_leads.items() if 1 < len(v) <= 4}

    if not redes_locais:
         return jsonify({"status": "Nenhum diamante encontrado."}), 200

    # PREPARAÇÃO DO PACOTE DE DADOS PUROS PARA O MAKE.COM
    diamantes_para_make = []
    for rede_name, unidades in redes_locais.items():
        nome_formatado = unidades[0].get('title').split('-')[0].split(',')[0].strip().upper()
        
        detalhes_unidades = []
        for lead in unidades:
            detalhes_unidades.append({
                "telefone": lead.get('phoneUnformatted', lead.get('phone', 'Sem telefone')),
                "endereco": lead.get('address', 'Endereço não cadastrado'),
                "website": lead.get('website', 'Sem site'),
                "nota": lead.get('totalScore', 'N/A')
            })
            
        diamantes_para_make.append({
            "nome_rede": nome_formatado,
            "quantidade_unidades": len(unidades),
            "unidades": detalhes_unidades
        })

    payload_make = {
        "leads_descartados": leads_descartados,
        "total_redes_encontradas": len(diamantes_para_make),
        "diamantes": diamantes_para_make
    }

    # DISPARO PARA O MAKE.COM
    if "hook.us2.make.com" in MAKE_WEBHOOK_URL:
        try:
            requests.post(MAKE_WEBHOOK_URL, json=payload_make)
            print("[SISTEMA MAC] Carga transferida para o orquestrador Make com sucesso!")
        except Exception as e:
            return jsonify({"error": "Falha ao enviar para o Make"}), 500

    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
