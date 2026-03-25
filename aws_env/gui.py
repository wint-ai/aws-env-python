import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional

from aws_env.config import AppConfig, save_config, load_config
from aws_env.credentials import update_credentials, read_credentials, validate_credentials, SESSION_DURATION
from aws_env.services import ecr_login, docker_login, helm_login

log = logging.getLogger(__name__)

AWS_REGIONS = [
    "eu-west-1", "eu-west-2", "eu-central-1",
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
]


class TextHandler(logging.Handler):
    """Routes log records into a tkinter ScrolledText widget."""

    def __init__(self, text_widget: scrolledtext.ScrolledText):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._append, msg)

    def _append(self, msg: str):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("WINT AWS environment setup")
        self.root.geometry("720x480")
        self.root.minsize(600, 350)
        self.config = load_config()
        self.expiry_timer: Optional[threading.Timer] = None
        self._build_ui()
        self._load_config_to_ui()
        self._setup_logging()

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Row 1: Region + Profile + ECR
        row1 = ttk.Frame(main)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Region:").pack(side=tk.LEFT)
        self.region_var = tk.StringVar()
        self.region_combo = ttk.Combobox(
            row1, textvariable=self.region_var, values=AWS_REGIONS, width=15
        )
        self.region_combo.pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(row1, text="Profile:").pack(side=tk.LEFT)
        self.profile_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.profile_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="ECR Registry:").pack(side=tk.LEFT, padx=(15, 0))
        self.ecr_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.ecr_var, width=40).pack(side=tk.LEFT, padx=5)

        # Row 2: MFA + Login
        row2 = ttk.Frame(main)
        row2.pack(fill=tk.X, pady=6)

        ttk.Label(row2, text="MFA Token:").pack(side=tk.LEFT)
        self.mfa_var = tk.StringVar()
        vcmd = (self.root.register(self._validate_mfa), "%P")
        self.mfa_entry = ttk.Entry(
            row2, textvariable=self.mfa_var, width=10,
            font=("Consolas", 12), validate="key", validatecommand=vcmd,
        )
        self.mfa_entry.pack(side=tk.LEFT, padx=5)
        self.mfa_entry.bind("<KeyRelease>", self._on_mfa_key)

        self.login_btn = ttk.Button(row2, text="Login", command=self._on_login)
        self.login_btn.pack(side=tk.LEFT, padx=10)

        # Row 3: Checkboxes
        row3 = ttk.Frame(main)
        row3.pack(fill=tk.X, pady=2)

        self.new_creds_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="New Creds", variable=self.new_creds_var).pack(side=tk.LEFT, padx=5)

        self.docker_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="Docker", variable=self.docker_var).pack(side=tk.LEFT, padx=5)

        self.helm_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="Helm", variable=self.helm_var).pack(side=tk.LEFT, padx=5)

        self.auto_enter_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="Auto Enter", variable=self.auto_enter_var).pack(side=tk.LEFT, padx=5)

        self.audio_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="Audio", variable=self.audio_var).pack(side=tk.LEFT, padx=5)

        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(row3, text="Debug", variable=self.debug_var, command=self._toggle_debug).pack(
            side=tk.LEFT, padx=5
        )

        # Row 4: Save / Load
        row4 = ttk.Frame(main)
        row4.pack(fill=tk.X, pady=2)

        ttk.Button(row4, text="Save Config", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(row4, text="Load Config", command=self._load_config).pack(side=tk.LEFT, padx=5)

        # Log area
        self.log_text = scrolledtext.ScrolledText(
            main, state="disabled", wrap=tk.WORD, font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # ── Logging ──────────────────────────────────────────────────

    def _setup_logging(self):
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG if self.config.debug_enabled else logging.INFO)

    # ── Config ↔ UI ──────────────────────────────────────────────

    def _load_config_to_ui(self):
        self.region_var.set(self.config.aws_region)
        self.profile_var.set(self.config.aws_profile)
        self.ecr_var.set(self.config.ecr_registry)
        self.new_creds_var.set(self.config.new_creds_enabled)
        self.docker_var.set(self.config.docker_enabled)
        self.helm_var.set(self.config.helm_enabled)
        self.auto_enter_var.set(self.config.auto_enter)
        self.audio_var.set(self.config.audio_enabled)
        self.debug_var.set(self.config.debug_enabled)

    def _ui_to_config(self) -> AppConfig:
        return AppConfig(
            aws_region=self.region_var.get(),
            aws_profile=self.profile_var.get(),
            ecr_registry=self.ecr_var.get(),
            new_creds_enabled=self.new_creds_var.get(),
            debug_enabled=self.debug_var.get(),
            docker_enabled=self.docker_var.get(),
            helm_enabled=self.helm_var.get(),
            audio_enabled=self.audio_var.get(),
            auto_enter=self.auto_enter_var.get(),
        )

    def _save_config(self):
        save_config(self._ui_to_config())
        log.info("Configuration saved")

    def _load_config(self):
        self.config = load_config()
        self._load_config_to_ui()
        log.info("Configuration loaded")

    # ── MFA input ────────────────────────────────────────────────

    @staticmethod
    def _validate_mfa(new_value: str) -> bool:
        stripped = new_value.replace(" ", "")
        return stripped == "" or (len(stripped) <= 6 and stripped.isdigit())

    def _on_mfa_key(self, _event):
        if self.login_btn.instate(["disabled"]):
            return
        token = self.mfa_var.get().replace(" ", "")
        if self.auto_enter_var.get() and len(token) == 6 and token.isdigit():
            self._on_login()

    # ── Login flow ───────────────────────────────────────────────

    def _on_login(self):
        token = self.mfa_var.get().replace(" ", "").strip()
        if self.new_creds_var.get() and (len(token) != 6 or not token.isdigit()):
            log.error("Invalid MFA token — must be 6 digits")
            return
        self.login_btn.configure(state="disabled")
        self.mfa_entry.configure(state="disabled")
        threading.Thread(target=self._exec_login, args=(token,), daemon=True).start()

    def _exec_login(self, token_code: str):
        try:
            region = self.region_var.get()
            profile = self.profile_var.get()
            registry = self.ecr_var.get()
            session_creds = None

            if self.new_creds_var.get():
                log.info("Generating new session credentials for profile '%s' in %s...", profile, region)
                session_creds = update_credentials(profile, region, token_code)
                if not session_creds:
                    log.error("Failed to generate session credentials")
                    self._play_sound(success=False)
                    return
            else:
                log.info("Reading existing credentials for profile '%s'...", profile)
                session_creds = read_credentials(profile)
                if not session_creds:
                    log.error("No credentials found for profile '%s'", profile)
                    self._play_sound(success=False)
                    return

            ecr_creds = ecr_login(session_creds, region)

            need_ecr = self.docker_var.get() or self.helm_var.get()
            if not ecr_creds and need_ecr:
                log.error("ECR authorization failed — cannot proceed with Docker/Helm login")
                self._play_sound(success=False)
                return
            elif not ecr_creds:
                log.warning("No ECR credentials obtained")

            if self.docker_var.get() and ecr_creds:
                for cred in ecr_creds:
                    docker_login(cred, registry)

            if self.helm_var.get() and ecr_creds:
                for cred in ecr_creds:
                    helm_login(cred, registry)

            log.info("Login complete")
            self._play_sound(success=True)
            self._schedule_expiry_reminder()

        except Exception as e:
            log.error("Login failed: %s", e)
            log.debug("Stack trace:", exc_info=True)
            self._play_sound(success=False)
        finally:
            self.root.after(0, self._reset_ui)

    def _reset_ui(self):
        self.login_btn.configure(state="normal")
        self.mfa_entry.configure(state="normal")
        self.mfa_var.set("")
        self.mfa_entry.focus()

    # ── Expiry reminder ──────────────────────────────────────────

    def _schedule_expiry_reminder(self):
        if self.expiry_timer:
            self.expiry_timer.cancel()
        remind_seconds = SESSION_DURATION - (30 * 60)
        self.expiry_timer = threading.Timer(remind_seconds, self._on_expiry_reminder)
        self.expiry_timer.daemon = True
        self.expiry_timer.start()

    def _on_expiry_reminder(self):
        log.warning("AWS session credentials will expire in ~30 minutes")
        self._play_sound(success=False)

    # ── Audio ────────────────────────────────────────────────────

    def _play_sound(self, success: bool):
        if not self.audio_var.get():
            return
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK if success else winsound.MB_ICONHAND)
        except ImportError:
            pass  # non-Windows: skip

    # ── Debug toggle ─────────────────────────────────────────────

    def _toggle_debug(self):
        level = logging.DEBUG if self.debug_var.get() else logging.INFO
        logging.getLogger().setLevel(level)
        log.info("Debug mode %s", "enabled" if self.debug_var.get() else "disabled")
