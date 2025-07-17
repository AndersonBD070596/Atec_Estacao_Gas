#Nome  : Software de controle maquina de auto atendimento venda de vazilhame

#Autor : joao carlos borba -  

#Data  : 03/2025

#Versao: 7.6

#- config.json adicionando o campo 'apiKey'
#- adicionada a propriedade apiKey na classe 
#- Funcao _loadConfigFile() para ler o valor de apiKey
#- Headers da requisiçao GET do callback para usar a apikey e envia o content/type
#- mensagens de log que sao escritas em app.log
#- mensagens de Log
#- Ajuste na gerecia da data de expiracao do Token de Autenticacao
#- mensages e logging() Substituidas por logging.info

import threading
import tkinter as tk
from tkinter import messagebox  # Importar messagebox
from PIL import Image, ImageTk
import pygame
import os
import json
import multiprocessing
import cv2
import numpy as np
import time
import requests
from payer2 import AtecSystemLib
import logging
from datetime import datetime
from Conexao import Conexao
try:
    import RPi.GPIO as GPIO
except ImportError:
    from mock_rpi_gpio import GPIO

# Criação de pasta para armazenar os logs
pasta_logs = "./logs"
os.makedirs(pasta_logs, exist_ok=True)

# Nome do arquivo de log baseado na data atual
nome_arquivo_log = os.path.join(pasta_logs, f"App_{datetime.now().strftime('%Y-%m-%d')}.log")

# Classe de filtro personalizada para ignorar logs específicos
class FiltroIgnorarStream(logging.Filter):
    def filter(self, record):
        # Retorna False para ignorar mensagens contendo "STREAM"
        return "STREAM" not in record.getMessage()

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,  # Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Exibe os logs no terminal
        logging.FileHandler(nome_arquivo_log, encoding="utf-8")  # Salva os logs no arquivo
    ]
)

# Adicionar filtro para ignorar logs indesejados
for handler in logging.getLogger().handlers:
    handler.addFilter(FiltroIgnorarStream())

def camera_process(conn):
    logging.info("Camera Process")
    # Definindo os caminhos persistentes das câmeras
    camera_device_paths = ["/dev/video2", "/dev/video4", "/dev/video0"]
    #ordem das cameras 420
    # Caminhos das imagens fixas para comparação
    fixed_image_paths = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png", "10.png", "11.png", "12.png", "13.png", "14.png", "15.png", "16.png", "17.png", "18.png", "19.png", "20.png", "21.png", "22.png", "23.png", "24.png", "25.png", "26.png", "27.png", "28.png", "29.png", "30.png", "31.png", "32.png", "33.png", "34.png", "35.png", "36.png", "37.png", "38.png", "39.png", "40.png", "41.png", "42.png", "43.png", "44.png", "45.png", "46.png", "47.png", "48.png", "49.png", "50.png", "51.png", "52.png"]

    # Defina a quantidade de comparações para cada câmera antes de trocar
    max_captures_list = [14, 14, 13]  # Ajuste os valores conforme necessário para cada câmera
    
    # Inicializa e inicia a câmera com os caminhos persistentes e limites de captura específicos
    camera = Camera(camera_device_paths, fixed_image_paths, max_captures_list)
    camera.start(pipe=conn)

class Camera:
    def __init__(self, camera_indices, fixed_image_paths, max_captures_list):
        logging.info("Class Camera Iniciada")
        self.camera_indices = camera_indices
        self.fixed_image_paths = fixed_image_paths
        self.fixed_images = self.load_fixed_images()
        self.capture_counts = [0] * len(camera_indices)
        self.max_captures_list = max_captures_list
        self.cap = None
        self.camera_atual = 0
        self.initialize_camera()
    
    def load_fixed_images(self, pasta="Fotos_PB"):
        logging.info("Camera - Load Fixed Images")
        images = []
        try:
            # Verifica se a pasta existe
            if not os.path.exists(pasta):
                logging.error(f"Pasta '{pasta}' não encontrada.")
                return images
            # Lista todos os arquivos na pasta
            arquivos = [os.path.join(pasta, arquivo) for arquivo in os.listdir(pasta) if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))]
            # Carrega as imagens em preto e branco
            for caminho in arquivos:
                imagem = cv2.imread(caminho, cv2.IMREAD_GRAYSCALE)  # Lê a imagem em preto e branco
                if imagem is not None:
                    images.append(imagem)
                    logging.info(f"Imagem carregada: {caminho}")
                else:
                    logging.error(f"Erro ao carregar a imagem: {caminho}")
            if not images:
                logging.warning("Nenhuma imagem válida foi encontrada na pasta.")
        except Exception as e:
            logging.error(f"Erro ao carregar imagens da pasta '{pasta}': {e}")
        return images

    def initialize_camera(self):
        logging.info("Camera - Initialize Camera")
        """Tenta abrir a câmera atual. Fecha e reabre se necessário."""
        logging.info("\nReseta cameras")
        if self.cap:
            self.release_camera()  # Fecha qualquer câmera aberta anteriormente
    
        logging.info(f"inicializa camera {self.camera_atual} \n")
        self.cap = cv2.VideoCapture(self.camera_indices[self.camera_atual])
        if not self.cap.isOpened():
            raise ValueError(f"Não foi possível abrir a câmera {self.camera_indices[self.camera_atual]}")
        logging.info(f"Câmera {self.camera_indices[self.camera_atual]} inicializada.")

    def release_camera(self):
        logging.info("Camera - Release Camera")
        """Libera a câmera atual."""
        if self.cap:
            self.cap.release()
            logging.info(f"Câmera {self.camera_indices[self.camera_atual]} liberada.")

    def reset_camera(self):
        logging.info("Camera - Reset Camera")
        """Reinicializa a câmera atual."""
        logging.info(f"Resetando câmera {self.camera_indices[self.proxima]}")
        self.initialize_camera()

    def start(self, pipe):
        logging.info("Camera - Start")
        cv2.namedWindow("Câmera", cv2.WINDOW_NORMAL)

        # Adiciona uma espera de 3 segundos para inicialização da câmera
        logging.info("Aguardando inicialização da câmera...")
        time.sleep(2)  # Tempo de espera ajustável

        while self.camera_atual < len(self.camera_indices):
            ret, frame = self.cap.read()
            if not ret:
                logging.error(f"Falha na captura de imagem na câmera {self.camera_indices[self.camera_atual]}. Tentando reiniciar.")
                self.reinicia_camera()
                continue  # Tenta capturar novamente

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Converte o frame para preto e branco
            cv2.imshow("Câmera", gray_frame)

            if pipe.poll():
                command = pipe.recv()
                logging.info(f"Camera - comando - {command} - recebido")

                if command == 'camera1':
                    logging.info(f"Camera 1 - Selecinada")
                    if self.camera_atual != 0:
                        self.camera_atual = 0
                        self.initialize_camera()

                elif command == 'camera2':
                    logging.info(f"Camera 2 - Selecinada")
                    if self.camera_atual != 1:
                        self.camera_atual = 1
                        self.initialize_camera()

                elif command == 'camera3':
                    logging.info(f"Camera 3 - Selecinada")
                    if self.camera_atual != 2:
                        self.camera_atual = 2
                        self.initialize_camera()

                elif command == 'c':
                    
                    if not self.cap.isOpened():
                        self.initialize_camera()

                    logging.info(f"C:\n camera atual = {self.camera_atual}")

                    self.capture_counts[self.camera_atual] += 1
                    logging.info(f"Captura {self.capture_counts[self.camera_atual]} na câmera {self.camera_indices[self.camera_atual]}")
                    
                    if self.compare_images(gray_frame):
                        pipe.send('recognized')
                    else:
                        pipe.send('image_not_recognized')

                elif command == 'q':
                    logging.info(f"Comando para sair recebido. Finalizando.")
                    break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                logging.info(f"Saindo do programa.")
                break

        cv2.destroyAllWindows()
        self.release_camera()

    def compare_images(self, gray_frame):
        logging.info("Camera - Compare Images")
        """Compara o frame capturado com as imagens fixas em preto e branco."""
        for idx, fixed_image in enumerate(self.fixed_images):
            resized_frame = cv2.resize(gray_frame, (fixed_image.shape[1], fixed_image.shape[0]))
            correlation = cv2.matchTemplate(resized_frame, fixed_image, cv2.TM_CCOEFF_NORMED)
            max_corr = np.max(correlation)

            # Captura apenas os dois primeiros dígitos antes do ponto
            if max_corr >= 100:
                formatted_corr = str(max_corr)[:3]  # Trunca para os três primeiros caracteres
            elif max_corr >= 10:
                formatted_corr = str(max_corr)[:2]  # Trunca para os dois primeiros caracteres
            else:
                formatted_corr = f"{max_corr:.2f}"  # Formata para dois dígitos após o ponto se menor que 10

            logging.info(f"Imagem fixa {idx + 1}, correlação máxima: {formatted_corr}")

            if max_corr >= 0.35:  # Ajuste do limiar de correlação
                #0.35 07/04/2025
                logging.info(f"Imagem {idx + 1} reconhecida com correlação de {formatted_corr}")
                return True
        logging.error(f"Nenhuma imagem reconhecida.")
        return False
   
class Aplicativo:
    def __init__(self, root, camera_pipe):
        logging.info("Inicia Class Aplicativo")
        self.root = root
        self.canvas = tk.Canvas(self.root, width=600, height=800)
        self.canvas.pack()
        self.camera_pipe = camera_pipe
        
        self.quantidade_de_ciclos = [14, 14, 13]
        self.atual_ciclos = 0
        self.contador = 0
        
        self.pino_abre_porta = 23
        
        #Carrossel
        self.GPIO_PIN_12 = 12
        
        #porta 1
        self.GPIO_PIN_23 = 23 #abre
        self.GPIO_PIN_24 = 24 #fecha
        
        #porta 2
        self.GPIO_PIN_25 = 25 #abre
        self.GPIO_PIN_8 = 8 #fecha
        
        #porta 3
        self.GPIO_PIN_7 = 7 #abre
        self.GPIO_PIN_1 = 1 #fecha

        self.GPIO_PIN_26 = 26 #pota de recarga
        
        self.reproduzindo_som = False # Flag para controlar a reprodução de som
        #self.GPIO_PIN_13 = 13  # Corrigido o nome do pino
        # Contador de ciclos (inicializado em 0)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM) 
        

        # Configurar todos os pinos GPIO como saída e inicializá-los como LOW
        pinos_saida = [
            self.GPIO_PIN_12, 
            self.GPIO_PIN_23, self.GPIO_PIN_24,
            self.GPIO_PIN_25, self.GPIO_PIN_8, 
            self.GPIO_PIN_7, self.GPIO_PIN_1,
            self.GPIO_PIN_26, self.pino_abre_porta
        ]
        for pino in pinos_saida:
            GPIO.setup(pino, GPIO.OUT)
            GPIO.output(pino, GPIO.HIGH)  # Inicializar como LOW (desligado)

        #Configurar os pinos de entrada com resistores de pull-up
        GPIO.setup(self.GPIO_PIN_26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        root.title("Estacao gas 24hs")
        root.attributes('-fullscreen', True)
        pygame.mixer.init()

        # Carregar imagens, valores de pagamento e exibir a tela inicial
        self.imagens = {}
        self.carregar_imagens()
        
        self.telas = [
            {"tela": "Bemvindo.png", "som": "bemvindo.wav"}, #0
            {"tela": "Selecao.png", "som": "Opcaodepagamento.wav"}, #1
            {"tela": "Pagamento.png", "som": "Digiteasenha.wav"}, #2
            {"tela": "Senha.png", "som": "Digiteasenha.wav"}, #3
            {"tela": "Insiraobotijao.png", "som": "insiraobotijao.wav"}, #4
            {"tela": "toque_em_avancar.png", "som": "retire.wav"}, #5
            {"tela": "Analisando.png", "som": "Analisandobotijao.wav"}, #6
            {"tela": "botijaoreconhecido.png", "som": "botijao_reconhecido.wav"}, #7
            {"tela": "retirabotijao.png", "som": "agradecimento.wav"}, #8
            {"tela": "botijaorecusado.png", "som": "botijaorecusado.mp3"}, #9
            {"tela": "Maquina_Vazia.png", "som": "botijaorecusado.mp3"}, #10 
            {"tela": "Pagamento_REJEITADO.png", "som": "Pagamento_Rejeitado.wav"}, #11
            {"tela": "Pagamento_CANCELADO.png", "som": "Pagamento_Cancelado.wav"}, #12
            {"tela": "Pagamento_ABORTADO.png", "som": "Pagamento_Abortado.wav"}, #13
            {"tela": "Pagamento_NAO_AUTORIZADO.png", "som": "Pagamento_Nao_Autorizado.wav"}, #14
            {"tela": "recarregandoequipamento.png", "som": "botijaorecusado.mp3"}, #15
            {"tela": "Compra_Completa.png", "som": "botijaorecusado.mp3"}, #16
            {"tela": "Manutencao.png", "som": "botijaorecusado.mp3"}, #17
        ]

        self.indice_tela_atual = 0

        self.som_terminado = True

        self.teclado_virtual = None

        self.botoes_selecao_ativos = True
        self.botoes_pagamento_ativos = True
        self.botao_avancar_ativo = True

        self.porta_de_recarga_aberta = False
        self.time_porta_de_recarga = None

        self.valor_pagamento_com_vasilhame = 0.0
        self.valor_pagamento_sem_vasilhame = 0.0
        self.senha_correta = "1075"
        self.valor_pagamento = 0.0
        self.cor_bg = None
        self.metodo_pagamento = ''
        self.tipo_pagamento = ''
        self.After_Para_Tela_0 = None
        self.gif_label = self.Inserir_Gif("Maquininha.gif", (200, 200), (200, 390), 500)
        self.conexao = Conexao(self.root,self.canvas)
        self.Selecionar_Cor_Do_Pixel()
        self.carregar_valores_pagamento()
        self.carregar_contagem()

        self.exibir_tela()
        self.consultar_preco_periodicamente(intervalo_ms=60000)  # Atualiza a cada 60 segundos

        root.bind("<space>", self.fechar_aplicativo)
        root.bind("<Escape>", self.minimizar_janela)  # ESC para minimizar
        
        logging.info("Verificar GPIO Periodicamente Iniciado")
        self.verificar_gpio_periodicamente()
        self.verificar_pipe_periodicamente()
        self.conexao.verificar_conexao_periodicamente(self.exibir_tela)
        self.verificar_ciclo()
        logging.info(f"Inicial:\ncontador = {self.contador}\nciclo atual = {self.atual_ciclos}\nquantidade de ciclos = {self.quantidade_de_ciclos}\nabre = {self.pino_abre_porta}")

    def fechar_aplicativo(self, event=None):
        logging.info("Fechar Aplicativo")
        logging.info(f"Fechando aplicativo...")
        self.root.quit()  # Encerra o loop principal do Tkinter        

    def carregar_imagens(self):
        logging.info("Carregar Imagens")
        for tela in ["Bemvindo.png", "Selecao.png", "Pagamento.png", "Senha.png", 
                     "Insiraobotijao.png", "toque_em_avancar.png", "Analisando.png","botijaoreconhecido.png", 
                     "retirabotijao.png", "botijaorecusado.png","Maquina_Vazia.png", "Pagamento_REJEITADO.png",
                     "Pagamento_CANCELADO.png", "Pagamento_ABORTADO.png","Pagamento_NAO_AUTORIZADO.png", "recarregandoequipamento.png", 
                     "Compra_Completa.png", "Manutencao.png"]:
            
            caminho_imagem = os.path.join(os.getcwd(), tela)
            if os.path.exists(caminho_imagem):
                imagem = Image.open(caminho_imagem)
                imagem = imagem.resize((600, 800))
                imagem = imagem.rotate(0, expand=True)
                self.imagens[tela] = ImageTk.PhotoImage(imagem)
            else:
                logging.error(f"Arquivo de imagem não encontrado: {caminho_imagem}")
                # Adicionar imagem padrão caso a imagem não seja encontrada
                imagem_padrao = Image.new('RGB', (600, 800), color = (73, 109, 137))
                self.imagens[tela] = ImageTk.PhotoImage(imagem_padrao)

    def carregar_valores_pagamento(self):
        logging.info("Carregar Valores Pagamento")
        try:
            with open('valores_pagamento.json', 'r') as f:
                dados = json.load(f)
                self.valor_pagamento_com_vasilhame = dados.get('valor_pagamento_com_vasilhame', 0.0)
                self.valor_pagamento_sem_vasilhame = dados.get('valor_pagamento_sem_vasilhame', 0.0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.valor_pagamento_com_vasilhame = 0.0
            self.valor_pagamento_sem_vasilhame = 0.0

    def salvar_valores_pagamento(self):
        logging.info("Salvar Valores Pagamento")
        with open('valores_pagamento.json', 'w') as f:
            json.dump({
                'valor_pagamento_com_vasilhame': self.valor_pagamento_com_vasilhame,
                'valor_pagamento_sem_vasilhame': self.valor_pagamento_sem_vasilhame
            }, f)

    def exibir_tela(self):
        self.limpar_tela_anterior()
        logging.info(f"Tela Atual = {self.indice_tela_atual}")
        imagem = self.imagens.get(self.telas[self.indice_tela_atual]["tela"])
        if imagem:
            self.canvas.create_image(0, 0, anchor=tk.NW, image=imagem)

            # Verifica se estamos na tela 0
            if self.indice_tela_atual == 0:
                self.botoes_selecao_ativos = True
                self.botoes_pagamento_ativos = True
                self.botao_avancar_ativo = True
                logging.info(f"{self.indice_tela_atual} - Bem Vindo")
                self.canvas.bind("<Button-1>", lambda event: [self.reproduzir_som(), time.sleep(5), self.avancar_tela()])
            
            elif self.indice_tela_atual == 1:
                logging.info(f"{self.indice_tela_atual} - Selecao Vasilhame")
                self.canvas.unbind("<Button-1>")
                botao_com_vasilhame = tk.Button(self.canvas, text="C.V.", command=lambda: self.root.after(2000, self.Iniciar_Teclado(True,True)))
                self.canvas.create_window(550, 770, anchor=tk.NW, window=botao_com_vasilhame)
                botao_sem_vasilhame = tk.Button(self.canvas, text="S.V.", command=lambda: self.root.after(2000, self.Iniciar_Teclado(False,True)))
                self.canvas.create_window(490, 770, anchor=tk.NW, window=botao_sem_vasilhame)
                self.adicionar_botoes_selecao()
                self.adicionar_botao_voltar()
                self.After_Para_Tela_0 = self.root.after(120000,lambda:self.trocar_tela(0))

            elif self.indice_tela_atual == 2:
                logging.info(f"{self.indice_tela_atual} - Metodo de Pagamento")
                self.adicionar_botoes_pagamento()
                self.adicionar_botao_voltar()
                self.After_Para_Tela_0 = self.root.after(120000,lambda:self.trocar_tela(0))

            elif self.indice_tela_atual == 3:
                logging.info(f"{self.indice_tela_atual} - Executa Pagamento")
                self.gif_label = self.Inserir_Gif("MaquininhaV3.gif", (400, 250), (100, 375), 100)
                self.root.after(5000,
                lambda: threading.Thread(target=self.executar_pagamento, daemon=True).start())

            elif self.indice_tela_atual == 4:
                logging.info(f"{self.indice_tela_atual} - Insira O Botijao")
                self.root.after(2000, lambda: self.reproduzir_som("insiraobotijao.wav"))
                self.root.after(17000, lambda: self.trocar_tela(5))
          
            elif self.indice_tela_atual == 5:
                logging.info(f"{self.indice_tela_atual} - Toque Em Avancar")
                self.verificar_ciclo()
                botao_imagem = Image.open("avancar.png").resize((200, 150))
                botao_imagem = ImageTk.PhotoImage(botao_imagem)
                botao = tk.Button(self.canvas, image=botao_imagem, command=lambda: self.Botao_Avancar_Acionado(), bg=self.cor_bg, bd=0, highlightthickness=0,
                    activebackground=self.cor_bg, activeforeground=self.cor_bg)
                botao.image = botao_imagem
                self.canvas.create_window(200, 420, anchor=tk.NW, window=botao)
                
            elif self.indice_tela_atual == 6:
                logging.info(f"{self.indice_tela_atual} - Analisando")
                # Verifica se há resultado disponível no pipe e armazena
                self.root.after(20000, lambda: self.comparacao())
                       
            elif self.indice_tela_atual == 7:
                logging.info(f"{self.indice_tela_atual} - Botijao Reconhecido")
                self.root.after(2000, lambda: self.reproduzir_som("botijao_reconhecido_novo.wav"))
                self.root.after(10000, lambda: self.reproduzir_som("botijao_reconhecido_novo.wav"))
                self.root.after(20000, lambda: self.reproduzir_som("Aguarde_botijao_reconhecido.wav"))
                self.root.after(10000,lambda: self.acionar_saida(self.GPIO_PIN_12))
                self.root.after(30000, lambda: self.trocar_tela(8))
            
            elif self.indice_tela_atual == 8:
                logging.info(f"{self.indice_tela_atual} - Retire O Botijao")

                self.root.after(5000, lambda:self.reproduzir_som("compra_efetuada.wav"))
                self.root.after(15000, lambda:self.reproduzir_som("compra_efetuada.wav"))
                #self.root.after(20000, lambda:self.reproduzir_som("revendedor.wav"))
                self.root.after(25000, lambda:self.reproduzir_som("agradecimento.wav"))
                self.root.after(35000, lambda:self.reproduzir_som("agradecimento.wav"))

                self.add_contador()
                self.verificar_ciclo()
                self.acionar_saida(self.pino_abre_porta)
                self.root.after(30000,lambda: self.Fechar_Porta())
                if self.atual_ciclos==len(self.quantidade_de_ciclos)-1 and self.contador==self.quantidade_de_ciclos[len(self.quantidade_de_ciclos)-1]-1:
                    self.root.after(50000, lambda: self.trocar_tela(10))
                else:
                    self.root.after(50000, lambda: self.trocar_tela(0))
                  
            elif self.indice_tela_atual == 9:
                logging.info(f"{self.indice_tela_atual} - Botijao Nao Reconhecido")
                self.root.after(16000, lambda: self.acionar_saida(self.pino_abre_porta)) 
                self.root.after(1000, lambda: self.reproduzir_som("recusado.wav"))  # Toca o som pela segunda vez após 5 segundos
                self.root.after(7000, lambda: self.reproduzir_som("recusado.wav"))
                self.root.after(15000, lambda: self.reproduzir_som("recusado.wav"))  # Toca o som pela segunda vez após 5 segundos
                self.root.after(20000, lambda: self.reproduzir_som("recusado.wav"))
                self.root.after(50000, lambda: self.Fechar_Porta()) 
                self.root.after(60000, lambda: self.trocar_tela(0))
                  
            elif self.indice_tela_atual == 11:
                logging.info(f"{self.indice_tela_atual} - Pagamento Rejeitado")
                self.reproduzir_som()
                self.root.after(30000, lambda: self.trocar_tela(0))
            
            elif self.indice_tela_atual == 12:
                logging.info(f"{self.indice_tela_atual} - Pagamento Cancelado")
                self.reproduzir_som()
                self.root.after(30000, lambda: self.trocar_tela(0))
            
            elif self.indice_tela_atual == 13:
                logging.info(f"{self.indice_tela_atual} - Pagamento Abortado")
                self.reproduzir_som()
                self.root.after(30000, lambda: self.trocar_tela(0))
            
            elif self.indice_tela_atual == 14:
                logging.info(f"{self.indice_tela_atual} - Pagamento Nao autorizado")
                self.reproduzir_som()
                self.root.after(30000, lambda: self.trocar_tela(0))

            elif self.indice_tela_atual == 16:
                logging.info(f"{self.indice_tela_atual} - Compra 'Botijao + Carga' efetuada com sucesso")
                #self.root.after(1000,lambda: self.reproduzir_som("compra_efetuada.wav"))
                self.root.after(1000,lambda: self.reproduzir_som("aguarde.wav"))
                self.root.after(10000,lambda: self.reproduzir_som("aguarde.wav"))
                self.root.after(30000, lambda: self.trocar_tela(8))
            else :
                self.canvas.unbind("<Button-1>")

    def Botoes_Selecao_Acionados(self,valor_selecionado, tipo_selecionado,codigoitem):
        if self.botoes_selecao_ativos == True:
            self.botoes_selecao_ativos = False
            self.codigoitem = codigoitem
            self.selecionar_valor_pagamento(valor_selecionado, tipo_selecionado) 
            time.sleep(3)
            self.trocar_tela(2)
    
    def Botoes_Pagamento_Acionados(self, audio, metodo, tipo):
        if self.botoes_pagamento_ativos == True:
            self.botoes_pagamento_ativos = False
            self.reproduzir_som(audio)
            self.Selecionar_Metodo_Pagamento(metodo,tipo)

    def Botao_Avancar_Acionado(self):
        if self.botao_avancar_ativo == True:
            self.botao_avancar_ativo = False
            self.Fechar_Porta()
            self.reproduzir_som("Analisandobotijao.wav")
            self.root.after(10000, self.camera_pipe.send('c'))
            self.trocar_tela(6)

    def comparacao(self): 
        logging.info("Comparacao")       
        if self.camera_pipe.poll():
            #self.incrementar_contador()
            self.resultado_comparacao = self.camera.camera_pipe.recv()
            self.root.after(1000, lambda: self.reproduzir_som("Analisandobotijao.wav"))
        """
            # Exibe o resultado na tela
            self.canvas.create_text(300, 300, text=" Comparação em andamento...", font=("Arial", 16))
            self.canvas.create_text(300, 350, text=self.resultado_comparacao, font=("Arial", 12), fill="blue")
            #self.acionar_saida(self.GPIO_PIN_12)  
            
        else:
            # Exibe uma mensagem padrão enquanto aguarda o resultado
            self.canvas.create_text(300, 300, text=" Comparação em andamento...", font=("Arial", 16))
            self.canvas.create_text(300, 350, text="Aguardando resultado...", font=("Arial", 12), fill="orange")
        """
        
    def reproduzir_som(self, caminho_som=None):
        """
        Método para reproduzir som com suporte para diferentes cenários:
        - Evita reprodução duplicada.
        - Gerencia o estado de todos os botões durante a reprodução.
        - Permite especificar um arquivo de som ou usar um padrão.
        """
        logging.info(f"Reproduzir Som")
        # Verifica se já há um som sendo reproduzido
        if self.reproduzindo_som:
            logging.warning("Som já está sendo reproduzido.")
            return

        # Define o caminho do som padrão, se não for especificado
        if caminho_som is None:
            caminho_som = self.telas[self.indice_tela_atual]["som"]

        logging.info(f"Som = {caminho_som}")

        # Verifica se o arquivo de som existe
        if not os.path.exists(caminho_som):
            logging.error(f"Arquivo de som não encontrado: {caminho_som}")
            return

        try:
            # Inicializa o mixer do pygame
            pygame.mixer.init()
            self.reproduzindo_som = True

            # Carrega e toca o som
            pygame.mixer.music.load(caminho_som)
            pygame.mixer.music.play()

            # Desabilita todos os botões na interface
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Button):
                    widget.config(state='disabled')

            # Define callback para ações após o término do som
            duracao = int(pygame.mixer.Sound(caminho_som).get_length() * 1000)
            self.root.after(duracao, self.SomTerminadoFunc)
        except pygame.error as e:
            logging.error(f"Erro ao reproduzir som: {caminho_som}, {e}")
            self.reproduzindo_som = False

    def SomTerminadoFunc(self):
        """
        Callback chamado após o término do som para resetar estados.
        """
        logging.info("Reprodução de som finalizada.")
        self.reproduzindo_som = False

        # Reabilita todos os botões
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state='normal')

    def add_contador(self):
        logging.info("Add Contador")
        self.contador += 1  # Incrementa o contador corretamente
        if self.quantidade_de_ciclos[self.atual_ciclos] <= self.contador:
            self.contador = 0
            
            if self.atual_ciclos >= len(self.quantidade_de_ciclos) - 1:
                self.atual_ciclos = 0
            else:
                self.atual_ciclos += 1
        self.salvar_contagem()
        logging.info(f"\nContador:\nContaor = {self.contador}")

    def verificar_ciclo(self):
        logging.info("Verifica Ciclos")
        if self.atual_ciclos == 0:
            self.pino_abre_porta = self.GPIO_PIN_23
            self.camera_pipe.send('camera1')
        elif self.atual_ciclos == 1:
            self.pino_abre_porta = self.GPIO_PIN_25
            self.camera_pipe.send('camera2')
        elif self.atual_ciclos == 2:
            self.pino_abre_porta = self.GPIO_PIN_7 
            self.camera_pipe.send('camera3')
        logging.info(f"\nVerificar:\ncontador = {self.contador}\nciclo atual = {self.atual_ciclos}\nquantidade de ciclos = {self.quantidade_de_ciclos}\nabre = {self.pino_abre_porta}\n")
    
    def avancar_ciclo(self):
        logging.info("Avancar Ciclo")
        self.contador_ciclos += 1  # Incrementa o contador de ciclos
        self.atualizar_camera()  # Atualiza a câmera com base no contador    
                                   
    def retornar_para_tela_0(self):
        logging.info("Retornar Para Tela 0")
        self.indice_tela_atual = 0
        self.exibir_tela()

    def adicionar_botoes_selecao(self):
        logging.info("Adicionar Botoes Selecao")
        botoes = [
    {
        "imagem": "carga.png",
        "posicao": (87, 380),
        "texto": "VALOR",
        "valor": self.valor_pagamento_sem_vasilhame,
        "comando": lambda: self.Botoes_Selecao_Acionados(self.valor_pagamento_sem_vasilhame, "sem", 3)
    },
    {
        "imagem": "botijao.png",
        "posicao": (343, 380),
        "texto": "VALOR",
        "valor": self.valor_pagamento_com_vasilhame,
        "comando": lambda: self.Botoes_Selecao_Acionados(self.valor_pagamento_com_vasilhame, "com", 11)
    },
]

        for botao_info in botoes:
            botao_imagem = Image.open(botao_info["imagem"]).resize((170, 130))
            botao_imagem = ImageTk.PhotoImage(botao_imagem)
            botao = tk.Button(self.canvas, image=botao_imagem, command=botao_info["comando"], bg=self.cor_bg, bd=0, highlightthickness=0,
                    activebackground=self.cor_bg, activeforeground=self.cor_bg)
            botao.image = botao_imagem
            self.canvas.create_window(*botao_info["posicao"], anchor=tk.NW, window=botao)
            label_valor = tk.Label(self.canvas, text=f"{botao_info['texto']}: R${botao_info['valor']:.2f}", font=("Arial", 15, "bold"), bg="white", fg="black")
            self.canvas.create_window(botao_info["posicao"][0], botao_info["posicao"][1] + 145, anchor=tk.NW, window=label_valor)
            
    def selecionar_valor_pagamento(self, valor, tipo):
        logging.info("Selecionar Valor Pagamento")
        self.valor_pagamento = valor
        self.tipo_de_compra = tipo  # Armazena o tipo de pagamento selecionado
        logging.info(f"Valor: {valor}, Tipo: {tipo}")  # Para depuração
        self.reproduzir_som()

    def adicionar_botoes_pagamento(self):
        logging.info("Adicionar Botoes Pagamento")
        botoes = [
            #{"imagem": "pix.png", "posicao": (220, 380), "comando": lambda: self.Botoes_Pagamento_Acionados("Audio_pix.wav",'CARD', 'PIX') },
            {"imagem": "credito.png", "posicao": (220, 440), "comando": lambda: self.Botoes_Pagamento_Acionados("aproxime cartao.wav",'CARD', 'CREDITO')},
            {"imagem": "debito.png", "posicao": (220, 500), "comando": lambda: self.Botoes_Pagamento_Acionados("aproxime cartao.wav",'CARD', 'DEBITO')},
        ]
        for botao_info in botoes:
            botao_imagem = Image.open(botao_info["imagem"]).resize((150, 50))
            botao_imagem = ImageTk.PhotoImage(botao_imagem)
            botao = tk.Button(self.canvas, image=botao_imagem, command=botao_info["comando"], bg=self.cor_bg, bd=0, highlightthickness=0,
                    activebackground=self.cor_bg, activeforeground=self.cor_bg)
            botao.image = botao_imagem
            self.canvas.create_window(*botao_info["posicao"], anchor=tk.NW, window=botao)

    def adicionar_botao_voltar(self):
        logging.info("Adicionar Botao Voltar")
        botao_voltar_imagem = Image.open("VOLTAR.png").resize((100, 20))
        botao_voltar_imagem = ImageTk.PhotoImage(botao_voltar_imagem)
        botao_voltar = tk.Button(self.canvas, image=botao_voltar_imagem, command=self.voltar_tela, bg=self.cor_bg, bd=0, highlightthickness=0,
                    activebackground=self.cor_bg, activeforeground=self.cor_bg)
        botao_voltar.image = botao_voltar_imagem
        self.canvas.create_window(5, 770, anchor=tk.NW, window=botao_voltar)

    def voltar_tela(self):
        logging.info("Voltar Tela")
        if self.indice_tela_atual > 0:
            self.indice_tela_atual -= 1
            self.exibir_tela()

    def avancar_tela(self):
        logging.info("Avancar Tela")
        self.som_terminado = False
        self.indice_tela_atual += 1
        if self.indice_tela_atual >= len(self.telas):
            self.indice_tela_atual = 0
        self.exibir_tela()

    def limpar_tela_anterior(self):
        self.Destruir_Gif(self.gif_label)
        if self.After_Para_Tela_0 is not None:
            logging.info("Cancelado After_Para_Tela_0")
            self.root.after_cancel(self.After_Para_Tela_0)
        # Limpa todos os elementos do Canvas
        if hasattr(self, 'canvas'):
            self.canvas.delete("all")

    def fechar_aplicativo(self, event):
        logging.info("Fechar Aplicativo")
        self.camera_pipe.send('q')
        self.root.destroy()

    def Fechar_Porta(self):
        logging.info("Fechar Portas")
        GPIO.output(self.GPIO_PIN_24, GPIO.LOW)
        GPIO.output(self.GPIO_PIN_8, GPIO.LOW)
        GPIO.output(self.GPIO_PIN_1, GPIO.LOW)
        time.sleep(2)
        GPIO.output(self.GPIO_PIN_24, GPIO.HIGH)
        GPIO.output(self.GPIO_PIN_8, GPIO.HIGH)
        GPIO.output(self.GPIO_PIN_1, GPIO.HIGH)

    def acionar_saida(self, pin):
        logging.info(f"Acionar Saida {pin}")
        try:
            GPIO.output(pin, GPIO.LOW)  # Ligar a saída no pino especificado
            time.sleep(2)  # Manter a saída ligada por 2 segundos
            GPIO.output(pin, GPIO.HIGH)  # Desligar a saída
        except Exception as e:
            logging.error(f"Erro ao acionar saída {p} : {e}")


    def clicar_carga(self):
        self.codigoitem = 3
        self.executar_pagamento()

    def clicar_botijao(self):
        self.codigoitem = 11
        self.executar_pagamento()



    def executar_pagamento(self):
        logging.info("Executar Pagamento")
        try:
            atec = AtecSystemLib(
                url_api_base="http://atecgestao.masterdaweb.net",   # Ajuste aqui o IP ou URL da API
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJiZCI6ImNlcmVqZWlyYSIsImZpbGlhbCI6MX0.C1SSHTQT9tTAWV4-tzOEkQoXp0qdq0TS3rPCmeS9o94",                 # Ajuste aqui seu token
                terminal_pinpad= 4,           # Ajuste aqui o terminal pinpad
                id_maquina="",                         # Ajuste aqui o id da máquina
                tab_preco=1,                           # Ajuste aqui a tabela de preço
                codigoitem=self.codigoitem                         # Ajuste aqui o código do item
            )
            
            resultado = atec.payment(self.metodo_pagamento, self.tipo_pagamento, self.valor_pagamento)
            logging.info(f"Resultado do pagamento: {resultado}")

            if resultado is None:
                logging.info("Erro: Resultado do pagamento é None. Trocando para a tela de erro.")
                self.indice_tela_atual = 0
                self.exibir_tela()
                return

            if resultado.upper() == 'APPROVED':
                logging.info("Pagamento aprovado.")
                if self.valor_pagamento == self.valor_pagamento_com_vasilhame:
                    logging.info("Tipo de pagamento: com vasilhame. Trocando para a tela de aprovado com vasilhame.")
                    self.acionar_saida(self.GPIO_PIN_12)
                    self.root.after(1000, lambda: self.trocar_tela(16))
                else:
                    logging.info("Tipo de pagamento: sem vasilhame. Trocando para a tela de aprovado sem vasilhame.")
                    self.verificar_ciclo()
                    self.acionar_saida(self.pino_abre_porta)
                    self.trocar_tela(4)

            elif resultado.upper() == 'REJECTED':
                logging.info("Pagamento rejeitado.")
                self.trocar_tela(11)

            elif resultado.upper() == 'CANCELLED':
                logging.info("Pagamento cancelado.")
                self.trocar_tela(12)

            elif resultado.upper() == 'ABORTED':
                logging.info("Pagamento abortado.")
                self.trocar_tela(13)

            elif resultado.upper() == 'UNAUTHORIZED':
                logging.info("Pagamento nao autorizado.")
                self.trocar_tela(14)

            else:
                logging.warning(f"Resultado desconhecido do pagamento: {resultado}")
                self.trocar_tela(14)

        except Exception as e:
            logging.error(f"Erro durante o pagamento: {e}")
            self.trocar_tela(0)

            
    def Selecionar_Metodo_Pagamento(self,metodo,tipo):
        self.metodo_pagamento = metodo
        self.tipo_pagamento = tipo
        self.avancar_tela()

    def trocar_tela(self, indice):
        logging.info("Troca Tela")
        self.indice_tela_atual = indice
        self.exibir_tela()

    def Iniciar_Teclado(self, tipo, is_password=False):
            self.mostrar_teclado_virtual(tipo, is_password)

    def mostrar_teclado_virtual(self, tipo, is_password=False):
        logging.info("Mudar Teclado Virtual")  

        # Fecha a instância anterior, se existir  
        if self.teclado_virtual is not None and self.teclado_virtual.winfo_exists():  
            self.teclado_virtual.destroy()  
            self.teclado_virtual = None  

        if is_password:  
            # Criando o teclado para senha  
            self.teclado_virtual = TecladoVirtual(  
                self.root,  
                lambda valor: self.validar_senha(valor, tipo),  
                is_password=True,  
                titulo="Digite a sua senha"  
            )  
        else:  
            # Criando o teclado para valor  
            self.teclado_virtual = TecladoVirtual(  
                self.root,  
                lambda valor: self.atualizar_valor_pagamento(valor, tipo),  
                is_password=False,  
                titulo="Digite o valor"  
            )  

    def validar_senha(self, senha, tipo):
        logging.info("Validar Senha")
        if senha == self.senha_correta:
            self.mostrar_teclado_virtual(tipo)
        else:
            tk.messagebox.showerror("Erro", "Senha incorreta!")

    def atualizar_valor_pagamento(self, valor, tipo):
        logging.info("Atualizar Valor Pagamento")
        try:
            novo_valor = float(valor)
            if tipo:
                self.valor_pagamento_com_vasilhame = novo_valor
            else:
                self.valor_pagamento_sem_vasilhame = novo_valor
            self.salvar_valores_pagamento()  # Salva os novos valores de pagamento
            logging.info("Sucesso\nValor do pagamento atualizado com sucesso!")
            self.root.after(1000, lambda: messagebox.showinfo("Sucesso", "Valor do pagamento atualizado com sucesso!"))
        except ValueError:
            logging.warning("Atenção\nValor não foi atualizado. Entrada inválida.")
            self.root.after(1000, lambda: messagebox.showinfo("Atenção", "Valor não foi atualizado. Entrada inválida."))
        self.trocar_tela(1) 

    def limpar_gpio(self):
        logging.info("Limpar GPIO")
        GPIO.cleanup()

    def verificar_gpio_periodicamente(self):
        if GPIO.input(self.GPIO_PIN_26) == GPIO.LOW:
            if self.indice_tela_atual != 15 and self.indice_tela_atual != 7 and self.indice_tela_atual != 3 and self.porta_de_recarga_aberta == False:
                self.time_porta_de_recarga = self.root.after(5000,lambda: self.Porta_Recarga_Aberta())
        else:
            if self.time_porta_de_recarga is not None:
                self.root.after_cancel(self.time_porta_de_recarga)
            if self.indice_tela_atual == 15 and self.porta_de_recarga_aberta == True:
                self.Porta_Recarga_Fechada()
        self.root.after(100, self.verificar_gpio_periodicamente)
        
    def Porta_Recarga_Aberta(self):
        self.porta_de_recarga_aberta = True
        logging.info(f"Recarregando Maquina")
        self.trocar_tela(15)

    def Porta_Recarga_Fechada(self):
        self.porta_de_recarga_aberta = False
        logging.info(f"Recarga completa, indo para tela 0")
        self.contador=0
        self.atual_ciclos=0
        self.salvar_contagem()
        self.verificar_ciclo()
        self.root.after(120000, lambda:self.trocar_tela(0))

    def verificar_pipe_periodicamente(self):
        try:
            if self.camera_pipe.poll():  # Verifica se há mensagens no pipe
                message = self.camera_pipe.recv()  # Recebe a mensagem do pipe
                logging.info(f"Mensagem recebida do pipe: {message}")  # Verifique se a mensagem é recebida

                if message == 'image_not_recognized':
                    logging.info(f"Imagem não reconhecida. Trocando para a tela 8.")
                    self.trocar_tela(9)  # Exibe a tela 8
                    #self.root.after(10000, self.trocar_tela(0))
                elif message == 'recognized':
                    logging.info(f"Imagem reconhecida. Trocando para a tela 7.")
                    self.trocar_tela(7) 
        except Exception as e:
                logging.error(f"Erro ao verificar pipe: {e}")
        finally:
                self.root.after(1000, self.verificar_pipe_periodicamente)
    
    def minimizar_janela(self,event):
        self.root.iconify()  # Minimiza a janela
    
    def salvar_contagem(self):
        """Salva a contagem atual em um arquivo JSON."""
        try:
            dados = {
                "atual_ciclos": self.atual_ciclos,
                "contador": self.contador
            }
            with open("contagem.json", "w") as f:
                json.dump(dados, f)
            logging.info("Contagem salva com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao salvar contagem: {e}")

    def carregar_contagem(self):
        """Carrega a contagem salva de um arquivo JSON."""
        if not os.path.exists("contagem.json"):
            # Se o arquivo não existir, cria um com valores iniciais
            self.atual_ciclos = 0
            self.contador = 0
            self.salvar_contagem()  # Salva com valores iniciais
            logging.info("Arquivo de contagem não encontrado. Criado com valores iniciais.")
            return

        try:
            with open("contagem.json", "r") as f:
                dados = json.load(f)
                self.atual_ciclos = dados.get("atual_ciclos", 0)
                self.contador = dados.get("contador", 0)
            logging.info("Contagem carregada com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao carregar contagem: {e}")
    
    def Selecionar_Cor_Do_Pixel(self):
        image = Image.open("Bemvindo.png")
        pixel_color = image.getpixel((10, 960))
        self.cor_bg = '#{:02x}{:02x}{:02x}'.format(pixel_color[0], pixel_color[1], pixel_color[2])
        print(f"A cor do pixel ({10}, {960}) é {self.cor_bg}")

    def Inserir_Gif(self, caminho_gif, tamanho, posicao, intervalo):
        label_gif = tk.Label(self.canvas, bd=0, highlightthickness=0)
        label_gif.place(x=posicao[0], y=posicao[1])
        gif = Image.open(caminho_gif)
        frames = []
        try:
            while True:
                frame = gif.copy()
                bg = Image.new("RGBA", frame.size, self.cor_bg)
                frame = Image.alpha_composite(bg, frame.convert("RGBA"))
                frame = frame.resize(tamanho, Image.Resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(frame))
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass  

        def Animar(index=0):
            frame = frames[index]
            label_gif.configure(image=frame)
            label_gif.image = frame  
            label_gif.ani_id = self.root.after(intervalo, Animar, (index + 1) % len(frames))

        label_gif.frames = frames  # Armazena os frames para futura exclusão
        Animar()
        return label_gif  # Retorna o label para destruição futura

    def Destruir_Gif(self, label_gif):
        if hasattr(label_gif, "ani_id"):
            self.root.after_cancel(label_gif.ani_id)  # Cancela a animação
        label_gif.destroy()  # Remove o widget
        label_gif.frames.clear()  # Libera memória

    def Resetar(self):
        self.contador=0
        self.atual_ciclos=0
        self.salvar_contagem()
        self.trocar_tela(0)


    def consultar_preco_periodicamente(self, intervalo_ms=60000):
        #logging.info("Iniciando consulta de preço periódica")
        try:
            API_URL = "http://atecgestao.masterdaweb.net:9120/api/atecgaiola/produtos"
            headers = {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJiZCI6ImNlcmVqZWlyYSIsImZpbGlhbCI6MX0.C1SSHTQT9tTAWV4-tzOEkQoXp0qdq0TS3rPCmeS9o94",
                "Content-Type": "application/json"
            }
            payload = {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJiZCI6ImNlcmVqZWlyYSIsImZpbGlhbCI6MX0.C1SSHTQT9tTAWV4-tzOEkQoXp0qdq0TS3rPCmeS9o94",
                "codigo_carga": 3,
                "codigo_vasilhame": 11,
                "tab_preco": 1
            }

            resposta = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            if resposta.status_code == 200:
                dados = resposta.json()
                
                preco_carga = float(dados.get("preco_carga", 0.0))
                preco_vasilhame = float(dados.get("preco_vasilhame", 0.0))

                if preco_carga != self.valor_pagamento_sem_vasilhame or preco_vasilhame != self.valor_pagamento_com_vasilhame:

                    logging.info(f"Resposta da API: {dados}")
                    
                    if preco_carga > 0:
                        self.valor_pagamento_sem_vasilhame = preco_carga
                        logging.info(f"Preço carga atualizado: R${preco_carga:.2f}")
                    else:
                        logging.warning("Preço da carga inválido ou zero")

                    if preco_vasilhame > 0:
                        self.valor_pagamento_com_vasilhame = preco_vasilhame
                        logging.info(f"Preço vasilhame atualizado: R${preco_vasilhame:.2f}")
                    else:
                        logging.warning("Preço do vasilhame inválido ou zero")

                self.salvar_valores_pagamento()

            else:
                logging.warning(f"Erro na consulta da API: {resposta.status_code} - {resposta.text}")
        except Exception as e:
            logging.error(f"Erro na requisição de preço: {e}")

        # Agenda a próxima execução
        self.root.after(intervalo_ms, lambda: self.consultar_preco_periodicamente(intervalo_ms))

        
if __name__ == "__main__":
    parent_conn, child_conn = multiprocessing.Pipe()  # Cria um pipe
    p = multiprocessing.Process(target=camera_process, args=(child_conn,))  # Define o alvo do processo
    p.start()  # Inicia o processo
    root = tk.Tk()  # Cria a janela principal
    app = Aplicativo(root, parent_conn)  # Inicializa o aplicativo com o pipe
    root.mainloop()  # Inicia o loop da interface gráfica
    p.join()  # Aguarda o término do processo
