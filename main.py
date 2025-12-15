#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Epic Games Claimer - CLI Entry Point.

Usage:
    python main.py              # Run once (claim free games)
    python main.py --schedule   # Run on schedule (daily at 12:00)
    python main.py --check      # Check for free games without claiming
    python main.py --status     # Show scheduler status
    python main.py --help       # Show help
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.logger import Logger
from src.claimer import EpicGamesClaimer
from src.scheduler import Scheduler


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog='Epic Games Claimer',
        description='🎮 Automatize a coleta de jogos grátis da Epic Games Store',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py              # Executar uma vez
  python main.py --schedule   # Executar em loop (12:00 diariamente)
  python main.py --check      # Apenas verificar jogos disponíveis
  
Configuração:
  Copie .env.example para .env e configure suas credenciais.
  Use scripts/get_cookies.py para extrair token do navegador.
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    
    group.add_argument(
        '--schedule', '-s',
        action='store_true',
        help='Executar em modo agendado (verifica diariamente às 12:00)'
    )
    
    group.add_argument(
        '--check', '-c',
        action='store_true',
        help='Apenas verificar jogos grátis disponíveis (sem resgatar)'
    )
    
    group.add_argument(
        '--status',
        action='store_true',
        help='Mostrar status do agendamento'
    )
    
    parser.add_argument(
        '--hour',
        type=int,
        default=None,
        help='Hora para agendamento (0-23, padrão: 12)'
    )
    
    parser.add_argument(
        '--minute',
        type=int,
        default=None,
        help='Minuto para agendamento (0-59, padrão: 0)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Epic Games Claimer v2.0.0'
    )
    
    return parser


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Initialize config (allows CLI overrides)
    config = Config()
    
    if args.hour is not None:
        config.schedule_hour = args.hour
    if args.minute is not None:
        config.schedule_minute = args.minute
    
    # Initialize logger
    logger = Logger(str(config.log_base_dir))
    
    try:
        if args.status:
            # Show scheduler status
            scheduler = Scheduler(config, logger)
            scheduler.check_schedule_status()
            return 0
        
        elif args.schedule:
            # Run in scheduled mode
            scheduler = Scheduler(config, logger)
            scheduler.run_scheduled()
            return 0
        
        elif args.check:
            # Check only mode
            claimer = EpicGamesClaimer(config, logger)
            games = claimer.check_only()
            
            if games:
                print(f"\n🎮 {len(games)} jogo(s) disponível(is) para resgate:")
                for game in games:
                    print(f"   • {game['title']}")
            else:
                print("\n✅ Nenhum jogo novo disponível")
            
            return 0
        
        else:
            # Run once (default)
            claimer = EpicGamesClaimer(config, logger)
            result = claimer.run()
            
            # Return success if no failures
            return 0 if result.failed == 0 else 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrompido pelo usuário")
        return 0
    except Exception as e:
        # Log stacktrace + config snapshot to facilitar reprodução
        logger.error("Erro fatal", exc=e, config=config)
        return 1


if __name__ == "__main__":
    sys.exit(main())
