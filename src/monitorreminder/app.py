from __future__ import annotations

"""Desktop UI for saving and restoring monitor-aware window profiles."""

import logging
import threading
import webbrowser
from functools import partial
from tkinter import Menu, StringVar

import customtkinter as ctk

from monitorreminder.config import load_config, save_config
from monitorreminder.constants import APP_NAME, APP_TAG, APP_VERSION, AUTHOR, COPYRIGHT_YEAR, MAX_PROFILES
from monitorreminder.i18n import TRANSLATIONS, translate
from monitorreminder.logging_utils import configure_logging
from monitorreminder.models import AppConfig, Profile
from monitorreminder.monitor_watcher import MonitorWatcher
from monitorreminder.paths import icon_path
from monitorreminder.window_manager import WindowManager

PAYPAL_URL = "https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN"


class MonitorReminderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.logger = configure_logging()
        self.config_data = load_config()
        self.window_manager = WindowManager(self.logger)
        self.watcher = MonitorWatcher(self.window_manager, self._handle_monitor_change)
        self.language = StringVar(value=self.config_data.ui.language)
        self.selected_profile = StringVar(value=str(self.config_data.ui.selected_profile))
        self.profile_name = StringVar(value=self.current_profile.name)
        self.auto_close_remaining = self.config_data.ui.auto_close_seconds
        self.status_text = StringVar(value=self.t("status_ready"))
        self.monitor_summary = StringVar(value=self._format_monitors())
        self._profile_cards: list[ctk.CTkButton] = []
        self._applying_saved_window_state = True
        self._geometry_save_job: str | None = None
        self._geometry_save_delay_ms = 280
        self._auto_restore_lock = threading.Lock()
        self._last_saved_geometry = (
            self.config_data.ui.width,
            self.config_data.ui.height,
            self.config_data.ui.pos_x,
            self.config_data.ui.pos_y,
            self.config_data.ui.window_state,
        )

        ctk.set_appearance_mode(self.config_data.ui.theme_mode)
        ctk.set_default_color_theme("dark-blue")

        self.title(APP_NAME)
        self.geometry(
            f"{self.config_data.ui.width}x{self.config_data.ui.height}+{self.config_data.ui.pos_x}+{self.config_data.ui.pos_y}"
        )
        self.minsize(1024, 700)
        if icon_path().exists():
            try:
                self.iconbitmap(icon_path())
            except Exception:
                self.logger.warning("Could not set application icon", exc_info=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_configure)
        self.bind_all("<Control-s>", lambda _event: self.save_selected_profile())
        self.bind_all("<Control-r>", lambda _event: self.restore_selected_profile())
        self.bind_all("<Control-q>", lambda _event: self._on_close())

        self._build_menu()
        self._build_layout()
        self._render_profile_cards()
        self._refresh_window_list()
        self.after(120, self._restore_saved_window_state)

        if self.config_data.ui.auto_start_monitoring:
            self.start_monitoring()
        if self.config_data.ui.auto_close_enabled:
            self.after(1000, self._auto_close_tick)

    @property
    def current_profile(self) -> Profile:
        selected_id = int(self.selected_profile.get())
        return next(profile for profile in self.config_data.profiles if profile.id == selected_id)

    def t(self, key: str) -> str:
        return translate(self.language.get(), key)

    def _build_menu(self) -> None:
        menu_bar = Menu(self)
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label=self.t("about"), command=self._show_about)
        menu_bar.add_cascade(label=self.t("about"), menu=help_menu)
        self.configure(menu=menu_bar)

    def _build_layout(self) -> None:
        title_font = ctk.CTkFont("Bahnschrift Semibold", 34, "bold")
        subtitle_font = ctk.CTkFont("Segoe UI", 14)
        section_font = ctk.CTkFont("Bahnschrift Semibold", 20, "bold")
        card_title_font = ctk.CTkFont("Segoe UI Semibold", 13, "bold")
        body_font = ctk.CTkFont("Segoe UI", 12)
        mono_font = ctk.CTkFont("Consolas", 11)

        hero_color = ("#d1ebff", "#081b2d")
        shell_color = ("#eef6ff", "#0f2135")
        info_color = ("#d6f4ef", "#0a2b24")
        automation_color = ("#e8f1ff", "#11263d")
        status_color = ("#d8eafc", "#0c2238")
        rail_color = ("#4bd0ff", "#1a86b8")
        border_color = ("#86c5eb", "#1b4262")
        selected_color = ("#24706c", "#24706c")
        selected_hover = ("#1f5c59", "#1f5c59")
        danger_color = ("#b03d3d", "#b03d3d")
        danger_hover = ("#912e2e", "#912e2e")

        # Hero area groups primary actions and global app controls.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.configure(fg_color=("#c9dbef", "#060d19"))

        hero = ctk.CTkFrame(self, fg_color=hero_color, corner_radius=28, border_width=1, border_color=border_color)
        hero.grid(row=0, column=0, padx=24, pady=(24, 12), sticky="nsew")
        hero.grid_columnconfigure(0, weight=3)
        hero.grid_columnconfigure(1, weight=2)

        neon_rail = ctk.CTkFrame(hero, fg_color=rail_color, corner_radius=10, height=8)
        neon_rail.grid(row=0, column=0, columnspan=2, padx=18, pady=(12, 2), sticky="ew")

        title = ctk.CTkLabel(hero, text=self.t("app_title"), font=title_font)
        title.grid(row=1, column=0, padx=24, pady=(20, 4), sticky="w")

        subtitle = ctk.CTkLabel(hero, text=self.t("subtitle"), font=subtitle_font)
        subtitle.grid(row=2, column=0, padx=24, pady=(0, 6), sticky="w")

        hero_badge = ctk.CTkLabel(
            hero,
            text=self.t("hero_badge"),
            font=body_font,
            fg_color=("#bfe6ff", "#143149"),
            corner_radius=14,
            padx=12,
            pady=4,
        )
        hero_badge.grid(row=3, column=0, padx=24, pady=(0, 18), sticky="w")

        controls = ctk.CTkFrame(hero, fg_color="transparent")
        controls.grid(row=1, column=1, rowspan=3, padx=24, pady=20, sticky="e")
        controls.grid_columnconfigure((0, 1), weight=1)

        language_menu = ctk.CTkOptionMenu(
            controls,
            values=list(TRANSLATIONS.keys()),
            variable=self.language,
            command=self._change_language,
            fg_color=("#2a7196", "#1f5f85"),
            button_color=("#205f80", "#1a506c"),
            button_hover_color=("#1a506c", "#153e56"),
            width=140,
        )
        language_menu.grid(row=0, column=0, padx=(0, 12), pady=(0, 10), sticky="ew")

        beer_button = ctk.CTkButton(
            controls,
            text=self.t("buy_beer"),
            command=lambda: webbrowser.open(PAYPAL_URL),
            fg_color=("#24706c", "#24706c"),
            hover_color=("#1f5c59", "#1f5c59"),
        )
        beer_button.grid(row=0, column=1, pady=(0, 10), sticky="ew")

        support_caption = ctk.CTkLabel(controls, text=self.t("support_caption"), font=ctk.CTkFont("Segoe UI", 11))
        support_caption.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        self.monitoring_button = ctk.CTkButton(
            controls,
            text=self.t("start_monitoring"),
            command=self._toggle_monitoring,
            fg_color=("#2d87a1", "#1e6c8b"),
            hover_color=("#246c84", "#17566d"),
        )
        self.monitoring_button.grid(row=2, column=0, padx=(0, 12), sticky="ew")

        exit_button = ctk.CTkButton(
            controls,
            text=self.t("exit"),
            command=self._on_close,
            fg_color=danger_color,
            hover_color=danger_hover,
        )
        exit_button.grid(row=2, column=1, sticky="ew")

        # Main body separates profile management from monitor and automation details.
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=24, pady=12, sticky="nsew")
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(body, corner_radius=24, fg_color=shell_color, border_width=1, border_color=border_color)
        left_panel.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        profiles_label = ctk.CTkLabel(left_panel, text=self.t("profiles"), font=section_font)
        profiles_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.profile_cards_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.profile_cards_container.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="nsew")
        self.profile_cards_container.grid_columnconfigure((0, 1), weight=1)

        actions = ctk.CTkFrame(left_panel, fg_color="transparent")
        actions.grid(row=2, column=0, padx=20, pady=(4, 20), sticky="ew")
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        save_button = ctk.CTkButton(actions, text=self.t("save_profile"), command=self.save_selected_profile)
        save_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        restore_button = ctk.CTkButton(actions, text=self.t("restore_profile"), command=self.restore_selected_profile)
        restore_button.grid(row=0, column=1, padx=4, sticky="ew")

        rename_button = ctk.CTkButton(actions, text=self.t("rename_profile"), command=self.rename_selected_profile)
        rename_button.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        rename_frame = ctk.CTkFrame(left_panel, fg_color=("#d9e8f8", "#17304b"), corner_radius=18)
        rename_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        rename_frame.grid_columnconfigure(0, weight=1)

        rename_entry = ctk.CTkEntry(rename_frame, textvariable=self.profile_name, placeholder_text=self.t("rename_hint"), height=34)
        rename_entry.grid(row=0, column=0, padx=14, pady=14, sticky="ew")
        rename_entry.bind("<Return>", lambda _event: self.rename_selected_profile())
        rename_entry.bind("<FocusOut>", lambda _event: self.rename_selected_profile())

        right_panel = ctk.CTkFrame(body, corner_radius=24, fg_color=shell_color, border_width=1, border_color=border_color)
        right_panel.grid(row=0, column=1, padx=(12, 0), sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(6, weight=1)

        monitor_label = ctk.CTkLabel(right_panel, text=self.t("monitor_layout"), font=section_font)
        monitor_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        monitor_hint = ctk.CTkLabel(right_panel, text=self.t("monitor_hint"), font=body_font)
        monitor_hint.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        monitor_value = ctk.CTkLabel(right_panel, textvariable=self.monitor_summary, justify="left", anchor="w", font=mono_font)
        monitor_value.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="ew")

        # How-to card — concise instructions for the end user.
        howto_card = ctk.CTkFrame(right_panel, fg_color=info_color, corner_radius=18)
        howto_card.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="ew")
        howto_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            howto_card,
            text=self.t("howto_title"),
            font=card_title_font,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
        ctk.CTkLabel(
            howto_card,
            text=self.t("howto_steps"),
            justify="left",
            anchor="w",
            wraplength=320,
            font=body_font,
        ).grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")

        automation_card = ctk.CTkFrame(right_panel, fg_color=automation_color, corner_radius=18)
        automation_card.grid(row=4, column=0, padx=20, pady=(0, 16), sticky="ew")
        automation_card.grid_columnconfigure(0, weight=1)

        automation_title = ctk.CTkLabel(automation_card, text=self.t("watcher"), font=card_title_font, anchor="w")
        automation_title.grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        auto_start_checkbox = ctk.CTkCheckBox(
            automation_card,
            text=self.t("auto_start"),
            command=self._toggle_auto_start,
        )
        auto_start_checkbox.grid(row=1, column=0, padx=16, pady=(4, 8), sticky="w")
        if self.config_data.ui.auto_start_monitoring:
            auto_start_checkbox.select()

        auto_close_checkbox = ctk.CTkCheckBox(
            automation_card,
            text=self.t("auto_close"),
            command=self._toggle_auto_close,
        )
        auto_close_checkbox.grid(row=2, column=0, padx=16, pady=8, sticky="w")
        if self.config_data.ui.auto_close_enabled:
            auto_close_checkbox.select()

        self.auto_close_entry = ctk.CTkEntry(automation_card)
        self.auto_close_entry.insert(0, str(self.config_data.ui.auto_close_seconds))
        self.auto_close_entry.grid(row=3, column=0, padx=16, pady=(8, 6), sticky="ew")
        self.auto_close_entry.bind("<KeyRelease>", self._persist_auto_close_seconds)

        auto_close_hint = ctk.CTkLabel(automation_card, text=self.t("auto_close_hint"), font=ctk.CTkFont("Segoe UI", 11))
        auto_close_hint.grid(row=4, column=0, padx=16, pady=(0, 12), sticky="w")

        windows_label = ctk.CTkLabel(right_panel, text=self.t("windows"), font=section_font)
        windows_label.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="w")

        windows_hint = ctk.CTkLabel(right_panel, text=self.t("windows_hint"), font=body_font)
        windows_hint.grid(row=6, column=0, padx=20, pady=(0, 8), sticky="w")

        self.window_list = ctk.CTkTextbox(
            right_panel,
            height=160,
            font=mono_font,
            fg_color=("#dcefff", "#0b1c2d"),
            border_width=1,
            border_color=("#79b8df", "#1f4d70"),
        )
        self.window_list.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.window_list.configure(state="disabled")

        # Status bar keeps feedback visible without interrupting the user flow.
        status_bar = ctk.CTkFrame(self, corner_radius=18, fg_color=status_color)
        status_bar.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_columnconfigure(1, weight=0)

        self.status_label = ctk.CTkLabel(status_bar, textvariable=self.status_text, anchor="w", font=body_font)
        self.status_label.grid(row=0, column=0, padx=16, pady=10, sticky="ew")

        self.countdown_label = ctk.CTkLabel(status_bar, text=self._countdown_text(), anchor="e", font=body_font)
        self.countdown_label.grid(row=0, column=1, padx=16, pady=10, sticky="e")

        self.version_label = ctk.CTkLabel(status_bar, text=f"{self.t('version')}: {APP_TAG}", font=body_font)
        self.version_label.grid(row=0, column=2, padx=(0, 16), pady=10, sticky="e")

        self._profile_selected_color = selected_color
        self._profile_selected_hover = selected_hover

    def _render_profile_cards(self) -> None:
        for widget in self.profile_cards_container.winfo_children():
            widget.destroy()
        self._profile_cards.clear()
        for index, profile in enumerate(self.config_data.profiles[:MAX_PROFILES], start=1):
            row = (index - 1) // 2
            column = (index - 1) % 2
            text = f"{profile.id}. {profile.name}"
            if profile.created_at:
                text = f"{text}\n{profile.created_at}"
            button = ctk.CTkButton(
                self.profile_cards_container,
                text=text,
                height=84,
                command=partial(self._select_profile, profile.id),
            )
            button.grid(row=row, column=column, padx=8, pady=8, sticky="ew")
            self._profile_cards.append(button)
        self._highlight_selected_profile()

    def _highlight_selected_profile(self) -> None:
        selected_id = int(self.selected_profile.get())
        for button, profile in zip(self._profile_cards, self.config_data.profiles, strict=False):
            if profile.id == selected_id:
                button.configure(fg_color=self._profile_selected_color, hover_color=self._profile_selected_hover)
            else:
                button.configure(fg_color=("#2f7f96", "#1b5f79"), hover_color=("#276a80", "#154e64"))

    def _select_profile(self, profile_id: int) -> None:
        self.selected_profile.set(str(profile_id))
        self.config_data.ui.selected_profile = profile_id
        self.profile_name.set(self.current_profile.name)
        self._highlight_selected_profile()
        save_config(self.config_data)

    def save_selected_profile(self) -> None:
        """Capture the current visible windows into the selected profile and immediately
        restore them so every window moves to its saved position."""
        try:
            # Apply any name typed in the rename field before capturing so the
            # user does not need to click a separate Rename button.
            profile = self.current_profile
            pending_name = self.profile_name.get().strip()[:40]
            if pending_name and pending_name != profile.name:
                profile.name = pending_name
            updated = self.window_manager.capture_profile(profile)
            self._replace_profile(updated)
            self.profile_name.set(updated.name)
            self._render_profile_cards()
            self._refresh_window_list()
            # Restore immediately so all windows are aligned to the captured positions.
            summary = self.window_manager.restore_profile(updated)
            mode_label = self.t(f"restore_mode_{summary.restore_mode}")
            self._set_status(self.t("status_saved_restored").format(
                mode=mode_label,
                restored=summary.restored_count,
                aligned=summary.already_aligned_count,
            ))
        except Exception:
            self.logger.exception("Profile capture failed")
            self._set_status(self.t("status_error"))

    def restore_selected_profile(self) -> None:
        """Restore the saved windows for the selected profile."""
        try:
            summary = self.window_manager.restore_profile(self.current_profile)
            # Translate the mode name (exact / proportional) for the status bar.
            mode_label = self.t(f"restore_mode_{summary.restore_mode}")
            if summary.is_already_aligned:
                self._set_status(self.t("status_already_applied").format(
                    profile=summary.profile_name, mode=mode_label
                ))
            else:
                self._set_status(
                    self.t("status_restored_detail").format(
                        mode=mode_label,
                        restored=summary.restored_count,
                        aligned=summary.already_aligned_count,
                        missing=summary.missing_count,
                        failed=summary.failed_count,
                    )
                )
        except Exception:
            self.logger.exception("Profile restore failed")
            self._set_status(self.t("status_error"))

    def rename_selected_profile(self) -> None:
        """Rename the selected profile and persist the change immediately."""
        new_name = self.profile_name.get().strip()[:40] or self.current_profile.name
        updated = self.current_profile
        updated.name = new_name
        self._replace_profile(updated)
        self._render_profile_cards()
        self._set_status(f"{self.t('profile_name')}: {new_name}")

    def start_monitoring(self) -> None:
        self.watcher.start()
        self.monitoring_button.configure(text=self.t("stop_monitoring"))
        self._set_status(self.t("status_monitoring"))

    def stop_monitoring(self) -> None:
        self.watcher.stop()
        self.monitoring_button.configure(text=self.t("start_monitoring"))
        self._set_status(self.t("status_stopped"))

    def _toggle_monitoring(self) -> None:
        if self.watcher.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def _toggle_auto_start(self) -> None:
        self.config_data.ui.auto_start_monitoring = not self.config_data.ui.auto_start_monitoring
        save_config(self.config_data)

    def _toggle_auto_close(self) -> None:
        self.config_data.ui.auto_close_enabled = not self.config_data.ui.auto_close_enabled
        self.auto_close_remaining = self.config_data.ui.auto_close_seconds
        save_config(self.config_data)
        self.countdown_label.configure(text=self._countdown_text())
        if self.config_data.ui.auto_close_enabled:
            self.after(1000, self._auto_close_tick)

    def _persist_auto_close_seconds(self, _event: object | None = None) -> None:
        raw = self.auto_close_entry.get().strip()
        if not raw.isdigit():
            return
        value = max(5, min(3600, int(raw)))
        self.config_data.ui.auto_close_seconds = value
        self.auto_close_remaining = value
        save_config(self.config_data)
        self.countdown_label.configure(text=self._countdown_text())

    def _change_language(self, language: str) -> None:
        """Persist language changes and restart the UI so all labels refresh consistently."""
        self.config_data.ui.language = language
        self._cancel_scheduled_geometry_save()
        self._persist_window_geometry(force=True)
        self.stop_monitoring()
        self.destroy()
        run()

    def _show_about(self) -> None:
        about_window = ctk.CTkToplevel(self)
        about_window.title(self.t("about"))
        about_window.geometry("440x250+300+180")
        about_window.transient(self)
        about_window.grid_columnconfigure(0, weight=1)
        about_window.grid_rowconfigure((0, 1, 2, 3), weight=0)
        ctk.CTkLabel(
            about_window,
            text=f"{APP_NAME} {APP_TAG}",
            font=ctk.CTkFont("Segoe UI Semibold", 22, "bold"),
        ).grid(row=0, column=0, padx=20, pady=(24, 8), sticky="n")
        ctk.CTkLabel(about_window, text=f"Creado por {AUTHOR}").grid(row=1, column=0, pady=4)
        ctk.CTkLabel(about_window, text=f"{COPYRIGHT_YEAR} Derechos Reservados").grid(row=2, column=0, pady=4)
        ctk.CTkButton(
            about_window,
            text=self.t("buy_beer"),
            command=lambda: webbrowser.open(PAYPAL_URL),
            fg_color=("#24706c", "#24706c"),
            hover_color=("#1f5c59", "#1f5c59"),
        ).grid(row=3, column=0, padx=20, pady=(18, 16), sticky="n")

    def _set_status(self, value: str) -> None:
        self.status_text.set(value)

    def _handle_monitor_change(self, _signature: str) -> None:
        self.after(0, self._refresh_monitors)

    def _refresh_monitors(self) -> None:
        self.monitor_summary.set(self._format_monitors())
        self._set_status(self.t("status_monitoring"))
        # Auto-restore the selected profile in a background thread so the GUI
        # doesn't freeze while windows are being repositioned.
        if not self._auto_restore_lock.acquire(blocking=False):
            self._set_status(self.t("status_monitoring_busy"))
            return
        profile = self.current_profile
        threading.Thread(target=self._auto_restore_after_change, args=(profile,), daemon=True).start()

    def _auto_restore_after_change(self, profile: Profile) -> None:
        """Run restore after a monitor layout change (called from background thread)."""
        try:
            summary = self.window_manager.restore_profile(profile)
            mode_label = self.t(f"restore_mode_{summary.restore_mode}")
            self.after(0, lambda: self._set_status(
                self.t("status_auto_restored").format(
                    mode=mode_label,
                    restored=summary.restored_count,
                    aligned=summary.already_aligned_count,
                    missing=summary.missing_count,
                    failed=summary.failed_count,
                )
            ))
        except Exception:
            self.logger.exception("Auto-restore after monitor change failed")
            self.after(0, lambda: self._set_status(self.t("status_error")))
        finally:
            self._auto_restore_lock.release()

    def _refresh_window_list(self) -> None:
        """Show a compact preview of the windows saved in the active profile."""
        lines = []
        for item in self.current_profile.windows[:40]:
            lines.append(f"{item.process_name} | {item.title}")
        if not lines:
            lines = ["-"]
        self.window_list.configure(state="normal")
        self.window_list.delete("1.0", "end")
        self.window_list.insert("1.0", "\n".join(lines))
        self.window_list.configure(state="disabled")

    def _format_monitors(self) -> str:
        monitors = self.window_manager.monitor_snapshots()
        return "\n".join(
            f"{monitor.name}: {monitor.width}x{monitor.height} @ ({monitor.x}, {monitor.y})"
            for monitor in monitors
        )

    def _replace_profile(self, updated_profile: Profile) -> None:
        for index, profile in enumerate(self.config_data.profiles):
            if profile.id == updated_profile.id:
                self.config_data.profiles[index] = updated_profile
                break
        save_config(self.config_data)

    def _auto_close_tick(self) -> None:
        if not self.config_data.ui.auto_close_enabled:
            self.countdown_label.configure(text=self._countdown_text())
            return
        self.auto_close_remaining -= 1
        self.countdown_label.configure(text=self._countdown_text())
        if self.auto_close_remaining <= 0:
            self._on_close()
            return
        self.after(1000, self._auto_close_tick)

    def _countdown_text(self) -> str:
        if not self.config_data.ui.auto_close_enabled:
            return ""
        return f"{self.config_data.ui.auto_close_seconds}s / {self.auto_close_remaining}s"

    def _restore_saved_window_state(self) -> None:
        """Restore maximized/normal state after startup geometry is applied."""
        try:
            if self.config_data.ui.window_state == "zoomed":
                self.state("zoomed")
        except Exception:
            self.logger.warning("Could not restore saved window state", exc_info=True)
        finally:
            self._applying_saved_window_state = False

    def _persist_window_geometry(self, force: bool = False) -> None:
        """Persist size, position, and window state when the window changes."""
        if self._applying_saved_window_state:
            return

        ui = self.config_data.ui
        state = "zoomed" if self.state() == "zoomed" else "normal"
        width, height, x, y = ui.width, ui.height, ui.pos_x, ui.pos_y

        if state == "normal":
            try:
                width = self.winfo_width()
                height = self.winfo_height()
                x = self.winfo_x()
                y = self.winfo_y()
            except Exception:
                return
            if width <= 0 or height <= 0:
                return

        snapshot = (width, height, x, y, state)
        if not force and snapshot == self._last_saved_geometry:
            return

        ui.width = width
        ui.height = height
        ui.pos_x = x
        ui.pos_y = y
        ui.window_state = state
        self._last_saved_geometry = snapshot
        save_config(self.config_data)

    def _schedule_geometry_save(self) -> None:
        """Throttle geometry writes while the user drags/resizes the window."""
        if self._applying_saved_window_state:
            return
        if self._geometry_save_job is not None:
            try:
                self.after_cancel(self._geometry_save_job)
            except Exception:
                pass
        self._geometry_save_job = self.after(self._geometry_save_delay_ms, self._flush_scheduled_geometry_save)

    def _flush_scheduled_geometry_save(self) -> None:
        self._geometry_save_job = None
        self._persist_window_geometry()

    def _cancel_scheduled_geometry_save(self) -> None:
        if self._geometry_save_job is None:
            return
        try:
            self.after_cancel(self._geometry_save_job)
        except Exception:
            pass
        self._geometry_save_job = None

    def _on_configure(self, _event: object) -> None:
        self._schedule_geometry_save()

    def _on_close(self) -> None:
        """Persist state and close cleanly."""
        self._cancel_scheduled_geometry_save()
        self._persist_window_geometry(force=True)
        self.stop_monitoring()
        self.destroy()


def run() -> None:
    app = MonitorReminderApp()
    app.mainloop()