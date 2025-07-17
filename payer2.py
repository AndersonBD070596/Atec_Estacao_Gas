
from datetime import datetime
import requests
import time
import logging

class AtecSystemLib:
    def __init__(self, url_api_base, token, terminal_pinpad, id_maquina, tab_preco, codigoitem):
        self.url_api_base = url_api_base.rstrip('/')
        self.token = token
        self.terminal_pinpad = terminal_pinpad
        self.id_maquina = id_maquina
        self.tab_preco = tab_preco
        self.codigoitem = codigoitem

        self.API_GAIOLA = f"{self.url_api_base}:9120/api/atecgaiola/"
        self.API_PAYMENT = f"{self.url_api_base}:8000/"

        self.order_id = 0
        self.payment_id = 0
        self.status = ""
        self.status_message = ""

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
            resposta = requests.post(url, json=dados, headers=headers, timeout=60)
            resposta.raise_for_status()
            logging.info(f"POST enviado com sucesso para {url}")
            return resposta.json()
        except requests.exceptions.RequestException as erro:
            logging.error(f"Erro ao enviar POST: {erro}")
            return None

    def _send_get(self, url, headers=None):
        try:
            resposta = requests.get(url, headers=headers, timeout=60)
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

    def payment(self, metodo, tipo, valor):
        logging.info(f"Iniciando pagamento: método={metodo}, tipo={tipo}, valor={valor}")

        try:
            self.set_order(valor, tipo)

            if not self.send_order():
                return "REJECTED"

            if not self.process_payment():
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
