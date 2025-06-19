# mojaNauka 3.4.3 - Poprawka animacji karty (TclError) i finalne usprawnienia
# Wymaga: pip install pygame

import tkinter as tk
from tkinter import ttk, font, messagebox, simpledialog, Toplevel, Listbox
import json
import os
import random
import uuid
import copy
from datetime import datetime, timedelta
import math

try:
    import pygame
    SOUND_ENABLED_BY_INSTALL = True
except ImportError:
    SOUND_ENABLED_BY_INSTALL = False

APP_VERSION = "3.4.3"
FOLDER_PRZEDMIOTOW = "decks"
FOLDER_DZWIEKOW = "sounds"
PLIK_POSTEPU_PREFIX = "progress_"
PLIK_USTAWIEN = "settings.json"

THEMES = {
    "Dark": {
        "bg": "#1e1e1e", "frame_bg": "#252526", "fg": "#cccccc", "border": "#3c3c3c", "highlight": "#007acc",
        "danger": "#f44747", "warning": "#f0a830", "accent": "#4ec9b0", "easy": "#c586c0", "secondary": "#569cd6",
        "hover_bg": "#3e3e42", "button_fg": "#ffffff"
    },
    "Light": {
        "bg": "#f5f5f5", "frame_bg": "#ffffff", "fg": "#222222", "border": "#e0e0e0", "highlight": "#0078d4",
        "danger": "#d13438", "warning": "#f7a300", "accent": "#0b8a0b", "easy": "#881798", "secondary": "#0078d4",
        "hover_bg": "#e6e6e6", "button_fg": "#ffffff"
    }
}

SRS_INTERVALS = {
    'again': timedelta(minutes=1), 'hard': timedelta(minutes=10),
    'good_initial': timedelta(days=1), 'easy_initial': timedelta(days=4),
    'good_factor': 2.5, 'easy_factor_bonus': 1.3
}
SRS_MATURITY_THRESHOLD = timedelta(days=21)

class SettingsManager:
    def __init__(self):
        self.defaults = {'theme': 'Dark', 'sound_enabled': True, 'timer_duration': 0}
        self.settings = self.defaults.copy()
        self.load_settings()
    def load_settings(self):
        try:
            with open(PLIK_USTAWIEN, 'r') as f: self.settings.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError): self.save_settings()
    def save_settings(self):
        with open(PLIK_USTAWIEN, 'w') as f: json.dump(self.settings, f, indent=2)
    def get(self, key): return self.settings.get(key, self.defaults.get(key))
    def set(self, key, value): self.settings[key] = value

class SoundManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        if not SOUND_ENABLED_BY_INSTALL: self.sounds = {}; return
        try:
            pygame.mixer.init()
            self.sounds = {'flip': self.load_sound('flip'), 'correct': self.load_sound('correct'), 'incorrect': self.load_sound('incorrect')}
        except Exception as e:
            print(f"Błąd inicjalizacji dźwięku: {e}"); self.sounds = {}
    def load_sound(self, name):
        for ext in ['.wav', '.ogg']:
            path = os.path.join(FOLDER_DZWIEKOW, f"{name}{ext}")
            if os.path.exists(path): return pygame.mixer.Sound(path)
        return None
    def play(self, sound_name):
        if SOUND_ENABLED_BY_INSTALL and self.settings.get('sound_enabled') and self.sounds.get(sound_name): self.sounds[sound_name].play()

class mojaNaukaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self.sound_manager = SoundManager(self.settings)
        os.makedirs(FOLDER_PRZEDMIOTOW, exist_ok=True); os.makedirs(FOLDER_DZWIEKOW, exist_ok=True)
        self.title(f"mojaNauka {APP_VERSION}"); self.geometry("950x700"); self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.przy_zamykaniu)
        self.theme = THEMES[self.settings.get('theme')]
        self.konfiguruj_style()
        self.configure(bg=self.theme['bg'])
        container = ttk.Frame(self, style='TFrame'); container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1); container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (WelcomeScreen, StudyScreen, DeckEditor, StatsScreen, BrowseScreen, SettingsScreen):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("WelcomeScreen")

    def show_frame(self, page_name, *args):
        frame = self.frames[page_name]
        if hasattr(frame, 'on_show'): frame.on_show(*args)
        frame.tkraise()
    
    def set_theme(self, theme_name):
        self.settings.set('theme', theme_name); self.theme = THEMES[theme_name]
        self.configure(bg=self.theme['bg']); self.konfiguruj_style()
        for frame in self.frames.values():
            if hasattr(frame, 'update_theme'): frame.update_theme()
    
    def konfiguruj_style(self):
        style = ttk.Style(self); style.theme_use('clam')
        style.configure('.', background=self.theme['bg'], foreground=self.theme['fg'], borderwidth=0, focusthickness=0, highlightthickness=0)
        style.configure('TFrame', background=self.theme['bg'])
        style.configure('TLabel', font=('Segoe UI', 11))
        style.configure('Card.TFrame', background=self.theme['frame_bg'], relief='flat')
        style.configure('Title.TLabel', font=('Segoe UI Semibold', 24), foreground=self.theme['fg'])
        style.configure('Header.TLabel', font=('Segoe UI Semibold', 16), foreground=self.theme['fg'])
        style.configure('Subtitle.TLabel', font=('Segoe UI', 14), foreground=self.theme['secondary'])
        style.configure('Question.TLabel', background=self.theme['frame_bg'], font=('Segoe UI Semibold', 24))
        style.configure('Card.Header.TLabel', background=self.theme['frame_bg'], font=('Segoe UI', 14, 'bold'))
        style.configure('Card.TLabel', background=self.theme['frame_bg'], foreground=self.theme['fg'])
        style.configure('TButton', font=('Segoe UI', 11, 'bold'), padding=12, relief='flat', background=self.theme['frame_bg'])
        style.map('TButton', background=[('active', self.theme['hover_bg'])])
        def create_colored_button_style(name, color):
            style.configure(f'{name}.TButton', background=color, foreground=self.theme['button_fg'])
            style.map(f'{name}.TButton', background=[('active', color)])
        create_colored_button_style('Danger', self.theme['danger']); create_colored_button_style('Warning', self.theme['warning'])
        create_colored_button_style('Accent', self.theme['accent']); create_colored_button_style('Easy', self.theme['easy'])
        create_colored_button_style('Highlight', self.theme['highlight'])
        style.configure('TRadiobutton', background=self.theme['frame_bg'], foreground=self.theme['fg'])
        style.configure('TCheckbutton', background=self.theme['frame_bg'], foreground=self.theme['fg'])
        style.map('TRadiobutton', background=[('active', self.theme['frame_bg'])], indicatorcolor=[('selected', self.theme['highlight'])])
        style.map('TCheckbutton', background=[('active', self.theme['frame_bg'])], indicatorcolor=[('selected', self.theme['highlight'])])
        style.configure('Card.TRadiobutton', background=self.theme['frame_bg'], foreground=self.theme['fg'])
        style.configure('Card.TCheckbutton', background=self.theme['frame_bg'], foreground=self.theme['fg'])

    def przy_zamykaniu(self):
        self.settings.save_settings()
        if 'StudyScreen' in self.frames and hasattr(self.frames['StudyScreen'], 'nazwa_przedmiotu') and self.frames['StudyScreen'].nazwa_przedmiotu:
             self.frames['StudyScreen'].zapisz_postep()
        self.destroy()

class WelcomeScreen(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller
        top_bar = ttk.Frame(self); top_bar.pack(fill='x', padx=10, pady=10, anchor='n')
        ttk.Label(top_bar, text="Witaj w mojaNauka!", style='Title.TLabel').pack(side='left', anchor='w')
        ttk.Button(top_bar, text="⚙️", command=lambda: controller.show_frame("SettingsScreen")).pack(side='right', anchor='e')
        ttk.Label(self, text="Wybierz przedmiot, aby rozpocząć", style='Subtitle.TLabel').pack(pady=(0, 20))
        list_frame = ttk.Frame(self, style='Card.TFrame', padding=10); list_frame.pack(pady=10, padx=50, fill='x')
        self.deck_listbox = Listbox(list_frame, font=('Segoe UI', 14), relief='flat', borderwidth=0, height=8, selectborderwidth=0, exportselection=False)
        self.deck_listbox.pack(pady=10, padx=10, fill="both", expand=True)
        self.deck_listbox.bind('<<ListboxSelect>>', self.on_deck_select)
        btn_container = ttk.Frame(self); btn_container.pack(pady=10)
        main_btn_frame = ttk.Frame(btn_container, style='TFrame'); main_btn_frame.pack(pady=10)
        self.start_button = ttk.Button(main_btn_frame, text="🚀 Rozpocznij Naukę", style='Accent.TButton', state='disabled', command=self.start_session)
        self.start_button.pack(side='left', padx=10)
        ttk.Button(main_btn_frame, text="⚙️ Zarządzaj Przedmiotami", command=lambda: controller.show_frame("DeckEditor")).pack(side='left', padx=10)
        self.context_btn_frame = ttk.Frame(btn_container, style='TFrame'); self.context_btn_frame.pack(pady=10)
        self.browse_button = ttk.Button(self.context_btn_frame, text="👁️ Przeglądaj", state='disabled', command=self.browse_deck)
        self.browse_button.pack(side='left', padx=10)
        self.stats_button = ttk.Button(self.context_btn_frame, text="📊 Statystyki", state='disabled', command=self.show_stats)
        self.stats_button.pack(side='left', padx=10)
        self.reset_button = ttk.Button(self.context_btn_frame, text="🗑️ Wyzeruj Przedmiot", style='Danger.TButton', state='disabled', command=self.reset_deck)
        self.reset_button.pack(side='left', padx=10)
        self.stats_frame = ttk.Frame(self, style='Card.TFrame', padding=20); self.stats_frame.pack(pady=20, padx=50, fill='x')
        ttk.Label(self.stats_frame, text="Podsumowanie Przedmiotu", style='Card.Header.TLabel').pack(pady=(0, 15))
        self.stats_canvas = tk.Canvas(self.stats_frame, height=20, highlightthickness=0)
        self.stats_canvas.pack(fill='x')
        self.legend_frame = ttk.Frame(self.stats_frame, style='Card.TFrame'); self.legend_frame.pack(pady=10)
        self.update_theme()
    def update_theme(self):
        theme = self.controller.theme
        self.deck_listbox.config(bg=theme['frame_bg'], fg=theme['fg'], selectbackground=theme['highlight'])
        self.stats_canvas.config(bg=theme['frame_bg'])
        if self.deck_listbox.curselection(): self.on_deck_select()
    def on_show(self, *args):
        self.deck_listbox.delete(0, 'end')
        przedmioty = [f.replace('.txt', '') for f in os.listdir(FOLDER_PRZEDMIOTOW) if f.endswith('.txt')]
        for przedmiot in przedmioty: self.deck_listbox.insert('end', przedmiot)
        self.start_button.config(state='disabled'); self.stats_button.config(state='disabled')
        self.reset_button.config(state='disabled'); self.browse_button.config(state='disabled')
        self.update_stats_display(None)
    def on_deck_select(self, event=None):
        if not self.deck_listbox.curselection(): return
        self.start_button.config(state='normal'); self.stats_button.config(state='normal')
        self.reset_button.config(state='normal'); self.browse_button.config(state='normal')
        self.update_stats_display(self.get_deck_summary())
    def get_deck_summary(self, deck_name=None):
        if deck_name is None:
            if not self.deck_listbox.curselection(): return {}
            deck_name = self.deck_listbox.get(self.deck_listbox.curselection())
        plik_postepu = f"{PLIK_POSTEPU_PREFIX}{deck_name}.json"
        summary = {'new': 0, 'learning': 0, 'young': 0, 'mature': 0}
        if not os.path.exists(plik_postepu):
            plik_przedmiotu = os.path.join(FOLDER_PRZEDMIOTOW, f"{deck_name}.txt")
            if os.path.exists(plik_przedmiotu):
                with open(plik_przedmiotu, 'r', encoding='utf-8') as f: summary['new'] = len([line for line in f if line.strip()])
        else:
            with open(plik_postepu, 'r', encoding='utf-8') as f:
                try: karty = json.load(f)
                except json.JSONDecodeError: karty = []
            now = datetime.now()
            for k in karty:
                if k.get('status') == 'new': summary['new'] += 1
                elif datetime.fromisoformat(k.get('due_date', now.isoformat())) <= now: summary['learning'] += 1
                else:
                    interval = timedelta(seconds=k.get('interval', 0))
                    if interval >= SRS_MATURITY_THRESHOLD: summary['mature'] += 1
                    else: summary['young'] += 1
        return summary
    def update_stats_display(self, summary):
        self.stats_canvas.delete("all");
        for widget in self.legend_frame.winfo_children(): widget.destroy()
        if not summary: return
        do_nauki = summary.get('new', 0) + summary.get('learning', 0)
        nauczone = summary.get('young', 0) + summary.get('mature', 0)
        total = do_nauki + nauczone
        if total == 0: return
        canvas_width = 850
        nauka_width = (do_nauki / total) * canvas_width
        self.stats_canvas.create_rectangle(0, 0, nauka_width, 20, fill=self.controller.theme['danger'], outline="")
        nauczone_width = (nauczone / total) * canvas_width
        self.stats_canvas.create_rectangle(nauka_width, 0, nauka_width + nauczone_width, 20, fill=self.controller.theme['accent'], outline="")
        if do_nauki > 0:
            legend_item = ttk.Frame(self.legend_frame, style='Card.TFrame'); legend_item.pack(side='left', padx=10)
            ttk.Label(legend_item, text="●", foreground=self.controller.theme['danger'], font=('Segoe UI', 14), style='Card.TLabel').pack(side='left')
            ttk.Label(legend_item, text=f"Nie nauczone: {do_nauki}", style='Card.TLabel').pack(side='left', padx=5)
        if nauczone > 0:
            legend_item2 = ttk.Frame(self.legend_frame, style='Card.TFrame'); legend_item2.pack(side='left', padx=10)
            ttk.Label(legend_item2, text="●", foreground=self.controller.theme['accent'], font=('Segoe UI', 14), style='Card.TLabel').pack(side='left')
            ttk.Label(legend_item2, text=f"Nauczone: {nauczone}", style='Card.TLabel').pack(side='left', padx=5)
    def start_session(self):
        deck_name = self.deck_listbox.get(self.deck_listbox.curselection())
        self.controller.frames['StudyScreen'].uruchom_przedmiot(deck_name)
        self.controller.show_frame('StudyScreen')
    def browse_deck(self): self.controller.show_frame('BrowseScreen', self.deck_listbox.get(self.deck_listbox.curselection()), "WelcomeScreen")
    def show_stats(self): self.controller.show_frame('StatsScreen', self.deck_listbox.get(self.deck_listbox.curselection()))
    def reset_deck(self):
        if not self.deck_listbox.curselection(): return
        deck_name = self.deck_listbox.get(self.deck_listbox.curselection())
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno chcesz wyzerować cały postęp dla przedmiotu '{deck_name}'?"):
            plik_postepu = f"{PLIK_POSTEPU_PREFIX}{deck_name}.json"
            if os.path.exists(plik_postepu): os.remove(plik_postepu)
            self.update_stats_display(self.get_deck_summary())
            messagebox.showinfo("Sukces", "Postęp został wyzerowany.")

class StudyScreen(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller; self.timer_id = None
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        top_bar = ttk.Frame(self); top_bar.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        self.nazwa_przedmiotu_label = ttk.Label(top_bar, text="", style='Header.TLabel'); self.nazwa_przedmiotu_label.pack(side='left')
        context_bar = ttk.Frame(top_bar); context_bar.pack(side='right')
        self.browse_button = ttk.Button(context_bar, text="👁️ Przeglądaj", command=self.browse_deck_in_session); self.browse_button.pack(side='left', padx=10)
        self.cofnij_button = ttk.Button(context_bar, text="↩️ Cofnij Ocenę", command=self.cofnij_ocene, state='disabled'); self.cofnij_button.pack(side='left', padx=10)
        ttk.Button(context_bar, text="Zakończ sesję", command=self.zakoncz_sesje_btn, style='Danger.TButton').pack(side='left')
        card_container = ttk.Frame(self, style='TFrame'); card_container.grid(row=1, column=0, sticky='nsew', padx=50, pady=20)
        card_container.grid_rowconfigure(0, weight=1); card_container.grid_columnconfigure(0, weight=1)
        self.ramka_pytania = AnimatedCard(card_container, style='Card.TFrame')
        self.ramka_pytania.grid(row=0, column=0, sticky='nsew')
        self.label_pytanie = ttk.Label(self.ramka_pytania, text="...", style='Question.TLabel', wraplength=700, justify="center", anchor='center')
        self.ramka_pytania.set_content(self.label_pytanie)
        self.przyciski_kontrolne = ttk.Frame(self); self.przyciski_kontrolne.grid(row=2, column=0, pady=20)
        self.status_bar = ttk.Frame(self); self.status_bar.grid(row=3, column=0, sticky='ew', padx=20, pady=5)
        self.new_label = ttk.Label(self.status_bar, text="Nowe: 0", font=('Segoe UI', 10, 'bold')); self.new_label.pack(side='left')
        self.review_label = ttk.Label(self.status_bar, text="Powtórki: 0", font=('Segoe UI', 10, 'bold')); self.review_label.pack(side='left', padx=20)
        self.done_label = ttk.Label(self.status_bar, text="Ukończone: 0", font=('Segoe UI', 10, 'bold')); self.done_label.pack(side='left')
        self.timer_label = ttk.Label(self.status_bar, text="", font=('Segoe UI', 10, 'bold')); self.timer_label.pack(side='right')
        self.update_theme()
    def update_theme(self):
        theme = self.controller.theme
        self.new_label.config(foreground=theme['secondary']); self.review_label.config(foreground=theme['warning']); self.done_label.config(foreground=theme['accent']); self.timer_label.config(foreground=theme['fg'])
    def on_show(self, *args):
        self.focus_set()
        self.controller.bind('1', self.ocen_karte_skrot_1)
        self.controller.bind('2', self.ocen_karte_skrot_2)
        self.controller.bind('3', self.ocen_karte_skrot_3)
        self.controller.bind('4', self.ocen_karte_skrot_4)
        self.controller.bind('<space>', self.odwroc_karte_skrot)
    def ocen_karte_skrot_1(self, event=None):
        if hasattr(self, 'stan_aplikacji') and self.stan_aplikacji == 'ocena': self.ocen_karte('again')
    def ocen_karte_skrot_2(self, event=None):
        if hasattr(self, 'stan_aplikacji') and self.stan_aplikacji == 'ocena': self.ocen_karte('hard')
    def ocen_karte_skrot_3(self, event=None):
        if hasattr(self, 'stan_aplikacji') and self.stan_aplikacji == 'ocena': self.ocen_karte('good')
    def ocen_karte_skrot_4(self, event=None):
        if hasattr(self, 'stan_aplikacji') and self.stan_aplikacji == 'ocena': self.ocen_karte('easy')
    def odwroc_karte_skrot(self, event=None):
        if hasattr(self, 'stan_aplikacji') and self.stan_aplikacji == 'pytanie' and hasattr(self, 'przycisk_pokaz_odpowiedz') and self.przycisk_pokaz_odpowiedz.winfo_exists(): self.przycisk_pokaz_odpowiedz.invoke()
    def uruchom_przedmiot(self, nazwa_przedmiotu):
        self.nazwa_przedmiotu = nazwa_przedmiotu; self.nazwa_przedmiotu_label.config(text=f"Przedmiot: {nazwa_przedmiotu}")
        self.wczytaj_dane_przedmiotu(); self.rozpocznij_sesje()
    def rozpocznij_sesje(self):
        self.previous_state = None; self.cofnij_button.config(state='disabled')
        now = datetime.now()
        karty_do_powtorki = [k for k in self.karty if k['status'] != 'new' and datetime.fromisoformat(k['due_date']) <= now]
        karty_nowe = [k for k in self.karty if k['status'] == 'new']
        self.kolejka = sorted(karty_do_powtorki, key=lambda x: x['due_date']) + karty_nowe
        random.shuffle(self.kolejka); self.karty_zrobione_w_sesji = 0
        self.aktualizuj_licznik_statusu(); self.nastepna_karta()
    def nastepna_karta(self):
        self.cofnij_button.config(state='disabled')
        if self.timer_id: self.after_cancel(self.timer_id); self.timer_id = None; self.timer_label.config(text="")
        for widget in self.przyciski_kontrolne.winfo_children(): widget.destroy()
        if not self.kolejka: self.koniec_sesji(); return
        self.biezaca_karta = self.kolejka[0]
        self.label_pytanie.config(text=self.biezaca_karta['pytanie'])
        self.ramka_pytania.reset()
        self.przycisk_pokaz_odpowiedz = ttk.Button(self.przyciski_kontrolne, text="Oceń (Spacja)", command=self.odwroc_karte, style='Highlight.TButton')
        self.przycisk_pokaz_odpowiedz.pack(ipady=10, ipadx=20)
        self.stan_aplikacji = 'pytanie'
        self.aktualizuj_licznik_statusu()
        timer_duration_minutes = self.controller.settings.get('timer_duration')
        if timer_duration_minutes > 0: self.start_timer(timer_duration_minutes * 60)
    def start_timer(self, seconds_left):
        if self.stan_aplikacji != 'pytanie': return
        mins, secs = divmod(seconds_left, 60)
        self.timer_label.config(text=f"Czas: {mins:02d}:{secs:02d}")
        if seconds_left > 0: self.timer_id = self.after(1000, lambda: self.start_timer(seconds_left - 1))
        else: self.odwroc_karte()
    def odwroc_karte(self):
        if self.stan_aplikacji != 'pytanie': return
        if self.timer_id: self.after_cancel(self.timer_id); self.timer_id = None; self.timer_label.config(text="")
        self.controller.sound_manager.play('flip'); self.ramka_pytania.flip(on_complete=self.pokaz_oceny)
    def pokaz_oceny(self):
        for widget in self.przyciski_kontrolne.winfo_children(): widget.destroy()
        ttk.Button(self.przyciski_kontrolne, text="[1] Nie umiem", command=lambda: self.ocen_karte('again'), style='Danger.TButton').pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(self.przyciski_kontrolne, text="[2] Trudne", command=lambda: self.ocen_karte('hard'), style='Warning.TButton').pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(self.przyciski_kontrolne, text="[3] Dobrze", command=lambda: self.ocen_karte('good'), style='Accent.TButton').pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(self.przyciski_kontrolne, text="[4] Łatwe", command=lambda: self.ocen_karte('easy'), style='Easy.TButton').pack(side='left', expand=True, fill='x', padx=5)
        self.stan_aplikacji = 'ocena'
    def ocen_karte(self, ocena: str):
        if not hasattr(self, 'biezaca_karta') or not self.biezaca_karta: return
        self.previous_state = {'karty': copy.deepcopy(self.karty), 'kolejka': copy.deepcopy(self.kolejka), 'done_count': self.karty_zrobione_w_sesji}
        self.cofnij_button.config(state='normal')
        karta_z_kolejki = self.kolejka.pop(0)
        karta = next((k for k in self.karty if k['id'] == karta_z_kolejki['id']), None)
        if karta is None: self.nastepna_karta(); return
        now = datetime.now()
        if ocena == 'again':
            self.controller.sound_manager.play('incorrect'); karta['status'] = 'learning'; karta['interval'] = SRS_INTERVALS['again'].total_seconds()
            karta['due_date'] = (now + SRS_INTERVALS['again']).isoformat(); self.kolejka.insert(random.randint(0, min(len(self.kolejka), 3)), karta)
        else:
            self.controller.sound_manager.play('correct')
            if karta['status'] in ['new', 'learning']:
                if ocena == 'hard': karta['interval'] = SRS_INTERVALS['hard'].total_seconds()
                elif ocena == 'good': karta['interval'] = SRS_INTERVALS['good_initial'].total_seconds()
                elif ocena == 'easy': karta['interval'] = SRS_INTERVALS['easy_initial'].total_seconds()
            elif karta['status'] == 'review':
                if ocena == 'hard': karta['interval'] *= 1.2
                elif ocena == 'good': karta['interval'] *= SRS_INTERVALS['good_factor']
                elif ocena == 'easy': karta['interval'] *= SRS_INTERVALS['good_factor'] * SRS_INTERVALS['easy_factor_bonus']
            karta['status'] = 'review'; karta['due_date'] = (now + timedelta(seconds=karta['interval'])).isoformat()
            self.karty_zrobione_w_sesji += 1
        self.nastepna_karta()
    def cofnij_ocene(self):
        if not self.previous_state: return
        self.karty = self.previous_state['karty']; self.kolejka = self.previous_state['kolejka']
        self.karty_zrobione_w_sesji = self.previous_state['done_count']
        self.previous_state = None; self.cofnij_button.config(state='disabled')
        self.nastepna_karta()
    def browse_deck_in_session(self): self.controller.show_frame('BrowseScreen', self.nazwa_przedmiotu, "StudyScreen")
    def zakoncz_sesje_btn(self): self.zapisz_postep(); self.controller.show_frame("WelcomeScreen")
    def koniec_sesji(self): self.zapisz_postep(); self.controller.show_frame("WelcomeScreen")
    def aktualizuj_licznik_statusu(self):
        nowe_w_kolejce = sum(1 for k in self.kolejka if k['status'] == 'new'); powtorki_w_kolejce = len(self.kolejka) - nowe_w_kolejce
        self.new_label.config(text=f"Nowe: {nowe_w_kolejce}"); self.review_label.config(text=f"Powtórki: {powtorki_w_kolejce}"); self.done_label.config(text=f"Ukończone: {self.karty_zrobione_w_sesji}")
    def wczytaj_dane_przedmiotu(self):
        plik_przedmiotu = os.path.join(FOLDER_PRZEDMIOTOW, f"{self.nazwa_przedmiotu}.txt"); plik_postepu = f"{PLIK_POSTEPU_PREFIX}{self.nazwa_przedmiotu}.json"
        pytania_z_pliku = []
        if os.path.exists(plik_przedmiotu):
            with open(plik_przedmiotu, 'r', encoding='utf-8') as f: pytania_z_pliku = [line.strip() for line in f if line.strip()]
        postep_by_question = {}
        if os.path.exists(plik_postepu):
            try:
                with open(plik_postepu, 'r', encoding='utf-8') as f:
                    postep_data = json.load(f)
                    if isinstance(postep_data, list): postep_by_question = {p['pytanie']: p for p in postep_data if isinstance(p, dict) and 'pytanie' in p}
            except (json.JSONDecodeError, TypeError): pass 
        self.karty = []
        for pytanie_text in pytania_z_pliku:
            if pytanie_text in postep_by_question: self.karty.append(postep_by_question[pytanie_text])
            else: self.karty.append(self.stworz_nowa_karte(pytanie_text))
    def stworz_nowa_karte(self, pytanie_text): return {"id": str(uuid.uuid4()), "pytanie": pytanie_text, "status": "new", "due_date": datetime.now().isoformat(), "interval": 0}
    def zapisz_postep(self):
        if not hasattr(self, 'nazwa_przedmiotu') or not self.nazwa_przedmiotu: return
        plik_postepu = f"{PLIK_POSTEPU_PREFIX}{self.nazwa_przedmiotu}.json"
        if hasattr(self, 'karty'):
            with open(plik_postepu, 'w', encoding='utf-8') as f: json.dump(self.karty, f, ensure_ascii=False, indent=2)

class StatsScreen(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller
        top_frame = ttk.Frame(self); top_frame.pack(fill='x', padx=10, pady=10)
        self.title_label = ttk.Label(top_frame, text="Statystyki", style='Title.TLabel'); self.title_label.pack(side='left')
        ttk.Button(top_frame, text="← Wróć", command=lambda: controller.show_frame("WelcomeScreen")).pack(side='right')
        main_frame = ttk.Frame(self); main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        self.canvas = tk.Canvas(main_frame, highlightthickness=0); self.canvas.pack(side='left', fill='both', expand=True, padx=20)
        right_panel = ttk.Frame(main_frame); right_panel.pack(side='left', fill='y', padx=20)
        self.legend_frame = ttk.Frame(right_panel); self.legend_frame.pack(anchor='n', pady=20)
        wnioski_frame = ttk.Frame(right_panel, style='Card.TFrame', padding=15); wnioski_frame.pack(anchor='n', pady=20, fill='x')
        ttk.Label(wnioski_frame, text="Wnioski", style='Card.Header.TLabel').pack(anchor='w')
        self.wnioski_label = ttk.Label(wnioski_frame, text="", style='Card.TLabel', wraplength=250, justify='left'); self.wnioski_label.pack(anchor='w', pady=5)
        self.update_theme()
    def update_theme(self): self.canvas.config(bg=self.controller.theme['bg'])
    def draw_pie_chart(self, summary):
        self.canvas.delete("all");
        for widget in self.legend_frame.winfo_children(): widget.destroy()
        total = sum(summary.values())
        if total == 0:
            self.canvas.create_text(250, 250, text="Brak danych do wyświetlenia.", fill=self.controller.theme['fg'], font=('Segoe UI', 14))
            self.wnioski_label.config(text="Dodaj karty do przedmiotu."); return
        colors = {'new': self.controller.theme['secondary'], 'learning': self.controller.theme['warning'], 'young': self.controller.theme['accent'], 'mature': self.controller.theme['easy']}
        names = {'new': 'Nowe', 'learning': 'W Nauce', 'young': 'Młode', 'mature': 'Dojrzałe'}
        start_angle = 90
        for key, value in summary.items():
            if value > 0:
                extent = (value / total) * 360
                self.canvas.create_arc(50, 50, 450, 450, start=start_angle, extent=-extent, fill=colors[key], outline=self.controller.theme['bg'], width=3)
                legend_item = ttk.Frame(self.legend_frame); legend_item.pack(anchor='w', pady=5)
                ttk.Label(legend_item, text="●", foreground=colors[key], font=('Segoe UI', 20)).pack(side='left')
                ttk.Label(legend_item, text=f"{names[key]}: {value} ({value/total:.1%})", font=('Segoe UI', 12)).pack(side='left', padx=10)
                start_angle -= extent
        self.wnioski_label.config(text=self.generuj_wnioski(summary, total))
    def generuj_wnioski(self, summary, total):
        nauczone_proc = (summary['young'] + summary['mature']) / total if total > 0 else 0
        if nauczone_proc > 0.8: return "Świetna robota! Zdecydowana większość materiału jest już opanowana. Kontynuuj regularne powtórki."
        elif nauczone_proc > 0.5: return "Dobry postęp! Ponad połowa kart jest nauczona. Skup się na kartach 'W Nauce'."
        elif summary['new'] == total: return "Czas zacząć! Wszystkie karty w tym przedmiocie są nowe. Rozpocznij sesję."
        else: return "Przed Tobą jeszcze trochę pracy. Regularne sesje pomogą Ci szybko opanować materiał."
    def on_show(self, deck_name):
        self.title_label.config(text=f"Statystyki: {deck_name}")
        summary = self.controller.frames['WelcomeScreen'].get_deck_summary(deck_name)
        self.draw_pie_chart(summary)

class BrowseScreen(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller
        top_frame = ttk.Frame(self); top_frame.pack(fill='x', padx=10, pady=10)
        self.title_label = ttk.Label(top_frame, text="Przeglądaj", style='Title.TLabel'); self.title_label.pack(side='left')
        self.back_button = ttk.Button(top_frame, text="← Wróć", command=lambda: controller.show_frame("WelcomeScreen")); self.back_button.pack(side='right')
        self.listbox = Listbox(self, font=('Segoe UI', 11), relief='flat', borderwidth=0)
        self.listbox.pack(fill='both', expand=True, padx=20, pady=10)
        self.update_theme()
    def update_theme(self): self.listbox.config(bg=self.controller.theme['frame_bg'], fg=self.controller.theme['fg'], selectbackground=self.controller.theme['highlight'], selectforeground=self.controller.theme['button_fg'])
    def on_show(self, deck_name, return_screen="WelcomeScreen"):
        self.title_label.config(text=f"Przeglądaj: {deck_name}"); self.back_button.config(command=lambda: self.controller.show_frame(return_screen))
        self.listbox.delete(0, 'end')
        plik_postepu = f"{PLIK_POSTEPU_PREFIX}{deck_name}.json"
        karty = []
        if not os.path.exists(plik_postepu):
            plik_przedmiotu = os.path.join(FOLDER_PRZEDMIOTOW, f"{deck_name}.txt")
            if os.path.exists(plik_przedmiotu):
                with open(plik_przedmiotu, 'r', encoding='utf-8') as f: karty = [{'pytanie': line.strip(), 'status': 'new'} for line in f if line.strip()]
        else:
            with open(plik_postepu, 'r', encoding='utf-8') as f:
                try: karty = json.load(f)
                except json.JSONDecodeError: karty = []
        now = datetime.now()
        for i, k in enumerate(sorted(karty, key=lambda x: x['pytanie'])):
            self.listbox.insert('end', k['pytanie'])
            is_learned = k.get('status') in ['young', 'mature'] and datetime.fromisoformat(k.get('due_date', now.isoformat())) > now
            final_bg_color = self.controller.theme['accent'] if is_learned else self.controller.theme['danger']
            self.listbox.itemconfig(i, {'bg': final_bg_color, 'fg': self.controller.theme['button_fg']})

class SettingsScreen(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller
        top_frame = ttk.Frame(self); top_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(top_frame, text="Ustawienia", style='Title.TLabel').pack(side='left')
        ttk.Button(top_frame, text="← Zapisz i Wróć", command=self.save_and_exit, style='Accent.TButton').pack(side='right')
        main_frame = ttk.Frame(self, style='Card.TFrame', padding=20); main_frame.pack(fill='both', expand=True, padx=50, pady=20)
        self.theme_var = tk.StringVar(value=self.controller.settings.get('theme'))
        self.sound_var = tk.BooleanVar(value=self.controller.settings.get('sound_enabled'))
        self.timer_var = tk.IntVar(value=self.controller.settings.get('timer_duration'))
        theme_frame = ttk.Frame(main_frame, style='Card.TFrame'); theme_frame.pack(fill='x', pady=10)
        ttk.Label(theme_frame, text="Motyw aplikacji:", style='Card.Header.TLabel').pack(anchor='w')
        ttk.Radiobutton(theme_frame, text="Ciemny", variable=self.theme_var, value="Dark", command=self.apply_theme, style='Card.TRadiobutton').pack(anchor='w', padx=10)
        ttk.Radiobutton(theme_frame, text="Jasny", variable=self.theme_var, value="Light", command=self.apply_theme, style='Card.TRadiobutton').pack(anchor='w', padx=10)
        sound_frame = ttk.Frame(main_frame, style='Card.TFrame'); sound_frame.pack(fill='x', pady=10)
        ttk.Label(sound_frame, text="Dźwięki:", style='Card.Header.TLabel').pack(anchor='w')
        ttk.Checkbutton(sound_frame, text="Włącz efekty dźwiękowe", variable=self.sound_var, style='Card.TCheckbutton').pack(anchor='w', padx=10)
        timer_frame = ttk.Frame(main_frame, style='Card.TFrame'); timer_frame.pack(fill='x', pady=10)
        ttk.Label(timer_frame, text="Limit czasu na odpowiedź (w minutach, 0 = wyłączony):", style='Card.Header.TLabel').pack(anchor='w')
        ttk.Spinbox(timer_frame, from_=0, to=60, increment=1, textvariable=self.timer_var, width=10).pack(anchor='w', padx=10, pady=5)
        about_frame = ttk.Frame(main_frame, style='Card.TFrame'); about_frame.pack(fill='x', pady=20, side='bottom')
        ttk.Label(about_frame, text=f"mojaNauka v{APP_VERSION}", style='Card.TLabel').pack()
        ttk.Label(about_frame, text="by Arychats (GitHub) © 2025", style='Card.TLabel').pack()
        self.update_theme()
    def apply_theme(self): self.controller.set_theme(self.theme_var.get())
    def save_and_exit(self):
        self.controller.settings.set('theme', self.theme_var.get()); self.controller.settings.set('sound_enabled', self.sound_var.get())
        self.controller.settings.set('timer_duration', self.timer_var.get()); self.controller.show_frame("WelcomeScreen")
    def on_show(self, *args):
        self.theme_var.set(self.controller.settings.get('theme')); self.sound_var.set(self.controller.settings.get('sound_enabled'))
        self.timer_var.set(self.controller.settings.get('timer_duration'))
    def update_theme(self): pass

class DeckEditor(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent); self.controller = controller
        top_frame = ttk.Frame(self); top_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(top_frame, text="Edytor Przedmiotów", style='Title.TLabel').pack(side='left')
        ttk.Button(top_frame, text="← Wróć", command=lambda: controller.show_frame("WelcomeScreen")).pack(side='right')
        main_frame = ttk.Frame(self); main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        left_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=10); left_frame.pack(side='left', fill='y', padx=(0, 10))
        ttk.Label(left_frame, text="Przedmioty", style='Card.Header.TLabel').pack()
        self.deck_listbox = Listbox(left_frame, width=25, relief='flat', borderwidth=0)
        self.deck_listbox.pack(fill='y', expand=True, pady=5)
        self.deck_listbox.bind('<<ListboxSelect>>', self.wyswietl_karty_przedmiotu)
        btn_frame = ttk.Frame(left_frame, style='Card.TFrame'); btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="+ Nowy", command=self.stworz_nowy_przedmiot).pack(fill='x')
        ttk.Button(btn_frame, text="- Usuń", command=self.usun_przedmiot, style='Danger.TButton').pack(fill='x', pady=2)
        right_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=10); right_frame.pack(side='right', fill='both', expand=True)
        ttk.Label(right_frame, text="Pytania w przedmiocie", style='Card.Header.TLabel').pack()
        self.card_listbox = Listbox(right_frame, relief='flat', borderwidth=0)
        self.card_listbox.pack(fill='both', expand=True, pady=5)
        card_btn_frame = ttk.Frame(right_frame, style='Card.TFrame'); card_btn_frame.pack(fill='x', pady=5)
        ttk.Button(card_btn_frame, text="+ Dodaj", command=self.dodaj_karte).pack(side='left')
        ttk.Button(card_btn_frame, text="✎ Edytuj", command=self.edytuj_karte).pack(side='left', padx=5)
        ttk.Button(card_btn_frame, text="- Usuń", command=self.usun_karte, style='Danger.TButton').pack(side='left')
        self.update_theme()
    def update_theme(self):
        theme = self.controller.theme
        for lb in [self.deck_listbox, self.card_listbox]: lb.config(bg=theme['frame_bg'], fg=theme['fg'], selectbackground=theme['highlight'])
    def on_show(self, *args): self.odswiez_liste_przedmiotow()
    def odswiez_liste_przedmiotow(self):
        self.deck_listbox.delete(0, 'end')
        przedmioty = [f.replace('.txt', '') for f in os.listdir(FOLDER_PRZEDMIOTOW) if f.endswith('.txt')]
        for przedmiot in przedmioty: self.deck_listbox.insert('end', przedmiot)
        self.card_listbox.delete(0, 'end')
    def wyswietl_karty_przedmiotu(self, event=None):
        if not self.deck_listbox.curselection(): return
        self.card_listbox.delete(0, 'end')
        self.selected_deck = self.deck_listbox.get(self.deck_listbox.curselection())
        plik_przedmiotu = os.path.join(FOLDER_PRZEDMIOTOW, f"{self.selected_deck}.txt")
        if os.path.exists(plik_przedmiotu):
            with open(plik_przedmiotu, 'r', encoding='utf-8') as f:
                self.karty_w_przedmiocie = [line.strip() for line in f if line.strip()]
            for karta in self.karty_w_przedmiocie: self.card_listbox.insert('end', karta)
    def stworz_nowy_przedmiot(self):
        nazwa = simpledialog.askstring("Nowy Przedmiot", "Podaj nazwę nowego przedmiotu:", parent=self)
        if nazwa and nazwa.strip():
            with open(os.path.join(FOLDER_PRZEDMIOTOW, f"{nazwa}.txt"), 'w', encoding='utf-8') as f: pass
            self.odswiez_liste_przedmiotow()
    def usun_przedmiot(self):
        if not self.deck_listbox.curselection(): return
        nazwa = self.deck_listbox.get(self.deck_listbox.curselection())
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno chcesz usunąć przedmiot '{nazwa}' i jego postęp?"):
            plik_przedmiotu_path = os.path.join(FOLDER_PRZEDMIOTOW, f"{nazwa}.txt")
            if os.path.exists(plik_przedmiotu_path): os.remove(plik_przedmiotu_path)
            plik_postepu = f"{PLIK_POSTEPU_PREFIX}{nazwa}.json"
            if os.path.exists(plik_postepu): os.remove(plik_postepu)
            self.odswiez_liste_przedmiotow()
    def dodaj_karte(self):
        if not hasattr(self, 'selected_deck') or not self.selected_deck: messagebox.showerror("Błąd", "Najpierw wybierz przedmiot z listy."); return
        pytanie = simpledialog.askstring("Nowe pytanie", "Wpisz treść pytania:", parent=self)
        if pytanie and pytanie.strip():
            self.karty_w_przedmiocie.append(pytanie)
            self.zapisz_biezacy_przedmiot()
    def edytuj_karte(self):
        if not self.card_listbox.curselection(): return
        index = self.card_listbox.curselection()[0]; stare_pytanie = self.karty_w_przedmiocie[index]
        nowe_pytanie = simpledialog.askstring("Edytuj pytanie", "Popraw treść pytania:", initialvalue=stare_pytanie, parent=self)
        if nowe_pytanie and nowe_pytanie.strip():
            self.karty_w_przedmiocie[index] = nowe_pytanie
            self.zapisz_biezacy_przedmiot()
    def usun_karte(self):
        if not self.card_listbox.curselection(): return
        index = self.card_listbox.curselection()[0]
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz usunąć to pytanie?"):
            del self.karty_w_przedmiocie[index]
            self.zapisz_biezacy_przedmiot()
    def zapisz_biezacy_przedmiot(self):
        plik_przedmiotu = os.path.join(FOLDER_PRZEDMIOTOW, f"{self.selected_deck}.txt")
        with open(plik_przedmiotu, 'w', encoding='utf-8') as f:
            for karta in self.karty_w_przedmiocie: f.write(karta + '\n')
        self.wyswietl_karty_przedmiotu()

class AnimatedCard(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs); self.parent = parent; self.animation_in_progress = False; self.front_content = None; self.on_flip_complete = None
    def set_content(self, front_widget):
        self.front_content = front_widget; self.front_content.pack(fill='both', expand=True, padx=20, pady=20)
    def flip(self, on_complete=None):
        if self.animation_in_progress: return
        self.animation_in_progress = True; self.on_flip_complete = on_complete
        if not hasattr(self, 'start_width') or self.winfo_width() == 1: self.start_width = self.master.winfo_width()
        self._animate_flip_out()
    def _animate_flip_out(self, step=0):
        if step < 10:
            scale = 1.0 - (step + 1) / 10.0
            self.place(relx=0.5, rely=0.5, anchor="center", relwidth=scale, relheight=1.0)
            self.parent.after(15, lambda: self._animate_flip_out(step + 1))
        else: self._animate_flip_in()
    def _animate_flip_in(self, step=0):
        if step < 10:
            scale = (step + 1) / 10.0
            self.place(relx=0.5, rely=0.5, anchor="center", relwidth=scale, relheight=1.0)
            self.parent.after(15, lambda: self._animate_flip_in(step + 1))
        else:
            self.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)
            self.animation_in_progress = False
            if self.on_flip_complete: self.on_flip_complete()
    def reset(self):
        self.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)

if __name__ == "__main__":
    app = mojaNaukaApp()
    app.mainloop()

# mojaNauka v3.4.2 by Arychats (GitHub) © 2025