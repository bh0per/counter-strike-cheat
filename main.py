import tkinter as tk
from tkinter import ttk
from tkinter import font
import pymem
import pymem.process
import keyboard
import time
import logging
from pynput.mouse import Controller, Button
from win32gui import GetWindowText, GetForegroundWindow
from random import uniform
from requests import get
from threading import Thread

mouse = Controller()

class TriggerBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TriggerBot")
        self.geometry("800x600")
        self.configure(bg="#2d2d2d")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Customize fonts
        self.title_font = font.Font(family="Helvetica", size=16, weight="bold")
        self.label_font = font.Font(family="Helvetica", size=12)
        self.button_font = font.Font(family="Helvetica", size=12)

        # Customize ttk styles
        self.style.configure(
            "TButton",
            foreground="#ffffff",
            background="#444444",
            padding=10,
            font=self.button_font,
            # Add rounded edges to buttons
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.style.configure(
            "TLabel",
            foreground="#ffffff",
            background="#2d2d2d",
            font=self.label_font,
        )

        self.toggle_active = False
        self.toggleKey = "K"

        self.create_widgets()
        keyboard.on_press_key(self.toggleKey, self.on_key_press)

        self.bot_thread = Thread(target=self.run_triggerbot)
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def create_widgets(self):
        # Title label
        self.title_label = ttk.Label(
            self,
            text="TriggerBot",
            font=self.title_font,
            padding=10,
        )
        self.title_label.pack(pady=20)

        # Content frame
        self.content_frame = ttk.Frame(self, padding=10)
        self.content_frame.pack(pady=10)

        # Status label
        self.status_label = ttk.Label(
            self.content_frame,
            text="TriggerBot is Off",
            font=self.label_font,
            padding=5,
        )
        self.status_label.grid(row=0, column=0, pady=5)

        # On button
        self.on_button = ttk.Button(
            self.content_frame,
            text="On",
            command=self.turn_on,
            padding=5,
        )
        self.on_button.grid(row=1, column=0, pady=5)

        # Off button
        self.off_button = ttk.Button(
            self.content_frame,
            text="Off",
            command=self.turn_off,
            padding=5,
        )
        self.off_button.grid(row=2, column=0, pady=5)

        # Toggle Key label
        self.toggle_label = ttk.Label(
            self.content_frame,
            text=f"Toggle Key: {self.toggleKey}",
            font=self.label_font,
            padding=5,
        )
        self.toggle_label.grid(row=3, column=0, pady=5)

        # Language buttons frame
        self.language_frame = ttk.Frame(self.content_frame, padding=10)
        self.language_frame.grid(row=4, column=0, pady=10)

        # Language buttons
        self.pl_button = ttk.Button(
            self.language_frame,
            text="PL",
            command=self.set_pl_language,
            padding=5,
        )
        self.pl_button.grid(row=0, column=0, padx=5, pady=5)

        self.eng_button = ttk.Button(
            self.language_frame,
            text="ENG",
            command=self.set_eng_language,
            padding=5,
        )
        self.eng_button.grid(row=0, column=1, padx=5, pady=5)

        self.ru_button = ttk.Button(
            self.language_frame,
            text="RU",
            command=self.set_ru_language,
            padding=5,
        )
        self.ru_button.grid(row=0, column=2, padx=5, pady=5)

    def fetch_offsets(self):
        try:
            offset = get(
                "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json"
            ).json()
            client = get(
                "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client.dll.json"
            ).json()
            return offset, client
        except Exception as e:
            logging.error(f"Nie udało się pobrać przesunięć: {e}")
            return None, None

    def initialize_pymem(self):
        try:
            pm = pymem.Pymem("cs2.exe")
            return pm
        except pymem.exception.PymemError as e:
            logging.error(f"Nie można otworzyć cs2.exe: {e}")
            return None

    def get_client_module(self, pm):
        client_module = pymem.process.module_from_name(pm.process_handle,
                                                       "client.dll")
        if not client_module:
            logging.error("Nie można znaleźć modułu client.dll.")
            return None
        return client_module.lpBaseOfDll

    def get_entity(self, pm, base_address, index):
        try:
            ent_list = pm.read_longlong(base_address + dwEntityList)
            ent_entry = pm.read_longlong(ent_list + 0x8 * (index >> 9) + 0x10)
            return pm.read_longlong(ent_entry + 120 * (index & 0x1FF))
        except Exception as e:
            logging.error(f"Błąd odczytu encji: {e}")
            return None

    def is_game_active(self):
        return GetWindowText(GetForegroundWindow()) == application_name

    def should_trigger(self, entity_team, player_team, entity_health):
        return entity_team != player_team and entity_health > 0

    def turn_on(self):
        self.toggle_active = True
        self.status_label.config(text="TriggerBot is On")
        logging.info("TriggerBot turned on.")

    def turn_off(self):
        self.toggle_active = False
        self.status_label.config(text="TriggerBot is Off")
        logging.info("TriggerBot turned off.")

    def on_key_press(self, event):
        self.toggle_active = not self.toggle_active
        state = "On" if self.toggle_active else "Off"
        self.status_label.config(text=f"TriggerBot is {state}")
        logging.info(f"TriggerBot {state}.")

    def run_triggerbot(self):
        offsets, client_data = self.fetch_offsets()
        if offsets is None or client_data is None:
            return

        global dwEntityList, dwLocalPlayerPawn, m_iHealth, m_iTeamNum, m_iIDEntIndex
        dwEntityList = offsets["client.dll"]["dwEntityList"]
        dwLocalPlayerPawn = offsets["client.dll"]["dwLocalPlayerPawn"]
        m_iHealth = client_data["client.dll"]["classes"]["C_BaseEntity"][
            "fields"]["m_iHealth"]
        m_iTeamNum = client_data["client.dll"]["classes"]["C_BaseEntity"][
            "fields"]["m_iTeamNum"]
        m_iIDEntIndex = client_data["client.dll"]["classes"][
            "C_CSPlayerPawnBase"]["fields"]["m_iIDEntIndex"]

        pm = self.initialize_pymem()
        if pm is None:
            return

        client_base = self.get_client_module(pm)
        if client_base is None:
            return

        last_shot_time = 0

        while True:
            try:
                if not self.is_game_active():
                    time.sleep(0.05)  # zmniejszone opóźnienie
                    continue

                if self.toggle_active:
                    player = pm.read_longlong(client_base + dwLocalPlayerPawn)
                    entity_id = pm.read_int(player + m_iIDEntIndex)

                    if entity_id > 0:
                        entity = self.get_entity(pm, client_base, entity_id)
                        if entity:
                            entity_team = pm.read_int(entity + m_iTeamNum)
                            player_team = pm.read_int(player + m_iTeamNum)
                            entity_health = pm.read_int(entity + m_iHealth)

                            if self.should_trigger(entity_team, player_team,
                                                  entity_health):
                                current_time = time.time()
                                if current_time - last_shot_time >= 0.05:  # zmniejszone opóźnienie między strzałami
                                    time.sleep(uniform(
                                        0.01, 0.02))  # zmniejszone opóźnienie
                                    mouse.press(Button.left)
                                    time.sleep(uniform(
                                        0.01, 0.03))  # zmniejszone opóźnienie
                                    mouse.release(Button.left)
                                    last_shot_time = current_time

                    time.sleep(0.01)  # zmniejszone opóźnienie
                else:
                    time.sleep(0.05)  # zmniejszone opóźnienie
            except KeyboardInterrupt:
                logging.info("TriggerBot stopped by user.")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")

    def set_pl_language(self):
        self.on_button.config(text="Włącz")
        self.off_button.config(text="Wyłącz")
        self.status_label.config(text="TriggerBot jest wyłączony")
        self.toggle_label.config(
            text=f"Klawisz przełączania: {self.toggleKey}")
        logging.info("Changed language to Polish.")

    def set_eng_language(self):
        self.on_button.config(text="On")
        self.off_button.config(text="Off")
        self.status_label.config(text="TriggerBot is turned off")
        self.toggle_label.config(text=f"Toggle Key: {self.toggleKey}")
        logging.info("Changed language to English.")

    def set_ru_language(self):
        self.on_button.config(text="Включить")
        self.off_button.config(text="Выключить")
        self.status_label.config(text="ТриггерБот отключен")
        self.toggle_label.config(
            text=f"Клавиша переключения: {self.toggleKey}")
        logging.info("Changed language to Russian.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    application_name = "Counter-Strike 2"
    app = TriggerBotApp()
    app.mainloop()
