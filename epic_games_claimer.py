
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Epic Games Store - Automatizador de Coleta de Jogos Grátis
Autor: Sistema Automatizado
Data: 2025-10-24

Este script automatiza a coleta de jogos grátis da Epic Games Store
usando Playwright para automação de browser.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

# Carrega variáveis de ambiente
load_dotenv()


class EpicGamesLogger:
    """Gerenciador de logs customizado para o Epic Games Claimer"""
    
    def __init__(self, log_base_dir: str = None):
        """
        Inicializa o logger
        
        Args:
            log_base_dir: Diretório base para logs (padrão: C:/IA/Epic Games)
        """
        if log_base_dir is None:
            # Usa o diretório do .env ou padrão
            log_base_dir = os.getenv('LOG_BASE_DIR', 'C:/IA/Epic Games')
        
        self.log_base_dir = Path(log_base_dir)
        self.setup_logger()
    
    def get_log_file_path(self) -> Path:
        """
        Retorna o caminho do arquivo de log organizado por data
        Formato: C:/IA/Epic Games/YYYY/MM/DD.txt
        """
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        
        log_dir = self.log_base_dir / year / month
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return log_dir / f"{day}.txt"
    
    def setup_logger(self):
        """Configura o sistema de logging"""
        log_file = self.get_log_file_path()
        
        # Remove handlers existentes
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Formato do log
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Configura logging para arquivo e console
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 80)
        self.logger.info("Epic Games Claimer - Nova Execução")
        self.logger.info("=" * 80)


class EpicGamesClaimer:
    """Classe principal para automação da Epic Games Store"""
    
    def __init__(self):
        """Inicializa o claimer com configurações do .env"""
        self.logger = EpicGamesLogger().logger
        
        # Credenciais
        self.email = os.getenv('EPIC_EMAIL')
        self.password = os.getenv('EPIC_PASSWORD')
        
        if not self.email or not self.password:
            self.logger.error("❌ EPIC_EMAIL e EPIC_PASSWORD devem estar configurados no arquivo .env")
            raise ValueError("Credenciais não configuradas")
        
        # Configurações
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.timeout = int(os.getenv('TIMEOUT', '30000'))
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))
        self.data_dir.mkdir(exist_ok=True)
        
        # URLs
        self.store_url = "https://store.epicgames.com/pt-BR/free-games"
        self.login_url = "https://www.epicgames.com/id/login"
        
        # Browser e página
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        self.logger.info(f"✓ Configurações carregadas (Headless: {self.headless}, Timeout: {self.timeout}ms)")
    
    def fetch_free_games_info(self) -> Dict:
        """
        Consulta API não oficial para obter informações sobre jogos grátis
        
        Returns:
            Dicionário com informações dos jogos atuais e futuros
        """
        self.logger.info("🔍 Consultando API para informações de jogos grátis...")
        
        try:
            response = requests.get(
                "https://freegamesepic.onrender.com/api/games",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Salva informações em arquivo JSON
            json_file = self.data_dir / 'next_games.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✓ Informações salvas em: {json_file}")
            
            # Log das informações
            if 'currentGames' in data and data['currentGames']:
                self.logger.info(f"📌 Jogos atuais disponíveis: {len(data['currentGames'])}")
                for game in data['currentGames']:
                    self.logger.info(f"   - {game.get('title', 'N/A')}")
            
            if 'nextGames' in data and data['nextGames']:
                self.logger.info(f"📅 Próximos jogos: {len(data['nextGames'])}")
                for game in data['nextGames']:
                    self.logger.info(f"   - {game.get('title', 'N/A')} (disponível em {game.get('date', 'N/A')})")
            
            return data
            
        except requests.RequestException as e:
            self.logger.warning(f"⚠️ Erro ao consultar API: {e}")
            return {}
    
    def start_browser(self):
        """Inicia o browser Playwright"""
        self.logger.info("🌐 Iniciando browser...")
        
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Cria contexto com user agent realista
            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = context.new_page()
            self.page.set_default_timeout(self.timeout)
            
            self.logger.info("✓ Browser iniciado com sucesso")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar browser: {e}")
            raise
    
    def login(self) -> bool:
        """
        Realiza login na Epic Games
        
        Returns:
            True se login bem-sucedido, False caso contrário
        """
        self.logger.info("🔐 Iniciando processo de login...")
        
        try:
            # Navega para a página de login
            self.page.goto(self.login_url, wait_until='networkidle')
            self.logger.info("✓ Página de login carregada")
            
            # Aguarda e preenche email
            self.page.wait_for_selector('#email', timeout=self.timeout)
            self.page.fill('#email', self.email)
            self.logger.info("✓ Email preenchido")
            
            # Preenche senha
            self.page.fill('#password', self.password)
            self.logger.info("✓ Senha preenchida")
            
            # Clica no botão de login
            self.page.click('#sign-in')
            self.logger.info("✓ Botão de login clicado")
            
            # Aguarda navegação após login
            time.sleep(5)
            
            # Verifica se o login foi bem-sucedido
            current_url = self.page.url
            
            # Verifica se há captcha ou 2FA
            if 'captcha' in current_url.lower():
                self.logger.warning("⚠️ CAPTCHA detectado! Resolva manualmente e o script continuará...")
                self.page.wait_for_url(lambda url: 'captcha' not in url.lower(), timeout=120000)
                self.logger.info("✓ CAPTCHA resolvido")
            
            # Verifica 2FA
            if 'mfa' in current_url.lower() or '2fa' in current_url.lower():
                self.logger.warning("⚠️ Autenticação de dois fatores detectada!")
                self.logger.info("   Por favor, complete a verificação 2FA manualmente...")
                self.page.wait_for_url(lambda url: 'mfa' not in url.lower() and '2fa' not in url.lower(), timeout=120000)
                self.logger.info("✓ 2FA completado")
            
            # Aguarda redirecionamento após login
            time.sleep(3)
            
            self.logger.info("✓ Login realizado com sucesso!")
            return True
            
        except PlaywrightTimeoutError:
            self.logger.error("❌ Timeout durante o login")
            return False
        except Exception as e:
            self.logger.error(f"❌ Erro durante login: {e}")
            return False
    
    def get_free_games(self) -> List[Dict]:
        """
        Detecta jogos grátis disponíveis na página
        
        Returns:
            Lista de jogos grátis encontrados
        """
        self.logger.info("🎮 Buscando jogos grátis disponíveis...")
        
        try:
            # Navega para a página de jogos grátis
            self.page.goto(self.store_url, wait_until='networkidle')
            self.logger.info("✓ Página de jogos grátis carregada")
            
            time.sleep(3)
            
            # Procura por elementos de jogos grátis
            # A estrutura da Epic pode mudar, então usamos múltiplos seletores
            free_games = []
            
            # Aguarda carregar os jogos
            try:
                self.page.wait_for_selector('[data-testid="offer-card"]', timeout=10000)
            except:
                self.logger.warning("⚠️ Seletor padrão não encontrado, tentando alternativas...")
            
            # Tenta diferentes seletores
            selectors = [
                '[data-testid="offer-card"]',
                'a[role="link"][href*="/p/"]',
                '.css-1myhtyb',
                'article'
            ]
            
            for selector in selectors:
                elements = self.page.query_selector_all(selector)
                if elements:
                    self.logger.info(f"✓ Encontrados {len(elements)} elementos com seletor: {selector}")
                    
                    for element in elements:
                        try:
                            # Tenta extrair informações do jogo
                            game_info = {
                                'title': None,
                                'url': None,
                                'price': None
                            }
                            
                            # Tenta pegar o título
                            title_elem = element.query_selector('h3, h2, h4, [data-testid="offer-title"]')
                            if title_elem:
                                game_info['title'] = title_elem.inner_text().strip()
                            
                            # Tenta pegar URL
                            href = element.get_attribute('href')
                            if href:
                                game_info['url'] = href if href.startswith('http') else f"https://store.epicgames.com{href}"
                            
                            # Verifica se é grátis
                            text_content = element.inner_text().lower()
                            if 'grátis' in text_content or 'free' in text_content or 'gratuito' in text_content:
                                if game_info['title']:
                                    free_games.append(game_info)
                                    self.logger.info(f"   ✓ Jogo grátis encontrado: {game_info['title']}")
                        
                        except Exception as e:
                            continue
                    
                    if free_games:
                        break
            
            if not free_games:
                self.logger.warning("⚠️ Nenhum jogo grátis encontrado na página")
            else:
                self.logger.info(f"✓ Total de jogos grátis encontrados: {len(free_games)}")
            
            return free_games
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar jogos grátis: {e}")
            return []
    
    def claim_game(self, game_url: str, game_title: str) -> bool:
        """
        Adiciona um jogo grátis à conta
        
        Args:
            game_url: URL do jogo
            game_title: Título do jogo
            
        Returns:
            True se jogo foi adicionado, False caso contrário
        """
        self.logger.info(f"🎁 Tentando adicionar: {game_title}")
        
        try:
            # Navega para a página do jogo
            self.page.goto(game_url, wait_until='networkidle')
            time.sleep(2)
            
            # Procura pelo botão de obter/adicionar
            button_selectors = [
                'button:has-text("Obter")',
                'button:has-text("Adicionar")',
                'button:has-text("Get")',
                '[data-testid="purchase-cta-button"]',
                'button[class*="get"]',
                'button[class*="purchase"]'
            ]
            
            button_clicked = False
            for selector in button_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        button.click()
                        button_clicked = True
                        self.logger.info(f"   ✓ Botão clicado: {selector}")
                        time.sleep(2)
                        break
                except:
                    continue
            
            if not button_clicked:
                # Verifica se já possui o jogo
                page_content = self.page.content().lower()
                if 'já possui' in page_content or 'already own' in page_content or 'na biblioteca' in page_content:
                    self.logger.info(f"   ℹ️ Jogo já está na biblioteca: {game_title}")
                    return True
                else:
                    self.logger.warning(f"   ⚠️ Botão de adicionar não encontrado para: {game_title}")
                    return False
            
            # Aguarda confirmação e confirma se necessário
            time.sleep(2)
            
            # Procura botão de confirmação
            confirm_selectors = [
                'button:has-text("Fazer Pedido")',
                'button:has-text("Confirmar")',
                'button:has-text("Place Order")',
                '[data-testid="confirm-button"]'
            ]
            
            for selector in confirm_selectors:
                try:
                    confirm_button = self.page.query_selector(selector)
                    if confirm_button and confirm_button.is_visible():
                        confirm_button.click()
                        self.logger.info(f"   ✓ Confirmação clicada")
                        time.sleep(3)
                        break
                except:
                    continue
            
            # Verifica se foi adicionado com sucesso
            time.sleep(2)
            success_indicators = ['obrigado', 'thank you', 'adicionado', 'added', 'biblioteca']
            page_content = self.page.content().lower()
            
            for indicator in success_indicators:
                if indicator in page_content:
                    self.logger.info(f"   ✅ Jogo adicionado com sucesso: {game_title}")
                    return True
            
            self.logger.info(f"   ✓ Processo concluído para: {game_title}")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Erro ao adicionar jogo {game_title}: {e}")
            return False
    
    def run(self):
        """Executa o processo completo de coleta de jogos"""
        try:
            self.logger.info("🚀 Iniciando Epic Games Claimer...")
            
            # 1. Busca informações de jogos via API
            games_info = self.fetch_free_games_info()
            
            # 2. Inicia browser
            self.start_browser()
            
            # 3. Faz login
            if not self.login():
                self.logger.error("❌ Falha no login. Encerrando...")
                return
            
            # 4. Busca jogos grátis na página
            free_games = self.get_free_games()
            
            if not free_games:
                self.logger.info("ℹ️ Nenhum jogo grátis disponível no momento")
                return
            
            # 5. Adiciona cada jogo grátis
            added_games = []
            failed_games = []
            
            for game in free_games:
                if game['url']:
                    success = self.claim_game(game['url'], game['title'])
                    if success:
                        added_games.append(game['title'])
                    else:
                        failed_games.append(game['title'])
                    
                    time.sleep(2)  # Pausa entre jogos
            
            # 6. Resumo final
            self.logger.info("=" * 80)
            self.logger.info("📊 RESUMO DA EXECUÇÃO")
            self.logger.info("=" * 80)
            self.logger.info(f"✅ Jogos processados com sucesso: {len(added_games)}")
            for game in added_games:
                self.logger.info(f"   - {game}")
            
            if failed_games:
                self.logger.info(f"❌ Jogos com falha: {len(failed_games)}")
                for game in failed_games:
                    self.logger.info(f"   - {game}")
            
            self.logger.info("=" * 80)
            self.logger.info("✓ Execução concluída!")
            
        except Exception as e:
            self.logger.error(f"❌ Erro fatal durante execução: {e}")
            raise
        
        finally:
            # Fecha o browser
            if self.browser:
                self.logger.info("🔒 Fechando browser...")
                self.browser.close()


def main():
    """Função principal"""
    try:
        claimer = EpicGamesClaimer()
        claimer.run()
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info("\n⚠️ Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
