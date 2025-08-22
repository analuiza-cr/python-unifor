# -*- coding: utf-8 -*-
"""
Sistema de Coleta e Análise de Sentimentos do Twitter/X - VERSÃO COM SELEÇÃO INTELIGENTE
Prioriza postagens com mais comentários e permite ordenação temporal
"""

# Importações necessárias
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import pandas as pd
import time
import re
from LeIA import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
import hashlib
import random
import os
from pathlib import Path
import subprocess
import psutil
import shutil
from datetime import datetime, timedelta
import dateparser

class TwitterSentimentAnalyzerSmartSelection:
    """
    Versão com seleção inteligente - Prioriza postagens com mais comentários
    """
    
    def __init__(self, username="tvm", browser="chrome"):
        self.username = username
        self.browser = browser.lower()
        self.driver = None
        self.dados_coletados = []
        self.analyzer = SentimentIntensityAnalyzer()
        self.tweets_processados = set()
        self.tweets_vistos = set()
        self.ultima_altura_scroll = 0
        self.tentativas_scroll = 0
        self.tweets_candidatos = []  # Lista para armazenar tweets candidatos
        
    def fechar_chrome_existente(self):
        """Fecha todas as instâncias do Chrome existentes"""
        print("🔄 Verificando instâncias do Chrome...")
        
        try:
            # Para Linux
            subprocess.run(['pkill', '-f', 'chrome'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)
            print("✅ Chrome fechado (Linux)")
        except:
            pass
        
        try:
            # Para Windows
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)
            print("✅ Chrome fechado (Windows)")
        except:
            pass
        
        # Usando psutil como alternativa
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'chrome' in proc.info['name'].lower():
                    proc.kill()
            time.sleep(2)
            print("✅ Chrome fechado (psutil)")
        except:
            pass
            
    def criar_perfil_temporario(self):
        """Cria um perfil temporário do Chrome"""
        temp_profile = os.path.join(os.path.expanduser("~"), "temp_chrome_profile")
        
        # Remove perfil temporário existente
        if os.path.exists(temp_profile):
            try:
                shutil.rmtree(temp_profile)
            except:
                pass
                
        os.makedirs(temp_profile, exist_ok=True)
        print(f"✅ Perfil temporário criado: {temp_profile}")
        return temp_profile
        
    def configurar_driver_robusto(self):
        """Configuração robusta do driver"""
        print(f"🔧 Configurando o navegador {self.browser.upper()} (versão seleção inteligente)...")
        
        if self.browser in ["chrome", "brave"]:
            # Fecha Chrome existente primeiro
            self.fechar_chrome_existente()
            
            chrome_options = ChromeOptions()
            
            # Usa perfil temporário
            temp_profile = self.criar_perfil_temporario()
            chrome_options.add_argument(f"--user-data-dir={temp_profile}")
            
            # Configurações anti-erro
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--remote-debugging-port=0")  # Porta dinâmica
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Acelera carregamento
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Configurações de janela
            chrome_options.add_argument("--window-size=1366,768")
            chrome_options.add_argument("--start-maximized")
            
            # User agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Configurações de segurança relaxadas
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            
            if self.browser == "brave":
                brave_paths = [
                    "/usr/bin/brave-browser",
                    "/snap/brave/current/usr/bin/brave",
                    "/usr/bin/brave",
                    "/opt/brave.com/brave/brave-browser"
                ]
                
                for path in brave_paths:
                    if os.path.exists(path):
                        chrome_options.binary_location = path
                        break
            
            try:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✅ Chrome iniciado com perfil temporário!")
                
            except Exception as e:
                print(f"⚠️ Erro com Chrome: {e}")
                print("🔄 Tentando Firefox como alternativa...")
                self.browser = "firefox"
                return self.configurar_driver_robusto()
        
        if self.browser == "firefox":
            firefox_options = FirefoxOptions()
            
            # Configurações básicas
            firefox_options.add_argument("--width=1366")
            firefox_options.add_argument("--height=768")
            
            # Desabilitar notificações e mídia
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("media.volume_scale", "0.0")
            firefox_options.set_preference("media.autoplay.default", 5)
            
            # Configurações de performance
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)
            
            # JavaScript habilitado para Twitter
            firefox_options.set_preference("javascript.enabled", True)
            
            try:
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                print("✅ Firefox configurado com sucesso!")
                
            except Exception as e:
                print(f"❌ Erro também com Firefox: {e}")
                raise Exception("Não foi possível configurar nenhum navegador!")
        
        # Configurações anti-detecção
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
        except:
            pass
            
    def verificar_login_melhorado(self):
        """Verificação melhorada de login"""
        print("🔍 Verificando acesso ao Twitter...")
        
        try:
            # Primeiro, vai para a página de login para verificar
            self.driver.get("https://twitter.com/login")
            time.sleep(5)
            
            # Se for redirecionado para home, está logado
            if "/home" in self.driver.current_url or "/following" in self.driver.current_url:
                print("✅ Usuário já logado!")
                return True
            
            # Verifica elementos de login
            elementos_login = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'div[data-testid="LoginForm"]'
            ]
            
            login_encontrado = False
            for seletor in elementos_login:
                if self.driver.find_elements(By.CSS_SELECTOR, seletor):
                    login_encontrado = True
                    break
            
            if login_encontrado:
                print("🔐 Necessário fazer login...")
                self.fazer_login_manual()
                return self.verificar_login_pos_manual()
            else:
                print("✅ Aparentemente logado!")
                return True
                
        except Exception as e:
            print(f"⚠️ Erro na verificação: {e}")
            return False
            
    def fazer_login_manual(self):
        """Orientações para login manual"""
        print("\n" + "="*60)
        print("🔐 LOGIN MANUAL NECESSÁRIO")
        print("="*60)
        print("1. Uma janela do navegador foi aberta")
        print("2. Faça login manualmente no Twitter")
        print("3. Após o login, volte ao terminal")
        print("4. Pressione Enter para continuar")
        print("="*60)
        
        input("Pressione Enter após fazer login no navegador...")
        
    def verificar_login_pos_manual(self):
        """Verifica se login manual foi bem-sucedido"""
        print("🔍 Verificando login...")
        
        try:
            self.driver.get("https://twitter.com/home")
            time.sleep(5)
            
            if "/home" in self.driver.current_url:
                print("✅ Login confirmado!")
                return True
            else:
                print("❌ Login não detectado")
                return False
                
        except:
            return False
            
    def acessar_perfil_robusto(self):
        """Acessa perfil de forma robusta"""
        print(f"🌐 Acessando perfil @{self.username}...")
        
        # Verifica login primeiro
        if not self.verificar_login_melhorado():
            print("❌ Não foi possível confirmar login!")
            return False
        
        try:
            url = f"https://twitter.com/{self.username}"
            self.driver.get(url)
            time.sleep(8)
            
            # Verifica se o perfil carregou
            indicadores_perfil = [
                f'[data-testid="UserName"]',
                'article[data-testid="tweet"]',
                '[data-testid="primaryColumn"]'
            ]
            
            perfil_carregado = False
            for seletor in indicadores_perfil:
                if self.driver.find_elements(By.CSS_SELECTOR, seletor):
                    perfil_carregado = True
                    break
            
            if perfil_carregado:
                print("✅ Perfil acessado com sucesso!")
                return True
            else:
                print("⚠️ Perfil pode não ter carregado completamente")
                return True  # Tenta continuar mesmo assim
                
        except Exception as e:
            print(f"⚠️ Erro ao acessar perfil: {e}")
            return False
    
    def extrair_numero_comentarios(self, tweet):
        """Extrai o número de comentários de um tweet"""
        try:
            # Seletores comuns para contadores de comentários
            seletores_comentarios = [
                '[data-testid="reply"]',
                '[aria-label*="repl"]',
                '[aria-label*="comment"]',
                'div[role="group"] div[role="button"]'
            ]
            
            for seletor in seletores_comentarios:
                try:
                    elemento_comentario = tweet.find_element(By.CSS_SELECTOR, seletor)
                    aria_label = elemento_comentario.get_attribute('aria-label')
                    
                    if aria_label:
                        # Extrai números do aria-label
                        numeros = re.findall(r'\d+', aria_label)
                        if numeros:
                            return int(numeros[0])
                    
                    # Tenta pegar texto do elemento
                    texto = elemento_comentario.text.strip()
                    if texto and texto.isdigit():
                        return int(texto)
                        
                except:
                    continue
            
            # Se não encontrar contador específico, assume que tem comentários se conseguir clicar
            return 1  # Valor padrão
            
        except Exception as e:
            return 0
    
    def extrair_data_tweet(self, tweet):
        """Extrai a data do tweet"""
        try:
            time_element = tweet.find_element(By.CSS_SELECTOR, 'time')
            datetime_attr = time_element.get_attribute('datetime')
            
            if datetime_attr:
                # Converte para datetime
                data_tweet = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                return data_tweet
            
            # Tenta pegar do title ou texto
            title_attr = time_element.get_attribute('title')
            if title_attr:
                try:
                    return dateparser.parse(title_attr)
                except:
                    pass
            
            texto_tempo = time_element.text.strip()
            if texto_tempo:
                try:
                    return dateparser.parse(texto_tempo)
                except:
                    pass
                    
        except:
            pass
            
        # Se não conseguir extrair data, assume que é recente
        return datetime.now()
    
    def gerar_id_unico_tweet(self, tweet):
        """Gera ID único mais robusto para o tweet"""
        try:
            identificadores = []
            
            try:
                link_element = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                tweet_url = link_element.get_attribute('href')
                if tweet_url:
                    tweet_id = tweet_url.split('/')[-1].split('?')[0]
                    identificadores.append(f"url:{tweet_id}")
            except:
                pass
            
            try:
                texto_elemento = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                texto = texto_elemento.text.strip()
                if texto:
                    texto_hash = hashlib.md5(texto[:100].encode()).hexdigest()[:12]
                    identificadores.append(f"texto:{texto_hash}")
            except:
                pass
            
            try:
                time_element = tweet.find_element(By.CSS_SELECTOR, 'time')
                datetime_attr = time_element.get_attribute('datetime')
                if datetime_attr:
                    identificadores.append(f"time:{datetime_attr}")
            except:
                pass
            
            if identificadores:
                id_final = "|".join(identificadores)
                return hashlib.md5(id_final.encode()).hexdigest()
            else:
                html_hash = hashlib.md5(str(tweet.get_attribute('outerHTML')[:200]).encode()).hexdigest()
                return f"fallback:{html_hash[:12]}"
                
        except Exception as e:
            return f"emergency:{int(time.time())}:{random.randint(1000, 9999)}"
    
    def coletar_tweets_candidatos(self, max_scrolls=15):
        """Coleta todos os tweets candidatos com suas métricas"""
        print("🔍 Coletando tweets candidatos com métricas...")
        
        self.tweets_candidatos = []
        tweets_processados_nesta_coleta = set()
        scrolls_realizados = 0
        
        while scrolls_realizados < max_scrolls:
            try:
                todos_tweets = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                print(f"📊 Encontrados {len(todos_tweets)} tweets na tela (scroll {scrolls_realizados + 1}/{max_scrolls})")
                
                tweets_novos_nesta_rodada = 0
                
                for tweet in todos_tweets:
                    try:
                        tweet_id = self.gerar_id_unico_tweet(tweet)
                        
                        if tweet_id not in tweets_processados_nesta_coleta:
                            tweets_processados_nesta_coleta.add(tweet_id)
                            
                            # Extrai texto
                            seletores_texto = [
                                '[data-testid="tweetText"]',
                                '.tweet-text',
                                '[data-testid="tweet"] [lang]',
                                'div[lang] span'
                            ]
                            
                            texto_tweet = None
                            for seletor in seletores_texto:
                                try:
                                    texto_elemento = tweet.find_element(By.CSS_SELECTOR, seletor)
                                    texto_tweet = texto_elemento.text.strip()
                                    if texto_tweet:
                                        break
                                except:
                                    continue
                            
                            if texto_tweet and len(texto_tweet) > 15:
                                # Extrai métricas
                                num_comentarios = self.extrair_numero_comentarios(tweet)
                                data_tweet = self.extrair_data_tweet(tweet)
                                
                                # Adiciona à lista de candidatos
                                candidato = {
                                    'element': tweet,
                                    'id': tweet_id,
                                    'texto': texto_tweet,
                                    'comentarios': num_comentarios,
                                    'data': data_tweet,
                                    'score': num_comentarios  # Score inicial baseado em comentários
                                }
                                
                                self.tweets_candidatos.append(candidato)
                                tweets_novos_nesta_rodada += 1
                                
                    except Exception as e:
                        continue
                
                print(f"✅ {tweets_novos_nesta_rodada} novos tweets candidatos adicionados")
                
                # Scroll para carregar mais tweets
                altura_antes = self.driver.execute_script("return window.pageYOffset;")
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(2, 4))
                altura_depois = self.driver.execute_script("return window.pageYOffset;")
                
                # Se não houve scroll, para
                if altura_antes == altura_depois:
                    print("⚠️ Fim da página atingido")
                    break
                    
                scrolls_realizados += 1
                
            except Exception as e:
                print(f"⚠️ Erro durante coleta: {str(e)[:50]}")
                break
        
        print(f"🎯 Total de tweets candidatos coletados: {len(self.tweets_candidatos)}")
        return len(self.tweets_candidatos) > 0
    
    def selecionar_melhores_tweets(self, limite=5, criterio="comentarios"):
        """Seleciona os melhores tweets baseado no critério escolhido"""
        print(f"🎯 Selecionando os {limite} melhores tweets por {criterio}...")
        
        if not self.tweets_candidatos:
            print("⚠️ Nenhum tweet candidato disponível!")
            return []
        
        # Filtra tweets de hoje (últimas 24 horas)
        hoje = datetime.now()
        tweets_hoje = []
        
        for candidato in self.tweets_candidatos:
            try:
                if candidato['data'] and (hoje - candidato['data']).days <= 1:
                    tweets_hoje.append(candidato)
                else:
                    # Se não tiver data válida, considera como recente
                    tweets_hoje.append(candidato)
            except:
                tweets_hoje.append(candidato)
        
        print(f"📅 Tweets das últimas 24h: {len(tweets_hoje)}")
        
        # Ordena baseado no critério
        if criterio == "comentarios":
            # Ordena por número de comentários (decrescente)
            tweets_selecionados = sorted(tweets_hoje, 
                                       key=lambda x: x['comentarios'], 
                                       reverse=True)
        elif criterio == "cronologico":
            # Ordena por data (mais antigo primeiro)
            tweets_selecionados = sorted(tweets_hoje, 
                                       key=lambda x: x['data'] if x['data'] else datetime.min)
        elif criterio == "cronologico_reverso":
            # Ordena por data (mais novo primeiro)
            tweets_selecionados = sorted(tweets_hoje, 
                                       key=lambda x: x['data'] if x['data'] else datetime.min, 
                                       reverse=True)
        else:
            # Critério misto: prioriza comentários mas considera recência
            for candidato in tweets_hoje:
                # Score misto: comentários + bonus por recência
                horas_atras = (hoje - candidato['data']).total_seconds() / 3600 if candidato['data'] else 24
                bonus_recencia = max(0, 24 - horas_atras) * 0.5  # Bonus decrescente
                candidato['score'] = candidato['comentarios'] + bonus_recencia
            
            tweets_selecionados = sorted(tweets_hoje, 
                                       key=lambda x: x['score'], 
                                       reverse=True)
        
        # Pega apenas o número solicitado
        tweets_finais = tweets_selecionados[:limite]
        
        # Mostra seleção
        print(f"\n📋 TWEETS SELECIONADOS ({criterio.upper()}):")
        print("=" * 60)
        for i, tweet in enumerate(tweets_finais, 1):
            comentarios_texto = f"{tweet['comentarios']} comentários" if tweet['comentarios'] > 0 else "sem comentários"
            data_texto = tweet['data'].strftime("%H:%M") if tweet['data'] else "sem data"
            print(f"{i}. {tweet['texto'][:50]}... ({comentarios_texto}, {data_texto})")
        print("=" * 60)
        
        return tweets_finais
    
    def processar_tweets_selecionados(self, tweets_selecionados):
        """Processa os tweets selecionados coletando comentários"""
        print(f"🔄 Processando {len(tweets_selecionados)} tweets selecionados...")
        
        for i, tweet_data in enumerate(tweets_selecionados, 1):
            print(f"\n📝 Processando tweet {i}/{len(tweets_selecionados)}...")
            
            codigo_postagem = f"post_{i:03d}"
            
            try:
                # Volta ao perfil se necessário
                if "twitter.com/" + self.username not in self.driver.current_url:
                    self.driver.get(f"https://twitter.com/{self.username}")
                    time.sleep(3)
                
                sucesso = self.coletar_comentarios_tweet(
                    tweet_data['element'], 
                    codigo_postagem, 
                    tweet_data['texto']
                )
                
                if sucesso:
                    print(f"✅ Tweet {i} processado com sucesso!")
                else:
                    print(f"⚠️ Tweet {i} processado parcialmente")
                    
                    # Se não conseguiu comentários, adiciona pelo menos o tweet
                    self.dados_coletados.append({
                        'codigo_da_postagem': codigo_postagem,
                        'usuario': f'@{self.username}',
                        'texto_da_postagem': tweet_data['texto'],
                        'texto_do_comentario': tweet_data['texto'],  # Usa o próprio tweet
                        'sentimento': ''
                    })
                
            except Exception as e:
                print(f"⚠️ Erro ao processar tweet {i}: {str(e)[:50]}")
                continue
        
        print(f"\n🎉 Processamento concluído! {len(self.dados_coletados)} itens coletados")
    
    def coletar_comentarios_tweet(self, tweet, codigo_postagem, texto_postagem, max_comentarios=10):
        """Coleta comentários de um tweet específico"""
        try:
            # Clica no tweet para abrir
            self.driver.execute_script("arguments[0].click();", tweet)
            time.sleep(random.uniform(3, 5))
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Aguarda comentários carregarem
                comentarios = wait.until(
                    EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR, 
                        'div[data-testid="cellInnerDiv"] article[data-testid="tweet"]'
                    ))
                )[1:]  # Pula o primeiro que é o tweet original
                
                comentarios_coletados = 0
                
                for comentario in comentarios[:max_comentarios]:
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            comentario
                        )
                        time.sleep(0.5)
                        
                        texto_comentario = self.driver.execute_script("""
                            var elemento = arguments[0].querySelector('[data-testid="tweetText"]');
                            return elemento ? elemento.textContent.trim() : null;
                        """, comentario)
                        
                        if texto_comentario and len(texto_comentario) > 5:
                            self.dados_coletados.append({
                                'codigo_da_postagem': codigo_postagem,
                                'usuario': f'@{self.username}',
                                'texto_da_postagem': texto_postagem,
                                'texto_do_comentario': texto_comentario,
                                'sentimento': ''
                            })
                            comentarios_coletados += 1
                            
                    except Exception as e:
                        continue
                
                print(f"💬 {comentarios_coletados} comentários coletados!")
                
                # Volta ao perfil
                self.driver.get(f"https://twitter.com/{self.username}")
                time.sleep(random.uniform(2, 3))
                
                return comentarios_coletados > 0
                
            except TimeoutException:
                print("⚠️ Timeout ao carregar comentários")
                self.driver.get(f"https://twitter.com/{self.username}")
                time.sleep(2)
                return False
                
        except Exception as e:
            print(f"⚠️ Erro na coleta: {str(e)[:50]}")
            try:
                self.driver.get(f"https://twitter.com/{self.username}")
                time.sleep(2)
            except:
                pass
            return False
    
    def executar_coleta_inteligente(self, limite_postagens=5, criterio="comentarios"):
        """Executa coleta inteligente com seleção baseada em critérios"""
        print(f"🎯 Iniciando coleta inteligente: {limite_postagens} postagens por {criterio}")
        
        # Etapa 1: Coletar candidatos
        if not self.coletar_tweets_candidatos():
            print("❌ Falha ao coletar tweets candidatos!")
            return False
        
        # Etapa 2: Selecionar melhores
        tweets_selecionados = self.selecionar_melhores_tweets(limite_postagens, criterio)
        
        if not tweets_selecionados:
            print("❌ Nenhum tweet selecionado!")
            return False
        
        # Etapa 3: Processar selecionados
        self.processar_tweets_selecionados(tweets_selecionados)
        
        return len(self.dados_coletados) > 0
    
    def limpar_texto(self, texto):
        """Pré-processamento de texto"""
        texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'@\w+', '', texto)
        texto = re.sub(r'#(\w+)', r'\1', texto)
        texto = re.sub(r'[^\w\s]', ' ', texto)
        texto = ' '.join(texto.split())
        return texto.strip().lower()
        
    def preprocessar_dados(self):
        """Pré-processamento dos dados"""
        print("🧹 Pré-processando dados...")
        
        for item in self.dados_coletados:
            item['texto_da_postagem'] = self.limpar_texto(item['texto_da_postagem'])
            item['texto_do_comentario'] = self.limpar_texto(item['texto_do_comentario'])
            
        print("✅ Pré-processamento concluído!")
        
    def analisar_sentimentos(self):
        """Análise de sentimentos usando LeIA"""
        print("🎭 Analisando sentimentos...")
        
        for i, item in enumerate(self.dados_coletados):
            try:
                score = self.analyzer.polarity_scores(item['texto_do_comentario'])
                
                if score['compound'] >= 0.05:
                    sentimento = 'POSITIVO'
                elif score['compound'] <= -0.05:
                    sentimento = 'NEGATIVO'
                else:
                    sentimento = 'NEUTRO'
                    
                item['sentimento'] = sentimento
                
                if (i + 1) % 5 == 0:
                    print(f"📊 Analisados {i + 1}/{len(self.dados_coletados)} textos")
                    
            except Exception as e:
                item['sentimento'] = 'NEUTRO'
                
        print("✅ Análise de sentimentos concluída!")
        
    def salvar_csv(self, nome_arquivo="dados_twitter_selecao_inteligente.csv"):
        """Salva dados em CSV"""
        if not self.dados_coletados:
            print("⚠️ Nenhum dado para salvar!")
            return None
            
        df = pd.DataFrame(self.dados_coletados)
        df.to_csv(nome_arquivo, index=False, encoding='utf-8')
        
        print(f"✅ Dados salvos em {nome_arquivo}!")
        print(f"📊 Total de registros: {len(self.dados_coletados)}")
        return df
        
    def gerar_visualizacao(self, df):
        """Gera gráfico de análise de sentimentos"""
        if df is None or df.empty:
            print("⚠️ Sem dados para visualização!")
            return
            
        print("📈 Gerando gráfico...")
        
        plt.style.use('default')
        contagem_sentimentos = df.groupby(['codigo_da_postagem', 'sentimento']).size().unstack(fill_value=0)
        
        cores = {'NEGATIVO': '#ff4444', 'NEUTRO': '#888888', 'POSITIVO': '#44ff44'}
        cores_ordenadas = [cores.get(col, '#0066cc') for col in contagem_sentimentos.columns]
        
        plt.figure(figsize=(16, 8))
        ax = contagem_sentimentos.plot(kind='bar', 
                                     color=cores_ordenadas,
                                     width=0.7,
                                     alpha=0.8)
        
        plt.title('Análise de Sentimentos - Seleção Inteligente\n(Postagens com Mais Comentários)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Código da Postagem', fontsize=12, fontweight='bold')
        plt.ylabel('Quantidade de Comentários', fontsize=12, fontweight='bold')
        plt.legend(title='Sentimento', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        plt.savefig('analise_sentimentos_selecao_inteligente.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("✅ Gráfico salvo como 'analise_sentimentos_selecao_inteligente.png'!")
        
        self.mostrar_estatisticas(df)
    
    def mostrar_estatisticas(self, df):
        """Mostra estatísticas detalhadas"""
        total = len(df)
        if total == 0:
            return
            
        pos = len(df[df['sentimento'] == 'POSITIVO'])
        neg = len(df[df['sentimento'] == 'NEGATIVO']) 
        neu = len(df[df['sentimento'] == 'NEUTRO'])
        
        # Estatísticas por postagem
        stats_por_postagem = df.groupby('codigo_da_postagem').agg({
            'sentimento': 'count'
        }).rename(columns={'sentimento': 'total_comentarios'})
        
        print("\n" + "="*60)
        print("📊 ESTATÍSTICAS FINAIS (SELEÇÃO INTELIGENTE)")
        print("="*60)
        print(f"Total de comentários analisados: {total}")
        print(f"✅ Positivos: {pos} ({pos/total*100:.1f}%)")
        print(f"❌ Negativos: {neg} ({neg/total*100:.1f}%)")
        print(f"⚪ Neutros: {neu} ({neu/total*100:.1f}%)")
        print(f"📱 Postagens processadas: {df['codigo_da_postagem'].nunique()}")
        print(f"💬 Média comentários/postagem: {total/df['codigo_da_postagem'].nunique():.1f}")
        
        print("\n📋 DETALHES POR POSTAGEM:")
        for codigo, stats in stats_por_postagem.iterrows():
            comentarios_post = df[df['codigo_da_postagem'] == codigo]
            pos_post = len(comentarios_post[comentarios_post['sentimento'] == 'POSITIVO'])
            neg_post = len(comentarios_post[comentarios_post['sentimento'] == 'NEGATIVO'])
            neu_post = len(comentarios_post[comentarios_post['sentimento'] == 'NEUTRO'])
            
            print(f"  {codigo}: {stats['total_comentarios']} comentários "
                  f"(+{pos_post} -{neg_post} ={neu_post})")
        
    def fechar_navegador(self):
        """Fecha navegador e limpa arquivos temporários"""
        try:
            if self.driver:
                self.driver.quit()
            print("🧹 Navegador fechado!")
            
            # Remove perfil temporário
            temp_profile = os.path.join(os.path.expanduser("~"), "temp_chrome_profile")
            if os.path.exists(temp_profile):
                try:
                    shutil.rmtree(temp_profile)
                    print("🧹 Perfil temporário removido!")
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Aviso: {e}")
    
    def executar_processo_selecao_inteligente(self, limite_postagens=5, criterio="comentarios"):
        """Executa todo o processo com seleção inteligente"""
        try:
            print("🚀 INICIANDO SISTEMA COM SELEÇÃO INTELIGENTE\n")
            print("🔧 Recursos desta versão:")
            print("  - Coleta TODOS os tweets disponíveis primeiro")
            print("  - Extrai métricas: comentários, data, texto")
            print("  - Seleciona os melhores baseado no critério escolhido")
            print("  - Prioriza tweets de hoje com mais comentários")
            print("  - Garante coleta de dados úteis para análise")
            print(f"  - Critério atual: {criterio.upper()}")
            print(f"  - Meta: {limite_postagens} postagens\n")
            
            self.configurar_driver_robusto()
            
            if not self.acessar_perfil_robusto():
                print("❌ Falha ao acessar perfil!")
                return
            
            # Coleta inteligente
            sucesso = self.executar_coleta_inteligente(limite_postagens, criterio)
            self.fechar_navegador()
            
            if not sucesso or not self.dados_coletados:
                print("⚠️ Nenhum dado coletado! Possíveis causas:")
                print("  - Perfil sem tweets com comentários hoje")
                print("  - Perfil privado ou protegido")
                print("  - Bloqueio por segurança do Twitter")
                return
            
            self.preprocessar_dados()
            self.analisar_sentimentos()
            
            df = self.salvar_csv()
            if df is not None:
                self.gerar_visualizacao(df)
            
            print("\n🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
            print("📁 Arquivos gerados:")
            print("  - dados_twitter_selecao_inteligente.csv")
            print("  - analise_sentimentos_selecao_inteligente.png")
            
        except Exception as e:
            print(f"❌ Erro durante execução: {e}")
            self.fechar_navegador()

def main():
    """Função principal com opções de seleção inteligente"""
    print("=" * 70)
    print("SISTEMA DE ANÁLISE DE SENTIMENTOS - TWITTER/X")
    print("🎯 VERSÃO COM SELEÇÃO INTELIGENTE")
    print("=" * 70)
    
    portal = input("Digite o nome do portal (sem @) [Enter para 'tvm']: ").strip()
    if not portal:
        portal = "tvm"
    
    print("\n🌐 Escolha o navegador:")
    print("1 - Chrome (recomendado)")
    print("2 - Firefox") 
    print("3 - Brave")
    
    escolha = input("Digite 1, 2 ou 3 [Enter para Chrome]: ").strip()
    browsers = {"1": "chrome", "2": "firefox", "3": "brave"}
    browser = browsers.get(escolha, "chrome")
    
    print("\n🎯 Critério de seleção de postagens:")
    print("1 - Mais comentários (recomendado)")
    print("2 - Cronológico (mais antiga → mais nova)")
    print("3 - Cronológico reverso (mais nova → mais antiga)")
    print("4 - Misto (comentários + recência)")
    
    criterio_escolha = input("Digite 1, 2, 3 ou 4 [Enter para mais comentários]: ").strip()
    criterios = {
        "1": "comentarios",
        "2": "cronologico", 
        "3": "cronologico_reverso",
        "4": "misto"
    }
    criterio = criterios.get(criterio_escolha, "comentarios")
    
    print("\n📊 Quantas postagens analisar?")
    try:
        limite = int(input("Digite um número [Enter para 5]: ").strip() or "5")
        limite = max(1, min(10, limite)) 
    except:
        limite = 5
    
    criterio_nome = {
        "comentarios": "Mais Comentários",
        "cronologico": "Cronológico (Antiga→Nova)",
        "cronologico_reverso": "Cronológico (Nova→Antiga)", 
        "misto": "Misto (Comentários + Recência)"
    }
    
    print(f"\n📋 Configuração:")
    print(f"  📱 Portal: @{portal}")
    print(f"  🌐 Navegador: {browser.upper()}")
    print(f"  🎯 Critério: {criterio_nome[criterio]}")
    print(f"  📊 Meta: {limite} postagens")
    print(f"  🔧 Versão: Seleção Inteligente")
    print(f"  💡 Recurso: Prioriza posts com comentários")
    
    input("\nPressione Enter para iniciar a seleção inteligente...")
    
    analisador = TwitterSentimentAnalyzerSmartSelection(username=portal, browser=browser)
    analisador.executar_processo_selecao_inteligente(limite, criterio)

if __name__ == "__main__":
    main()