
from datetime import datetime
import requests
import time
import logging
import json
import uuid
class AtecSystemLib:
    def __init__(self):
        self.url_api_base = "http://atecgestao.masterdaweb.net"
        
        with open('AtecConfig.json', 'r', encoding='utf-8') as arquivo:
            loadedJson = json.load(arquivo)
        self.token = loadedJson.get("token")
        self.terminal_pinpad = loadedJson.get("terminal_pinpad")
        self.id_maquina = loadedJson.get("id_maquina")
        self.tab_preco = loadedJson.get("tab_preco")
        self.maquina_registrada = loadedJson.get("maquina_registrada")
        self.codigoitem = 0

        self.API_GAIOLA = f"{self.url_api_base}:9120/api/atecgaiola/"
        self.API_PAYMENT = f"{self.url_api_base}:8000/"

        self.order = None
        self.order_id = 0
        self.payment_id = 0
        self.status = ""
        self.status_message = ""
        if not self.maquina_registrada:
            self.Registrar_Maquina()

    def set_order(self, valor, tipo_pagamento):
        self.order = {
            "codigo_venda": int(time.time()),
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "valor_total": valor,
            "id_maquina": self.id_maquina,
            "tab_preco": self.tab_preco,
            "token": self.token,
            "cliente:": {
                "cpf_cnpj": {"cpf_cnpj": ""}
            },
            "pagamento": [
                {
                    "tipo": tipo_pagamento,
                    "dados_pagamento": {
                        "codigo_autenticacao": "",
                        "bandeira": "",
                        "cnpj_credenciadora": ""
                    },
                    "valor": valor
                }
            ],
            "item": [
                {
                    "id_atec": self.codigoitem,
                    "valor": valor
                }
            ]
        }

    def _send_post(self, url, dados, headers=None):
        try:
            resposta = requests.post(url, json=dados, headers=headers, timeout=10)
            resposta.raise_for_status()
            logging.info(f"POST enviado com sucesso para {url}")
            return resposta.json()
        except requests.exceptions.RequestException as erro:
            logging.error(f"Erro ao enviar POST: {erro}")
            return None

    def _send_get(self, url, headers=None):
        try:
            resposta = requests.get(url, headers=headers, timeout=10)
            resposta.raise_for_status()
            logging.info(f"GET enviado com sucesso para {url}")
            return resposta.json()
        except requests.exceptions.RequestException as erro:
            logging.error(f"Erro ao enviar GET: {erro}")
            return None

    def send_order(self):
        headers = {"Content-Type": "application/json"}
        json_response = self._send_post(self.API_GAIOLA + "venda", self.order, headers)
        if json_response and "codigo_venda" in json_response:
            self.order_id = json_response["codigo_venda"]
            logging.info(f"Venda registrada com código: {self.order_id}")
            return True
        else:
            self.status = "error"
            self.status_message = "Erro ao enviar a ordem."
            return False

    def process_payment(self):
        headers = {"Content-Type": "application/json"}
        paydata = {
            "terminal": self.terminal_pinpad,
            "token": self.token,
            "order": self.order_id
        }
        json_response = self._send_post(self.API_PAYMENT + "payments/createbyorder", paydata, headers)
        if json_response and "payment_id" in json_response:
            self.payment_id = json_response["payment_id"]
            logging.info(f"Pagamento iniciado com ID: {self.payment_id}")
            return True
        else:
            self.status = "error"
            self.status_message = "Erro ao criar pagamento."
            return False

    def processing(self):
        json_response = self._send_get(self.API_PAYMENT + f"payments/{self.payment_id}")
        if json_response:
            self.status = json_response.get("status", "")
            self.status_message = json_response.get("message", "")
        else:
            self.status = "error"
            self.status_message = "Erro ao consultar status do pagamento."
        return self.status

    def payment(self, metodo, tipo, valor, item):
        logging.info(f"Iniciando pagamento: método={metodo}, tipo={tipo}, valor={valor}")
        self.codigoitem = item
        try:
            self.set_order(valor, tipo)

            if not self.send_order():
                return "REJECTED"

            if not self.process_payment():
                return "REJECTED"

            if 3 != self.codigoitem != 11:
                return "REJECTED"
            
            while True:
                status = self.processing()
                logging.info(f"Status do pagamento: {status} - {self.status_message}")
                if status.lower() != "pending":
                    break
                time.sleep(1)

            return self.status.upper() if self.status else "REJECTED"

        except Exception as e:
            logging.error(f"Erro no processo de pagamento: {e}")
            return "REJECTED"

    def Precos(self):
        API_URL = self.url_api_base + ":9120/api/atecgaiola/produtos"
        headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json"
        }
        payload = {
            "token": self.token,
            "codigo_carga": 3,
            "codigo_vasilhame": 11,
            "tab_preco": self.tab_preco
        }

        return requests.post(API_URL, headers=headers, json=payload, timeout=10)

    def Registrar_Maquina(self):
        url = self.url_api_base + "http://atecgestao.masterdaweb.net:9120/api/atecgaiola/maquina"
        
        payload = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJiZCI6ImNlcmVqZWlyYSIsImZpbGlhbCI6MX0.C1SSHTQT9tTAWV4-tzOEkQoXp0qdq0TS3rPCmeS9o94",
            "uuid": uuid.uuid4().hex[:30],
            "plataforma": "Linux",
            "versaoos": "Debian",
            "versaoapp": "7.6"
        }

        try:
            resposta = requests.post(url, json=payload, timeout=10)
            print(resposta)
            dados_armazenados = {
                "data_hora": datetime.now().isoformat(),
                "dados_enviados": payload,
                "status_code": resposta.status_code,
                "resposta_api": resposta.json() if resposta.status_code == 200 else resposta.text
            }

            with open("Dados_Maquina.json", "w", encoding="utf-8") as f:
                json.dump(dados_armazenados, f, indent=4, ensure_ascii=False)

            if resposta.status_code == 200:
                print("✅ Dados enviados e salvos com sucesso.")
                self.id_maquina = resposta["id_maquina"]
                self.maquina_registrada = True
                self.Salvar_Config()
                return resposta.json()
            else:
                print(f"❌ Erro ao enviar dados: {resposta.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Falha na conexão: {e}")
            # Salva o erro também
            erro_info = {
                "data_hora": datetime.now().isoformat(),
                "dados_enviados": payload,
                "erro": str(e)
            }
            with open("Dados_Maquina.json", "w", encoding="utf-8") as f:
                json.dump(erro_info, f, indent=4, ensure_ascii=False)
            return None

    def Salvar_Config(self):
        dados_config = {
            "token": self.token,
            "terminal_pinpad": self.terminal_pinpad,
            "id_maquina": self.id_maquina,
            "tab_preco": self.tab_preco,
            "Maquina_Registrada": self.maquina_registrada
        }

        with open("AtecConfig.json", "w", encoding="utf-8") as arquivo:
            json.dump(dados_config, arquivo, indent=4, ensure_ascii=False)
