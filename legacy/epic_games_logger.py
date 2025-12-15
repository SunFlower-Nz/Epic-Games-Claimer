# -*- coding: utf-8 -*-
"""Epic Games Claimer logging configuration."""

from typing import Optional
import logging
import os
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    """Gerenciador de logs customizado."""
    
    def __init__(self, log_base_dir: Optional[str] = None):
        """
        Inicializa o logger.
        
        Args:
            log_base_dir: Diretório base para logs (padrão: C:/IA/Epic Games).
        """
        # Configura diretório base
        if log_base_dir is None:
            log_base_dir = os.getenv('LOG_BASE_DIR', 'C:/IA/Epic Games')
        
        self.log_base_dir = Path(log_base_dir)
        self._logger = self._setup_logger()
    
    def _get_log_file_path(self) -> Path:
        """
        Retorna o caminho do arquivo de log organizado por data.
        
        Returns:
            Path: Caminho absoluto para o arquivo de log.
        """
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        
        log_dir = self.log_base_dir / year / month
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return log_dir / f"{day}.txt"
        
    def _setup_logger(self) -> logging.Logger:
        """
        Configura o logger com formatação personalizada.
        
        Returns:
            Logger: Instância configurada do logger.
        """
        # Remove handlers existentes
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Formato do log
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Configura logging para arquivo e console
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(self._get_log_file_path(), encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger('EpicGamesClaimer')
        logger.info("=" * 80)
        logger.info("Epic Games Claimer - Nova Execução")
        logger.info("=" * 80)
        
        return logger
    
    @property
    def logger(self) -> logging.Logger:
        """
        Retorna o logger configurado.
        
        Returns:
            Logger: Instância do logger.
        """
        return self._logger