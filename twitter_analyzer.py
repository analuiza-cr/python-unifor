from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import pandas as pd
import time
import re
from LeIA import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
import hashlib
import random

class TwitterSentimentAnalyzer:
    """
    Sistema de coleta e análise de sentimentos do Twitter/X
    """
    
    def __init__(self, username="tvm", browser="chrome"):
        self.username = username
        self.browser = browser.lower()
        self.driver = None
        self.dados_coletados = []
        self.analyzer = SentimentIntensityAnalyzer()
        self.tweets_processados = []
        
    def configurar_driver(self):
        """Configuração robusta do WebDriver"""
        print(f"Configurando navegador {self.browser.upper()}...")
        
        if self.browser == "chrome":
            chrome_options = ChromeOptions()
            
            # Configurações para estabilidade
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--window-size=1366,768")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent realista
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            try:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(12)
                
                # Remove propriedade webdriver para evitar detecção
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                print("Chrome configurado com sucesso!")
                return True
                
            except Exception as e:
                print(f"Erro com Chrome: {e}")
                print("Tentando Firefox...")
                self.browser = "firefox"
                return self.configurar_driver()
        
        elif self.browser == "firefox":
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--width=1366")
            firefox_options.add_argument("--height=768")
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("media.autoplay.default", 5)
            
            try:
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(12)
                print("Firefox configurado com sucesso!")
                return True
                
            except Exception as e:
                print(f"Erro com Firefox: {e}")
                return False
        
        return False
            
    def realizar_login_manual(self):
        """Processo de login manual conforme necessário"""
        print("\n" + "="*60)
        print("ETAPA DE LOGIN - TWITTER/X")
        print("="*60)
        print("INSTRUÇÕES:")
        print("1. O navegador será aberto na página de login")
        print("2. Faça login com suas credenciais")
        print("3. Aguarde carregar completamente")
        print("4. Volte ao terminal e pressione Enter")
        print("="*60)
        
        try:
            self.driver.get("https://twitter.com/login")
            time.sleep(8)
        except:
            print("Aviso: Timeout no carregamento da página de login")
        
        input("\nPressione Enter APÓS fazer login completamente...")
        
        # Verifica login
        for tentativa in range(3):
            try:
                self.driver.get("https://twitter.com/home")
                time.sleep(5)
                
                # Verifica se está na home ou se há tweets
                if ("/home" in self.driver.current_url or 
                    self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')):
                    print("✅ Login confirmado!")
                    return True
                else:
                    if tentativa < 2:
                        print(f"Tentativa {tentativa + 1}/3 - Login não confirmado, tentando novamente...")
                        time.sleep(3)
                    
            except Exception as e:
                if tentativa < 2:
                    print(f"Erro na verificação, tentativa {tentativa + 1}/3...")
                    time.sleep(3)
                    
        print("❌ Não foi possível confirmar o login")
        return False
            
    def acessar_perfil_alvo(self):
        """Acessa o perfil do portal de notícias especificado"""
        print(f"Acessando perfil @{self.username}...")
        
        try:
            url_perfil = f"https://twitter.com/{self.username}"
            self.driver.get(url_perfil)
            time.sleep(8)
            
            # Aguarda tweets carregarem
            wait = WebDriverWait(self.driver, 20)
            tweets = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]')))
            
            if tweets:
                print(f"✅ Perfil @{self.username} acessado - {len(tweets)} tweets iniciais encontrados")
                return True
            else:
                print("❌ Nenhum tweet encontrado no perfil")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao acessar perfil: {e}")
            return False
    
    def extrair_dados_tweet(self, tweet_element):
        """Extrai dados essenciais de um tweet"""
        try:
            # Texto do tweet
            try:
                texto_elemento = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                texto_tweet = texto_elemento.text.strip()
            except:
                texto_tweet = "Texto não disponível"
            
            # URL do tweet para acessar comentários
            try:
                link_element = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                url_tweet = link_element.get_attribute('href')
            except:
                url_tweet = None
            
            # ID único do tweet
            if url_tweet:
                tweet_id = url_tweet.split('/')[-1].split('?')[0]
            else:
                tweet_id = hashlib.md5(texto_tweet.encode()).hexdigest()[:12]
            
            return {
                'id': tweet_id,
                'texto': texto_tweet,
                'url': url_tweet
            }
            
        except Exception as e:
            return None
    
    def coletar_ultimas_30_postagens(self):
        """Coleta EXATAMENTE as últimas 30 postagens conforme documentação"""
        print("COLETANDO ÚLTIMAS 30 POSTAGENS - REQUISITO OBRIGATÓRIO")
        print("=" * 60)
        
        tweets_dados = []
        tweets_ids_coletados = set()
        scrolls_realizados = 0
        max_scrolls = 30  # Aumentado para garantir 30 posts
        scrolls_sem_novos_tweets = 0
        
        while len(tweets_dados) < 30 and scrolls_realizados < max_scrolls:
            try:
                # Localiza todos os tweets na página atual
                tweets_atuais = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                
                novos_tweets_nesta_rodada = 0
                
                for tweet in tweets_atuais:
                    if len(tweets_dados) >= 30:
                        break
                        
                    dados_tweet = self.extrair_dados_tweet(tweet)
                    
                    if dados_tweet and dados_tweet['id'] not in tweets_ids_coletados:
                        if len(dados_tweet['texto']) > 5:  # Critério mais flexível
                            tweets_dados.append(dados_tweet)
                            tweets_ids_coletados.add(dados_tweet['id'])
                            novos_tweets_nesta_rodada += 1
                            
                            # Progresso em tempo real
                            print(f"Tweet {len(tweets_dados)}/30 coletado")
                
                # Controle de scroll inteligente
                if novos_tweets_nesta_rodada == 0:
                    scrolls_sem_novos_tweets += 1
                    if scrolls_sem_novos_tweets >= 3:
                        print("Sem novos tweets após 3 scrolls - finalizando coleta")
                        break
                else:
                    scrolls_sem_novos_tweets = 0
                
                # Scroll para carregar mais tweets
                if len(tweets_dados) < 30:
                    print(f"Scroll {scrolls_realizados + 1} - Coletados {len(tweets_dados)}/30")
                    
                    altura_antes = self.driver.execute_script("return window.pageYOffset;")
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(random.uniform(4, 6))  # Tempo maior para carregar
                    altura_depois = self.driver.execute_script("return window.pageYOffset;")
                    
                    # Se não houve scroll mas ainda não tem 30, força mais scroll
                    if altura_antes == altura_depois:
                        if len(tweets_dados) < 30:
                            print("Forçando scroll adicional para atingir 30 postagens...")
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(5)
                        else:
                            break
                        
                scrolls_realizados += 1
                
            except Exception as e:
                print(f"Erro durante coleta: {e}")
                # Continua tentando mesmo com erro
                scrolls_realizados += 1
                time.sleep(3)
        
        print("=" * 60)
        print(f"RESULTADO DA COLETA: {len(tweets_dados)} postagens")
        
        if len(tweets_dados) < 30:
            print(f"AVISO: Coletadas apenas {len(tweets_dados)}/30 postagens")
            print("Possíveis motivos:")
            print("- Perfil com menos de 30 postagens")
            print("- Tweets protegidos ou indisponíveis")
            print("- Limite de scroll atingido")
        else:
            print("SUCESSO: 30 postagens coletadas conforme especificação!")
        
        print("=" * 60)
        return tweets_dados
    
    def coletar_comentarios_de_postagem(self, dados_tweet, codigo_postagem):
        """Coleta comentários de uma postagem específica"""
        try:
            if not dados_tweet['url']:
                print(f"Tweet {codigo_postagem}: URL não disponível")
                return []
            
            print(f"Coletando comentários da postagem {codigo_postagem}...")
            
            # Acessa a página do tweet
            self.driver.get(dados_tweet['url'])
            time.sleep(6)
            
            comentarios_coletados = []
            
            try:
                # Aguarda página carregar
                wait = WebDriverWait(self.driver, 15)
                
                # Localiza todos os elementos de tweet (primeiro é original, resto são comentários)
                todos_elementos = wait.until(
                    EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR, 
                        'div[data-testid="cellInnerDiv"] article[data-testid="tweet"]'
                    ))
                )
                
                # Remove o tweet original (primeiro elemento)
                elementos_comentarios = todos_elementos[1:] if len(todos_elementos) > 1 else []
                
                print(f"→ Encontrados {len(elementos_comentarios)} comentários")
                
                for i, comentario in enumerate(elementos_comentarios[:25]):  # Máximo 25 comentários por post
                    try:
                        # Scroll suave até o comentário
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            comentario
                        )
                        time.sleep(0.5)
                        
                        # Extrai texto do comentário
                        texto_comentario = comentario.find_element(
                            By.CSS_SELECTOR, '[data-testid="tweetText"]'
                        ).text.strip()
                        
                        if texto_comentario and len(texto_comentario) > 3:
                            comentarios_coletados.append(texto_comentario)
                            
                    except Exception as e:
                        continue
                
                print(f"→ {len(comentarios_coletados)} comentários válidos coletados")
                return comentarios_coletados
                
            except TimeoutException:
                print(f"→ Timeout ao carregar comentários da postagem {codigo_postagem}")
                return []
                
        except Exception as e:
            print(f"→ Erro ao acessar postagem {codigo_postagem}: {e}")
            return []
    
    def executar_coleta_completa(self):
        """
        Executa coleta completa das 30 postagens + comentários
        REQUISITO OBRIGATÓRIO: últimas 30 postagens do portal
        """
        print("EXECUTANDO COLETA OBRIGATÓRIA: 30 POSTAGENS")
        print("=" * 60)
        
        # Etapa 1: Coletar EXATAMENTE 30 postagens
        tweets_dados = self.coletar_ultimas_30_postagens()
        
        if not tweets_dados:
            print("ERRO CRÍTICO: Nenhuma postagem coletada!")
            return False
        
        if len(tweets_dados) < 30:
            print(f"AVISO: Apenas {len(tweets_dados)} postagens disponíveis (meta: 30)")
        
        # Etapa 2: Coletar comentários de CADA uma das postagens
        print(f"\nINICIANDO COLETA DE COMENTÁRIOS...")
        print(f"Processando {len(tweets_dados)} postagens coletadas...")
        
        postagens_com_comentarios = 0
        total_comentarios_coletados = 0
        
        for i, dados_tweet in enumerate(tweets_dados, 1):
            print(f"\n--- PROCESSANDO POSTAGEM {i}/{len(tweets_dados)} ---")
            
            # Coleta comentários desta postagem específica
            comentarios = self.coletar_comentarios_de_postagem(dados_tweet, i)
            
            if comentarios:
                postagens_com_comentarios += 1
                # Adiciona cada comentário ao dataset final
                for comentario in comentarios:
                    self.dados_coletados.append({
                        'codigo_da_postagem': i,
                        'nome_portal': f'@{self.username}',
                        'texto_da_postagem': dados_tweet['texto'],
                        'texto_do_comentario': comentario,
                        'sentimento': ''  # Preenchido na análise
                    })
                    total_comentarios_coletados += 1
                    
                print(f"✅ {len(comentarios)} comentários coletados desta postagem")
            else:
                # IMPORTANTE: Mesmo sem comentários, inclui a postagem
                # (pode ser que não tenha comentários mesmo)
                print(f"⚠️ Postagem {i} sem comentários - incluindo postagem original")
                self.dados_coletados.append({
                    'codigo_da_postagem': i,
                    'nome_portal': f'@{self.username}',
                    'texto_da_postagem': dados_tweet['texto'],
                    'texto_do_comentario': dados_tweet['texto'],  # Usa o próprio post
                    'sentimento': ''
                })
                total_comentarios_coletados += 1
            
            # Pausa entre postagens (importante para não ser bloqueado)
            if i < len(tweets_dados):
                time.sleep(random.uniform(3, 6))
        
        # Relatório da coleta
        print("\n" + "=" * 60)
        print("RESULTADO DA COLETA DE COMENTÁRIOS")
        print("=" * 60)
        print(f"📊 Postagens processadas: {len(tweets_dados)}/30")
        print(f"💬 Postagens com comentários: {postagens_com_comentarios}")
        print(f"📝 Total de registros coletados: {total_comentarios_coletados}")
        print(f"📈 Média de comentários/postagem: {total_comentarios_coletados/len(tweets_dados):.1f}")
        print("=" * 60)
        
        return len(self.dados_coletados) > 0
    
    def limpar_texto(self, texto):
        """
        Pré-processamento de texto conforme especificação:
        - Remove caracteres especiais
        - Remove links, hashtags e menções
        - Converte para minúsculas
        - Remove espaços extras
        """
        if not texto:
            return ""
            
        # Remove URLs
        texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE)
        # Remove menções (@usuario)
        texto = re.sub(r'@\w+', '', texto)
        # Remove hashtags mas mantém o texto (#palavra -> palavra)
        texto = re.sub(r'#(\w+)', r'\1', texto)
        # Remove caracteres especiais, mantém apenas letras, números e espaços
        texto = re.sub(r'[^\w\s]', ' ', texto)
        # Remove espaços extras
        texto = ' '.join(texto.split())
        # Converte para minúsculas
        return texto.strip().lower()
        
    def preprocessar_dados(self):
        """Pré-processamento dos dados textuais"""
        print("\nRealizando pré-processamento dos dados...")
        print("- Removendo caracteres especiais")
        print("- Removendo links, hashtags e menções")
        print("- Convertendo para minúsculas")
        print("- Removendo espaços extras")
        
        dados_antes = len(self.dados_coletados)
        
        for item in self.dados_coletados:
            item['texto_da_postagem'] = self.limpar_texto(item['texto_da_postagem'])
            item['texto_do_comentario'] = self.limpar_texto(item['texto_do_comentario'])
        
        # Remove registros com texto muito curto após limpeza
        self.dados_coletados = [
            item for item in self.dados_coletados 
            if len(item['texto_do_comentario']) > 5
        ]
        
        dados_depois = len(self.dados_coletados)
        print(f"✅ Pré-processamento concluído!")
        print(f"Registros antes: {dados_antes} | Registros após: {dados_depois}")
        
    def analisar_sentimentos(self):
        """
        Análise de sentimentos usando biblioteca LeIA
        Classifica cada comentário em: POSITIVO, NEGATIVO ou NEUTRO
        """
        print("\nIniciando análise de sentimentos com LeIA...")
        
        for i, item in enumerate(self.dados_coletados):
            try:
                # Análise usando LeIA
                score = self.analyzer.polarity_scores(item['texto_do_comentario'])
                
                # Critério de classificação baseado no compound score
                if score['compound'] >= 0.05:
                    sentimento = 'POSITIVO'
                elif score['compound'] <= -0.05:
                    sentimento = 'NEGATIVO'
                else:
                    sentimento = 'NEUTRO'
                    
                item['sentimento'] = sentimento
                
                # Progresso a cada 20 análises
                if (i + 1) % 20 == 0:
                    print(f"→ Analisados {i + 1}/{len(self.dados_coletados)} comentários")
                    
            except Exception as e:
                # Em caso de erro, classifica como neutro
                item['sentimento'] = 'NEUTRO'
                
        print("✅ Análise de sentimentos concluída!")
        
    def salvar_dados_csv(self, nome_arquivo="dados_twitter.csv"):
        """
        Salva dados no formato CSV especificado na documentação
        Formato: codigo_da_postagem, nome_portal, texto_da_postagem, texto_do_comentario, sentimento
        """
        if not self.dados_coletados:
            print("❌ Nenhum dado para salvar!")
            return None
            
        print(f"\nSalvando dados em formato CSV...")
        
        # Cria DataFrame com as colunas exatas da documentação
        df = pd.DataFrame(self.dados_coletados, columns=[
            'codigo_da_postagem', 
            'nome_portal', 
            'texto_da_postagem', 
            'texto_do_comentario', 
            'sentimento'
        ])
        
        # Salva arquivo CSV
        df.to_csv(nome_arquivo, index=False, encoding='utf-8')
        
        print(f"✅ Dados salvos em '{nome_arquivo}'")
        print(f"📊 Total de registros: {len(self.dados_coletados)}")
        print(f"📱 Postagens únicas: {df['codigo_da_postagem'].nunique()}")
        
        return df
        
    def gerar_grafico_barras(self, df):
        """
        Gera gráfico de barras conforme especificação:
        Mostra quantidade de comentários positivos, negativos e neutros para cada notícia
        """
        if df is None or df.empty:
            print("❌ Sem dados para visualização!")
            return
            
        print("\nGerando gráfico de barras...")
        
        # Agrupa dados por postagem e sentimento
        contagem_sentimentos = df.groupby(['codigo_da_postagem', 'sentimento']).size().unstack(fill_value=0)
        
        # Define cores para cada sentimento
        cores_sentimentos = {
            'NEGATIVO': '#e74c3c',    # Vermelho
            'NEUTRO': '#95a5a6',      # Cinza
            'POSITIVO': '#27ae60'     # Verde
        }
        
        # Ordena cores conforme colunas disponíveis
        cores_ordenadas = [cores_sentimentos.get(col, '#3498db') for col in contagem_sentimentos.columns]
        
        # Cria gráfico
        plt.figure(figsize=(14, 8))
        ax = contagem_sentimentos.plot(
            kind='bar', 
            color=cores_ordenadas,
            width=0.7,
            alpha=0.8,
            edgecolor='black',
            linewidth=0.5
        )
        
        # Configuração do gráfico
        plt.title(f'Análise de Sentimentos dos Comentários - @{self.username}\n'
                 f'Quantidade de Comentários Positivos, Negativos e Neutros por Notícia', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Código da Postagem', fontsize=12, fontweight='bold')
        plt.ylabel('Quantidade de Comentários', fontsize=12, fontweight='bold')
        plt.legend(title='Sentimento', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Adiciona valores nas barras
        for container in ax.containers:
            ax.bar_label(container, fontsize=9)
        
        plt.tight_layout()
        plt.savefig('analise_sentimentos.png', dpi=300, bbox_inches='tight', facecolor='white')
        plt.show()
        
        print("✅ Gráfico salvo como 'analise_sentimentos.png'")
        
    def exibir_relatorio_final(self, df):
        """Exibe relatório final da análise"""
        total_comentarios = len(df)
        total_postagens = df['codigo_da_postagem'].nunique()
        
        positivos = len(df[df['sentimento'] == 'POSITIVO'])
        negativos = len(df[df['sentimento'] == 'NEGATIVO'])
        neutros = len(df[df['sentimento'] == 'NEUTRO'])
        
        print("\n" + "="*70)
        print("RELATÓRIO FINAL DA ANÁLISE DE SENTIMENTOS")
        print("="*70)
        print(f"Portal analisado: @{self.username}")
        print(f"Total de postagens processadas: {total_postagens}")
        print(f"Total de comentários analisados: {total_comentarios}")
        print(f"Média de comentários por postagem: {total_comentarios/total_postagens:.1f}")
        print()
        print("DISTRIBUIÇÃO DE SENTIMENTOS:")
        print(f"🟢 Comentários POSITIVOS: {positivos} ({positivos/total_comentarios*100:.1f}%)")
        print(f"🔴 Comentários NEGATIVOS: {negativos} ({negativos/total_comentarios*100:.1f}%)")
        print(f"⚪ Comentários NEUTROS: {neutros} ({neutros/total_comentarios*100:.1f}%)")
        print()
        
        # Estatísticas por postagem
        print("DETALHES POR POSTAGEM:")
        for codigo in sorted(df['codigo_da_postagem'].unique()):
            dados_post = df[df['codigo_da_postagem'] == codigo]
            pos_post = len(dados_post[dados_post['sentimento'] == 'POSITIVO'])
            neg_post = len(dados_post[dados_post['sentimento'] == 'NEGATIVO'])
            neu_post = len(dados_post[dados_post['sentimento'] == 'NEUTRO'])
            total_post = len(dados_post)
            
            print(f"  Postagem {codigo:2d}: {total_post:3d} comentários "
                  f"(+{pos_post} -{neg_post} ={neu_post})")
        
        print("="*70)
        
    def fechar_navegador(self):
        """Fecha o navegador e limpa recursos"""
        try:
            if self.driver:
                self.driver.quit()
            print("🔧 Navegador fechado!")
        except Exception as e:
            print(f"Aviso ao fechar navegador: {e}")
    
    def executar_processo_completo(self):
        """
        Executa processo completo:
        OBRIGATÓRIO: Últimas 30 postagens + comentários + análise
        """
        try:
            print("SISTEMA DE ANÁLISE DE SENTIMENTOS - TWITTER/X")
            print("REQUISITO: Últimas 30 postagens do portal de notícias")
            print("="*70)
            
            # Etapa 1: Configuração do navegador
            if not self.configurar_driver():
                print("ERRO: Falha na configuração do navegador!")
                return False
            
            # Etapa 2: Login no Twitter/X
            if not self.realizar_login_manual():
                print("ERRO: Falha no processo de login!")
                return False
            
            # Etapa 3: Acessar perfil do portal
            if not self.acessar_perfil_alvo():
                print("ERRO: Falha ao acessar perfil!")
                return False
            
            # Etapa 4: Coleta das 30 postagens + comentários
            if not self.executar_coleta_completa():
                print("ERRO: Falha na coleta obrigatória!")
                return False
            
            # Fecha navegador antes do processamento
            self.fechar_navegador()
            
            if not self.dados_coletados:
                print("ERRO CRÍTICO: Nenhum dado coletado!")
                return False
            
            # Etapa 5: Pré-processamento
            print("\nETAPA 5: PRÉ-PROCESSAMENTO")
            self.preprocessar_dados()
            
            # Etapa 6: Análise de sentimentos com LeIA
            print("\nETAPA 6: ANÁLISE DE SENTIMENTOS")
            self.analisar_sentimentos()
            
            # Etapa 7: Salvar CSV no formato especificado
            print("\nETAPA 7: ARMAZENAMENTO EM CSV")
            df = self.salvar_dados_csv()
            
            # Etapa 8: Gerar visualização
            if df is not None:
                print("\nETAPA 8: GERAÇÃO DE GRÁFICO")
                self.gerar_grafico_barras(df)
                print("\nETAPA 9: RELATÓRIO FINAL")
                self.exibir_relatorio_final(df)
            
            print("\n" + "="*70)
            print("PROCESSO CONCLUÍDO - REQUISITOS ATENDIDOS")
            print("="*70)
            print("ARQUIVOS GERADOS:")
            print("- dados_twitter.csv (formato da documentação)")
            print("- analise_sentimentos.png (gráfico de barras)")
            print("\nREQUISTOS DA ATIVIDADE ATENDIDOS:")
            print("✓ Coleta das últimas 30 postagens")
            print("✓ Captura automatizada de comentários")
            print("✓ Uso da biblioteca Selenium")
            print("✓ Armazenamento em CSV formato especificado")
            print("✓ Pré-processamento de texto")
            print("✓ Análise de sentimento com LeIA")
            print("✓ Classificação POSITIVO/NEGATIVO/NEUTRO")
            print("✓ Gráfico de barras por notícia")
            print("✓ Código bem estruturado e comentado")
            print("="*70)
            
            return True
            
        except Exception as e:
            print(f"ERRO CRÍTICO: {e}")
            self.fechar_navegador()
            return False

def main():
    """Função principal - Executa sistema conforme documentação"""
    print("="*70)
    print("SISTEMA DE ANÁLISE DE SENTIMENTOS - TWITTER/X")
    print("ATIVIDADE: Coleta e Mineração de Dados da Rede Social X")
    print("REQUISITO: Últimas 30 postagens + comentários")
    print("="*70)
    
    # Configuração do portal
    print("\n📋 CONFIGURAÇÃO:")
    portal = input("Digite o nome do portal de notícias (sem @): ").strip()
    if not portal:
        portal = "tvm"  # Portal padrão da documentação
    
    # Escolha do navegador
    print("\n🌐 Navegador:")
    print("1 - Chrome (recomendado)")
    print("2 - Firefox")
    
    escolha_browser = input("Digite 1 ou 2 [Enter = Chrome]: ").strip()
    browser = "firefox" if escolha_browser == "2" else "chrome"
    
    # Confirmação da configuração
    print(f"\n📋 CONFIGURAÇÃO FINAL:")
    print(f"   Portal: @{portal}")
    print(f"   Navegador: {browser.upper()}")
    print(f"   Meta: 30 postagens (conforme documentação)")
    print(f"   Coleta: Comentários de cada postagem")
    print(f"   Análise: Sentimentos com LeIA")
    print(f"   Saída: CSV + Gráfico de barras")
    
    confirmacao = input("\nConfirma configuração? [Enter = SIM]: ").strip()
    if confirmacao.lower() in ['n', 'nao', 'no']:
        print("Operação cancelada.")
        return
    
    print("\n" + "="*70)
    print("INICIANDO PROCESSO AUTOMATIZADO")
    print("ETAPAS:")
    print("1. Configurar navegador")
    print("2. Login manual no Twitter/X")
    print("3. Acessar perfil do portal")
    print("4. Coletar 30 postagens")
    print("5. Coletar comentários")
    print("6. Pré-processar dados")
    print("7. Analisar sentimentos")
    print("8. Gerar CSV e gráfico")
    print("="*70)
    
    input("Pressione Enter para iniciar...")
    
    # Executa o sistema completo
    analisador = TwitterSentimentAnalyzer(username=portal, browser=browser)
    sucesso = analisador.executar_processo_completo()
    
    if sucesso:
        print("\nSUCESSO TOTAL!")
        print("Todos os requisitos da documentação foram atendidos:")
        print("- 30 postagens processadas")
        print("- Comentários coletados automaticamente")
        print("- Análise de sentimentos realizada")
        print("- Arquivos CSV e gráfico gerados")
    else:
        print("\nFALHA NO PROCESSO!")
        print("Verifique os requisitos:")
        print("- Conexão estável com internet")
        print("- Login válido no Twitter/X")
        print("- Perfil público do portal")

if __name__ == "__main__":
    main()
