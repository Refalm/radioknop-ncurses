#!/usr/bin/env python3
import curses
import json
import locale
import subprocess
import time
import os
import tempfile
import shutil
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any, Union


TRANSLATIONS = {
    'en': {
        'fetching': "RADIOKNOP TUI - Fetching data...",
        'error_prefix': "Error: ",
        'press_quit': "Press any key to quit.",
        'select_genre': "Select a Genre",
        'stations_in': "Stations in '{genre_name}'",
        'no_stations': "No stations found for '{genre_name}'.",
        'press_back': "Press 'B' to go back...",
        'playing': "Playing: {station_name}",
        'stopped': "Stopped: {station_name}",
        'stream_error': "Error: Could not find stream URL for '{station_name}'.",
        'press_continue': "Press any key to continue...",
        'invalid_genre': "'{genre_name}' is not a valid genre category.",
        'instructions_nav': "[↑/↓] Navigate",
        'instructions_play': "[Enter] Play/Stop",
        'instructions_quit': "[Q] Quit",
        'instructions_back': "[B] Back",
        'network_error': "Network error: {e}",
        'parse_error': "Failed to parse API response.",
        'generic_error': "An error occurred: {e}",
        'terminal_size_error': "Please ensure your terminal window is large enough.",
        'mpv_not_found': "Error: 'mpv' is not installed. Please install mpv first."
    },
    'nl': {
        'fetching': "RADIOKNOP TUI - Gegevens ophalen...",
        'error_prefix': "Fout: ",
        'press_quit': "Druk op een toets om af te sluiten.",
        'select_genre': "Selecteer een Genre",
        'stations_in': "Zenders in '{genre_name}'",
        'no_stations': "Geen zenders gevonden voor '{genre_name}'.",
        'press_back': "Druk op 'B' om terug te gaan...",
        'playing': "Speelt nu: {station_name}",
        'stopped': "Gestopt: {station_name}",
        'stream_error': "Fout: Kon geen stream-URL vinden voor '{station_name}'.",
        'press_continue': "Druk op een toets om verder te gaan...",
        'invalid_genre': "'{genre_name}' is geen geldige genrecategorie.",
        'instructions_nav': "[↑/↓] Navigeren",
        'instructions_play': "[Enter] Afspelen/Stoppen",
        'instructions_quit': "[Q] Afsluiten",
        'instructions_back': "[B] Terug",
        'network_error': "Netwerkfout: {e}",
        'parse_error': "API-respons kon niet worden verwerkt.",
        'generic_error': "Er is een fout opgetreden: {e}",
        'terminal_size_error': "Zorg ervoor dat je terminalvenster groot genoeg is.",
        'mpv_not_found': "Fout: 'mpv' is niet geïnstalleerd. Installeer mpv om te luisteren."
    }
}

API_URL = "https://www.radioknop.nl/api.php"
CACHE_DIR = tempfile.gettempdir()
CACHE_FILE = os.path.join(CACHE_DIR, "radioknop_cache.json")
CACHE_DURATION = 24 * 60 * 60


def get_lang() -> str:
    try:
        lang_code, _ = locale.getlocale()
        if lang_code and lang_code.startswith('nl'):
            return 'nl'
    except (ValueError, TypeError):
        pass
    return 'en'


try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

LANG = get_lang()
T = TRANSLATIONS[LANG]



class RadioApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.player_process: Optional[subprocess.Popen] = None
        self.current_station_name: Optional[str] = None
        self.data: Dict = {}

        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK,
                         curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE,
                         curses.COLOR_BLUE)

    def check_dependencies(self) -> bool:
        if shutil.which("mpv") is None:
            self.show_error(T['mpv_not_found'])
            return False
        return True

    def fetch_data(self) -> Dict:
        if os.path.exists(CACHE_FILE):
            try:
                cache_age = time.time() - os.path.getmtime(CACHE_FILE)
                if cache_age < CACHE_DURATION:
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except (IOError, json.JSONDecodeError):
                pass

        try:
            req = urllib.request.Request(
                API_URL,
                headers={'User-Agent': 'RadioKnopTUI/1.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                raw_data = response.read().decode('utf-8')
                data = json.loads(raw_data)

                try:
                    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f)
                except IOError:
                    pass
                return data

        except urllib.error.URLError as e:
            return {"error": T['network_error'].format(e=e.reason)}
        except json.JSONDecodeError:
            return {"error": T['parse_error']}
        except Exception as e:
            return {"error": T['generic_error'].format(e=e)}

    def play_stream(self, url: str, station_name: str):
        self.stop_player()
        try:
            self.player_process = subprocess.Popen(
                ["mpv", "--no-video", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.current_station_name = station_name
        except FileNotFoundError:
            self.player_process = None
            self.current_station_name = None

    def stop_player(self):
        if self.player_process:
            self.player_process.terminate()
            try:
                self.player_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.player_process.kill()
            self.player_process = None

    def update_player_status(self):
        if self.player_process and self.player_process.poll() is not None:
            self.player_process = None

    def get_playing_info(self) -> str:
        self.update_player_status()
        if self.player_process:
            return T['playing'].format(station_name=self.current_station_name)
        elif self.current_station_name:
            return T['stopped'].format(station_name=self.current_station_name)
        return ""

    def draw_menu(self, title: str, items: List[str], current_row: int, scroll_offset: int, playing_item_name: Optional[str] = None):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        if h < 5 or w < 20:
            self.stdscr.addstr(0, 0, "Terminal too small")
            return

        header_text = f" {title} "
        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(0, 0, header_text.ljust(w)[
                           :w-1], curses.color_pair(2))
        self.stdscr.attroff(curses.color_pair(2))

        max_items = h - 4

        has_scrollbar = len(items) > max_items

        for i in range(max_items):
            actual_index = i + scroll_offset
            if actual_index >= len(items):
                break

            item_text = items[actual_index]
            display_text = item_text

            if item_text == self.current_station_name and self.player_process:
                display_text = f"▶️ {display_text}"
            elif item_text == self.current_station_name and not self.player_process:
                display_text = f"⏹️ {display_text}"

            max_len = w - 4 if has_scrollbar else w - 2
            display_text = display_text[:max_len]

            line_num = i + 1
            if actual_index == current_row:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(
                    line_num, 1, f"{display_text}".ljust(max_len))
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.addstr(line_num, 1, f"{display_text}")

        if has_scrollbar:
            scrollbar_height = max_items
            scroll_range = len(items) - max_items
            if scroll_range > 0:
                thumb_size = max(
                    1, int((max_items / len(items)) * scrollbar_height))
                thumb_pos = int((scroll_offset / scroll_range)
                                * (scrollbar_height - thumb_size))

                for i in range(scrollbar_height):
                    char = '┃'
                    if i >= thumb_pos and i < thumb_pos + thumb_size:
                        char = '█'
                    self.stdscr.addstr(i + 1, w - 1, char)

        playing_info = self.get_playing_info()
        if playing_info:
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(h - 2, 0, playing_info.ljust(w)
                               [:w-1], curses.color_pair(2))
            self.stdscr.attroff(curses.color_pair(2))

        instruction_parts = [T['instructions_nav'],
                             T['instructions_play'], T['instructions_quit']]
        if "Stations" in title or "Zenders" in title:
            instruction_parts.append(T['instructions_back'])

        instr_str = " | ".join(instruction_parts)
        self.stdscr.addstr(h - 1, 0, instr_str[:w-1])

        self.stdscr.refresh()

    def show_error(self, msg: str):
        self.stdscr.clear()
        self.stdscr.addstr(2, 2, f"{T['error_prefix']}{msg}")
        self.stdscr.addstr(4, 2, T['press_quit'])
        self.stdscr.refresh()
        self.stdscr.getch()

    def run_station_menu(self, genre_name: str, stations: List[Dict]):
        current_row = 0
        scroll_offset = 0
        station_names = [s.get('name', 'Unknown')
                         for s in stations if isinstance(s, dict)]

        if not station_names:
            self.show_error(T['no_stations'].format(genre_name=genre_name))
            return

        self.stdscr.timeout(100)

        while True:
            h, w = self.stdscr.getmaxyx()
            max_items = h - 4

            self.draw_menu(
                T['stations_in'].format(genre_name=genre_name),
                station_names,
                current_row,
                scroll_offset
            )

            key = self.stdscr.getch()

            if key == -1:
                self.update_player_status()
                continue

            if key == curses.KEY_UP:
                if current_row > 0:
                    current_row -= 1
                    if current_row < scroll_offset:
                        scroll_offset = current_row
            elif key == curses.KEY_DOWN:
                if current_row < len(station_names) - 1:
                    current_row += 1
                    if current_row >= scroll_offset + max_items:
                        scroll_offset += 1
            elif key in [ord('b'), ord('B')]:
                self.stop_player()
                break
            elif key in [ord('q'), ord('Q')]:
                self.stop_player()
                return 'quit'
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_name = station_names[current_row]

                if self.current_station_name == selected_name and self.player_process:
                    self.stop_player()
                    self.current_station_name = selected_name
                else:
                    selected_station = next(
                        (s for s in stations if s.get('name') == selected_name), None)
                    if selected_station and selected_station.get('url'):
                        self.play_stream(
                            selected_station['url'], selected_name)
                    else:
                        self.stdscr.timeout(-1)
                        self.show_error(T['stream_error'].format(
                            station_name=selected_name))
                        self.stdscr.timeout(100)

        self.stdscr.timeout(-1)

    def run(self):
        if not self.check_dependencies():
            return

        self.stdscr.clear()
        self.stdscr.addstr(0, 0, T['fetching'])
        self.stdscr.refresh()

        data = self.fetch_data()
        if "error" in data:
            self.show_error(data['error'])
            return

        self.data = data
        genres = list(self.data.keys())
        current_row = 0
        scroll_offset = 0

        while True:
            h, w = self.stdscr.getmaxyx()
            max_items = h - 4

            self.draw_menu(T['select_genre'], genres,
                           current_row, scroll_offset)

            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                if current_row > 0:
                    current_row -= 1
                    if current_row < scroll_offset:
                        scroll_offset = current_row
            elif key == curses.KEY_DOWN:
                if current_row < len(genres) - 1:
                    current_row += 1
                    if current_row >= scroll_offset + max_items:
                        scroll_offset += 1
            elif key in [ord('q'), ord('Q')]:
                break
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_genre = genres[current_row]
                stations = self.data[selected_genre]

                if isinstance(stations, list):
                    result = self.run_station_menu(selected_genre, stations)
                    if result == 'quit':
                        break
                else:
                    self.show_error(T['invalid_genre'].format(
                        genre_name=selected_genre))

        self.stop_player()


def main(stdscr):
    app = RadioApp(stdscr)
    app.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")
