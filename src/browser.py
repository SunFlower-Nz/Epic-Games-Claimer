"""
Browser management for Epic Games Claimer.

Provides a unified interface for browser automation with two modes:
1. Real Chrome via CDP (primary) — uses user's actual browser profile
   for minimal bot detection and natural fingerprint
2. Playwright Chromium (fallback) — launches a fresh browser with
   stealth patches when real Chrome is unavailable

The real Chrome approach drastically reduces CAPTCHA triggers because
hCaptcha's invisible mode sees a genuine browser fingerprint with
real cookies, extensions, and browsing history.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import Config
from .logger import Logger


class BrowserManager:
    """
    Manages browser lifecycle for claiming games.

    Tries to use the user's real Chrome browser via CDP first, falling
    back to Playwright's bundled Chromium with stealth patches.
    """

    # Anti-detection args for Playwright fallback
    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
    ]

    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self._logger = logger
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._chrome_process: subprocess.Popen | None = None
        self._temp_profile_dir: Path | None = None
        self._using_real_chrome = False

    # =========================================================================
    # Public API
    # =========================================================================

    def get_page(
        self,
        playwright: Any,
        *,
        access_token: str = "",
        headless: bool = False,
    ) -> Any:
        """
        Get a ready-to-use browser page.

        Tries real Chrome via CDP first (if enabled), then falls back to
        Playwright Chromium with stealth.  In both modes the EPIC_EG1
        cookie is injected so that the browser session is authenticated
        even if the profile's own cookies are encrypted / missing.

        Args:
            playwright: A Playwright instance (from ``sync_playwright``).
            access_token: EPIC_EG1 token for session authentication.
            headless: Run headless (only affects fallback mode).

        Returns:
            A Playwright Page object.
        """
        if self.config.use_real_chrome:
            try:
                page = self._launch_real_chrome(playwright)
                if page:
                    self._using_real_chrome = True
                    # Inject session cookie — the copied profile may lose
                    # cookies due to Chrome App-Bound Encryption.
                    if access_token:
                        self._inject_epic_cookies(access_token)
                    return page
            except Exception as e:
                self._logger.warning(f"Chrome real indisponível, usando Playwright: {e}")

        # Fallback: Playwright Chromium with stealth
        return self._launch_playwright_chromium(
            playwright, access_token=access_token, headless=headless
        )

    @property
    def is_real_chrome(self) -> bool:
        """Whether the current session is using the real Chrome browser."""
        return self._using_real_chrome

    def _inject_epic_cookies(self, access_token: str) -> None:
        """Inject EPIC_EG1 (and optionally cf_clearance) into the browser context."""
        if not self._context:
            return
        cookies: list[dict[str, str]] = [
            {
                "name": "EPIC_EG1",
                "value": access_token,
                "domain": ".epicgames.com",
                "path": "/",
            },
            {
                "name": "EPIC_LOCALE_COOKIE",
                "value": self.config.locale.replace("_", "-"),
                "domain": ".epicgames.com",
                "path": "/",
            },
        ]
        if self.config.cf_clearance:
            cookies.append(
                {
                    "name": "cf_clearance",
                    "value": self.config.cf_clearance,
                    "domain": ".epicgames.com",
                    "path": "/",
                }
            )
        try:
            self._context.add_cookies(cookies)
            self._logger.info("Cookies de sessão injetados no Chrome")
        except Exception as e:
            self._logger.warning(f"Falha ao injetar cookies: {e}")

    def close(self) -> None:
        """Close browser and clean up resources."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass

        # Don't kill Chrome if it was already running
        if self._chrome_process:
            try:
                self._chrome_process.terminate()
                self._chrome_process.wait(timeout=5)
            except Exception:
                pass
            self._chrome_process = None

        # Clean up temporary profile copy
        if self._temp_profile_dir and self._temp_profile_dir.exists():
            try:
                shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
            except Exception:
                pass
            self._temp_profile_dir = None

        self._browser = None
        self._context = None
        self._page = None
        self._using_real_chrome = False

    # =========================================================================
    # Real Chrome via CDP
    # =========================================================================

    def _launch_real_chrome(self, playwright: Any) -> Any | None:
        """
        Connect to real Chrome via Chrome DevTools Protocol.

        Chrome refuses CDP when ``--user-data-dir`` points to its own
        default location, so we copy the user's profile into a temp
        directory.  If Chrome is already running normally, it is killed
        first so the profile isn't locked during the copy.

        Returns:
            A Playwright Page, or None if connection fails.
        """
        port = self.config.chrome_cdp_port
        cdp_url = f"http://localhost:{port}"

        # Try connecting to an already-running Chrome with CDP
        if self._try_cdp_connect(playwright, cdp_url):
            return self._page

        # Chrome isn't listening on CDP — we need to (re)launch it
        chrome_exe = self._find_chrome_executable()
        if not chrome_exe:
            self._logger.warning("Chrome não encontrado no sistema")
            return None

        src_profile = self._get_chrome_user_data_dir()
        if not src_profile:
            self._logger.warning("Diretório de perfil do Chrome não encontrado")
            return None

        # Close any running Chrome that locks the profile directory
        if self._is_chrome_running():
            self._logger.info(
                "Chrome já está aberto — fechando para relançar com CDP..."
            )
            self._kill_chrome_processes()
            for _ in range(15):
                if not self._is_chrome_running():
                    break
                time.sleep(1)
            else:
                self._logger.warning("Chrome não fechou a tempo")
                return None
            time.sleep(2)

        # Copy profile into a temp dir — Chrome refuses CDP on its
        # default User Data directory
        profile = self.config.chrome_profile  # e.g. "Default"
        tmp_base = Path(tempfile.mkdtemp(prefix="epic_chrome_"))
        self._temp_profile_dir = tmp_base  # cleaned up in close()
        src_profile_sub = src_profile / profile

        self._logger.info(f"Copiando perfil '{profile}' para {tmp_base}...")
        try:
            dst_profile = tmp_base / profile
            shutil.copytree(
                src_profile_sub,
                dst_profile,
                ignore=shutil.ignore_patterns(
                    "Cache", "Code Cache", "GPUCache", "Service Worker",
                    "CacheStorage", "blob_storage", "IndexedDB",
                    "File System", "GCM Store",
                ),
                dirs_exist_ok=True,
            )
            # Also copy essential top-level files (Local State, etc.)
            for fname in ("Local State",):
                src_file = src_profile / fname
                if src_file.exists():
                    shutil.copy2(src_file, tmp_base / fname)
        except Exception as e:
            self._logger.warning(f"Falha ao copiar perfil: {e}")
            return None

        self._logger.info(f"Iniciando Chrome real com CDP na porta {port}...")

        cmd = [
            str(chrome_exe),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={tmp_base}",
            f"--profile-directory={profile}",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        try:
            self._chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            # Wait for Chrome to start and open CDP port
            for i in range(25):
                time.sleep(1)
                if self._try_cdp_connect(playwright, cdp_url):
                    return self._page
                if i == 9:
                    self._logger.debug("Ainda aguardando Chrome iniciar...")

            self._logger.warning("Chrome não respondeu no CDP após 25s")
            return None

        except FileNotFoundError:
            self._logger.warning(f"Chrome não encontrado: {chrome_exe}")
            return None
        except Exception as e:
            self._logger.warning(f"Falha ao iniciar Chrome: {e}")
            return None

    def _is_chrome_running(self) -> bool:
        """Check if any Chrome process is currently running."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "chrome.exe" in result.stdout.lower()
        except Exception:
            return False

    def _kill_chrome_processes(self) -> None:
        """Gracefully terminate all Chrome processes."""
        try:
            subprocess.run(
                ["taskkill", "/IM", "chrome.exe", "/F"],
                capture_output=True,
                timeout=10,
            )
            time.sleep(2)
        except Exception as e:
            self._logger.debug(f"Erro ao fechar Chrome: {e}")

    def _try_cdp_connect(self, playwright: Any, cdp_url: str) -> bool:
        """
        Try to connect to Chrome via CDP.

        Returns:
            True if connected successfully.
        """
        try:
            self._browser = playwright.chromium.connect_over_cdp(cdp_url)
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
                pages = self._context.pages
                if pages:
                    self._page = pages[0]
                else:
                    self._page = self._context.new_page()
            else:
                self._context = self._browser.new_context()
                self._page = self._context.new_page()

            self._logger.info("✅ Conectado ao Chrome real via CDP")
            return True
        except Exception:
            # CDP not available yet
            self._browser = None
            self._context = None
            self._page = None
            return False

    def _find_chrome_executable(self) -> Path | None:
        """Find Chrome executable on the system."""
        # User-configured path
        if self.config.chrome_exe_path:
            custom = Path(self.config.chrome_exe_path)
            if custom.exists():
                return custom

        # Common Windows paths
        candidates = [
            Path(os.environ.get("PROGRAMFILES", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
        ]

        # Also check if chrome is on PATH
        chrome_on_path = shutil.which("chrome") or shutil.which("google-chrome")
        if chrome_on_path:
            candidates.insert(0, Path(chrome_on_path))

        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate

        return None

    def _get_chrome_user_data_dir(self) -> Path | None:
        """Get Chrome user data directory."""
        local_appdata = os.getenv("LOCALAPPDATA", "")
        if not local_appdata:
            return None

        chrome_path = Path(local_appdata) / "Google" / "Chrome" / "User Data"
        return chrome_path if chrome_path.exists() else None

    # =========================================================================
    # Playwright Chromium Fallback
    # =========================================================================

    def _launch_playwright_chromium(
        self,
        playwright: Any,
        *,
        access_token: str = "",
        headless: bool = False,
    ) -> Any:
        """
        Launch Playwright's bundled Chromium with stealth patches.

        Injects session cookies and applies anti-detection measures.

        Args:
            playwright: Playwright instance.
            access_token: EPIC_EG1 token to inject as cookie.
            headless: Run without visible window.

        Returns:
            A Playwright Page object.
        """
        self._logger.info("Iniciando Chromium via Playwright (fallback)...")

        self._browser = playwright.chromium.launch(
            headless=headless,
            slow_mo=300,
            args=self.STEALTH_ARGS,
        )

        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale=self.config.locale,
        )

        # Inject session cookies
        if access_token:
            cookies: list[dict[str, str]] = [
                {
                    "name": "EPIC_EG1",
                    "value": access_token,
                    "domain": ".epicgames.com",
                    "path": "/",
                }
            ]
            if self.config.cf_clearance:
                cookies.append(
                    {
                        "name": "cf_clearance",
                        "value": self.config.cf_clearance,
                        "domain": ".epicgames.com",
                        "path": "/",
                    }
                )
            self._context.add_cookies(cookies)

        self._page = self._context.new_page()

        # Apply stealth patches
        try:
            from playwright_stealth import Stealth

            stealth = Stealth()
            stealth.apply_stealth_sync(self._page)
        except ImportError:
            self._logger.debug("playwright-stealth não disponível, prosseguindo sem stealth")

        self._using_real_chrome = False
        return self._page
