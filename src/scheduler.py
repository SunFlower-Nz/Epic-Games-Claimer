"""
Scheduler for Epic Games Claimer.

Runs the claimer on a schedule (default: daily at 12:00).
Features:
- Configurable schedule time via environment
- Calculates next run time automatically
- Graceful shutdown handling
- Detailed logging of schedule events
"""

import signal
import sys
import time
from datetime import datetime, timedelta

from .claimer import EpicGamesClaimer
from .config import Config
from .logger import Logger


class Scheduler:
    """
    Scheduler that runs the claimer at configured times.

    Default schedule: Every day at 12:00 (noon).
    Configure via SCHEDULE_HOUR and SCHEDULE_MINUTE in .env.
    """

    def __init__(self, config: Config | None = None, logger: Logger | None = None):
        """
        Initialize scheduler.

        Args:
            config: Application configuration.
            logger: Logger instance.
        """
        self.config = config or Config()
        self._logger = logger or Logger(str(self.config.log_base_dir))
        self._running = True
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers."""

        def handler(signum, frame):
            self._logger.info("\n⏹️  Scheduler interrompido pelo usuário")
            self._running = False

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def get_next_run_time(self) -> datetime:
        """
        Calculate the next scheduled run time.

        Returns:
            Datetime of next run (today or tomorrow at scheduled time).
        """
        now = datetime.now()
        target = now.replace(
            hour=self.config.schedule_hour,
            minute=self.config.schedule_minute,
            second=0,
            microsecond=0,
        )

        # If target time has passed today, schedule for tomorrow
        if target <= now:
            target += timedelta(days=1)

        return target

    def time_until_next_run(self) -> timedelta:
        """
        Get time remaining until next scheduled run.

        Returns:
            Timedelta until next run.
        """
        return self.get_next_run_time() - datetime.now()

    def format_duration(self, td: timedelta) -> str:
        """
        Format timedelta as human-readable string.

        Args:
            td: Timedelta to format.

        Returns:
            Formatted string (e.g., "5h 30min").
        """
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}min"
        elif minutes > 0:
            return f"{minutes}min {seconds}s"
        else:
            return f"{seconds}s"

    def run_once(self) -> None:
        """
        Run the claimer once immediately.

        Useful for testing or manual runs.
        """
        self._logger.header("🎮 EPIC GAMES CLAIMER - EXECUÇÃO ÚNICA")

        try:
            claimer = EpicGamesClaimer(self.config, self._logger)
            result = claimer.run()

            self._logger.info("Execução concluída", claimed=result.claimed, failed=result.failed)

        except Exception as e:
            self._logger.error("Erro na execução", exc=e)

    def run_scheduled(self) -> None:
        """
        Run the claimer on schedule (loop until stopped).

        Executes immediately on start, then waits for next scheduled time.
        """
        self._logger.header("⏰ EPIC GAMES CLAIMER - MODO AGENDADO")
        self._logger.info(
            f"Horário configurado: {self.config.schedule_hour:02d}:{self.config.schedule_minute:02d}"
        )
        self._logger.info("Pressione Ctrl+C para parar\n")

        # Run immediately on start
        self._logger.info("Executando verificação inicial...")
        self._execute_claim()

        # Then run on schedule
        while self._running:
            next_run = self.get_next_run_time()
            wait_time = self.time_until_next_run()

            self._logger.info(
                f"Próxima execução: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(em {self.format_duration(wait_time)})"
            )

            # Wait until next run time (checking periodically for shutdown)
            self._wait_until(next_run)

            if self._running:
                self._execute_claim()

        self._logger.info("Scheduler encerrado")

    def _execute_claim(self) -> None:
        """Execute the claim process with error handling."""
        self._logger.info(f"\n{'─' * 50}")
        self._logger.info(f"Iniciando verificação: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Pre-step: Try to refresh session from Chrome cookies
        self._refresh_session_from_chrome()

        try:
            claimer = EpicGamesClaimer(self.config, self._logger)
            result = claimer.run()

            if result.claimed > 0:
                self._logger.success(f"🎉 {result.claimed} jogo(s) resgatado(s)!")
            elif result.failed > 0:
                self._logger.warning(f"{result.failed} falha(s) no resgate")
            else:
                self._logger.info("Nenhum jogo novo para resgatar")

        except Exception as e:
            self._logger.error("Erro durante execução", exc=e)

    def _refresh_session_from_chrome(self) -> None:
        """
        Pre-step: Refresh session from Chrome cookies if possible.

        This ensures we have the freshest tokens before each scheduled run,
        reducing the chance of token expiration during operation.
        """
        try:
            from .session_store import SessionStore

            session_store = SessionStore(self.config.session_file, self._logger)

            # Check if current session is still valid
            current_session = session_store.load()
            if current_session and current_session.is_valid():
                remaining = current_session.time_until_expiry()
                if remaining and remaining.total_seconds() > 3600:  # More than 1 hour left
                    self._logger.debug("Sessão ainda válida, pulando refresh do Chrome")
                    return

            # Try to refresh from Chrome
            self._logger.info("Tentando atualizar sessão do Chrome...")
            new_session = session_store.refresh_from_chrome(self.config)

            if new_session:
                self._logger.info("✅ Sessão atualizada do Chrome antes da execução")
            else:
                self._logger.debug("Não foi possível atualizar do Chrome, usando sessão existente")

        except Exception as e:
            self._logger.debug(f"Refresh Chrome falhou: {e}")

    def _wait_until(self, target: datetime) -> None:
        """
        Wait until target time, checking periodically for shutdown.

        Args:
            target: Target datetime to wait for.
        """
        while self._running and datetime.now() < target:
            # Sleep in intervals to allow for graceful shutdown
            remaining = (target - datetime.now()).total_seconds()
            base_min = 5 if getattr(self.config, "low_cpu_mode", False) else 1
            sleep_time = min(60, max(base_min, remaining))
            time.sleep(sleep_time)

    def check_schedule_status(self) -> None:
        """Log current schedule status."""
        next_run = self.get_next_run_time()
        wait_time = self.time_until_next_run()

        self._logger.subheader("STATUS DO AGENDAMENTO")
        self._logger.info(
            f"Horário agendado: {self.config.schedule_hour:02d}:{self.config.schedule_minute:02d}"
        )
        self._logger.info(f"Próxima execução: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        self._logger.info(f"Tempo restante:   {self.format_duration(wait_time)}")


def run_scheduler() -> None:
    """Entry point for scheduler."""
    scheduler = Scheduler()
    scheduler.run_scheduled()


def run_once() -> None:
    """Entry point for single run."""
    scheduler = Scheduler()
    scheduler.run_once()


if __name__ == "__main__":
    # Allow running directly
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_scheduler()
