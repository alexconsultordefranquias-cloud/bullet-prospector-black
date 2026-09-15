from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ==========================================
# VARIÁVEIS DE AMBIENTE (CHAVES DE SEGURANÇA)
# ==========================================
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")

# ==========================================
# MÓDULOS DE INTELIGÊNCIA
# ==========================================
def enriquecer_contato_apollo(dominio):
    url = "https://api.apollo.io/v1/organizations/enrich"
    headers = {"Cache-Control": "no-cache", "Content-Type": "application/json"}
    payload = {"api_key": APOLLO_API_KEY, "domain": dominio}
    try:
        response = requests.post(url, headers=headers, json=payload).json()
        ceo_name = response['organization']['primary_contact']['name']
        ceo_phone = response['organization']['primary_contact']['mobile_number']
        return ceo_name, ceo_phone
    except:
        return None, None

def juiz_cognitivo_openai(dados_empresa):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Analise a empresa: {dados_empresa}. Critérios: 1. Mais de 2 unidades confirmadas? 2. CEO identificado? Responda EXATAMENTE com 'TRUE' (aprovado) ou 'FALSE' (lixo)."
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "Você é o Mac, engenheiro implacável da SellOut Academy."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        response = requests.post(url, headers=headers, json=payload).json()
        decisao = response['choices'][0]['message']['content'].strip()
        return "TRUE" in decisao
    except:
        return False

def disparar_ataque_whatsapp(telefone, mensagem):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN:
        print("[AVISO] Chaves do WhatsApp não configuradas. Disparo ignorado.")
        return
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"phone": telefone, "text": mensagem}
    requests.post(WHATSAPP_API_URL, headers=headers, json=payload)

# ==========================================
# ROTA DO SERVIDOR (WEBHOOK PARA O APIFY)
# ==========================================
@app.route('/webhook/apify', methods=['POST'])
def receber_dados_apify():
    print("[SISTEMA MAC] Webhook acionado. Duto aberto.")
    
    dados_recebidos = request.json
    run_id = dados_recebidos.get('eventData', {}).get('actorRunId')
    
    if not run_id:
        return jsonify({"status": "erro", "mensagem": "Run ID não encontrado"}), 400
        
    print(f"[PROCESSANDO] Sugando dados do Run ID: {run_id}")
    url_extracao = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_TOKEN}"
    response = requests.get(url_extracao)
    
    if response.status_code == 200:
        leads = response.json()
        alvos_atingidos = 0
        
        for lead in leads:
            dominio = lead.get("website")
            if not dominio:
                continue
                
            ceo_nome, ceo_telefone = enriquecer_contato_apollo(dominio)
            if ceo_nome and ceo_telefone:
                lead['ceo_nome'] = ceo_nome
                lead['ceo_telefone'] = ceo_telefone
                
                if juiz_cognitivo_openai(lead):
                    print(f"[SCORE 5] Diamante Negro: {lead.get('title', dominio)}")
                    # Script de Ataque Hormozi simplificado para injeção inicial
                    msg_ataque = f"Olá {ceo_nome}, identificamos gargalos na expansão própria da sua rede. A SellOut Academy tem o modelo para estruturar isso via franquia. Tem agenda essa semana?"
                    disparar_ataque_whatsapp(ceo_telefone, msg_ataque)
                    alvos_atingidos += 1
                    
        return jsonify({"status": "sucesso", "alvos_processados": alvos_atingidos}), 200
    else:
        return jsonify({"status": "erro", "mensagem": "Falha na extração do Apify"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
