#!/usr/bin/env python3
import curses
import json
import locale
import requests
import subprocess
import time
import os
import tempfile
import shutil

TRANSLATIONS = {
    'en': {
        'fetching': "RADIOKNOP TUI - Fetching data...",
        'error_prefix': "Error: ",
        'press_quit': "Press any key to quit.",
        'select_genre': "Select a Genre",
        'stations_in': "Stations in '{genre_name}'",
        'no_stations': "No stations found for '{genre_name}'.",
        'press_back': "Press any key to go back...",
        'playing': "Playing: {station_name}",
        'stopped': "Stopped: {station_name}",
        'stream_error': "Error: Could not find stream URL for '{station_name}'.",
        'press_continue': "Press any key to continue...",
        'invalid_genre': "'{genre_name}' is not a valid genre category.",
        'instructions_nav': "[↑] [↓] Navigate",
        'instructions_play': "[⏎ Enter]: Play/Stop",
        'instructions_quit': "[Q] Quit",
        'instructions_back': "[B] Back",
        'network_error': "Network error: {e}",
        'parse_error': "Failed to parse API response.",
        'generic_error': "An error occurred: {e}",
        'terminal_size_error': "Please ensure your terminal window is large enough.",
        'mpv_not_found': "Error: 'mpv' is not installed. Refer to the README for installation instructions."
    },
    'nl': {
        'fetching': "RADIOKNOP TUI - Gegevens ophalen...",
        'error_prefix': "Fout: ",
        'press_quit': "Druk op een toets om af te sluiten.",
        'select_genre': "Selecteer een Genre",
        'stations_in': "Zenders in '{genre_name}'",
        'no_stations': "Geen zenders gevonden voor '{genre_name}'.",
        'press_back': "Druk op een toets om terug te gaan...",
        'playing': "Speelt nu: {station_name}",
        'stopped': "Gestopt: {station_name}",
        'stream_error': "Fout: Kon geen stream-URL vinden voor '{station_name}'.",
        'press_continue': "Druk op een toets om verder te gaan...",
        'invalid_genre': "'{genre_name}' is geen geldige genrecategorie.",
        'instructions_nav': "[↑] [↓] Navigeren",
        'instructions_play': "[⏎ Enter] Afspelen/Stoppen",
        'instructions_quit': "[Q] Afsluiten",
        'instructions_back': "[B] Terug",
        'network_error': "Netwerkfout: {e}",
        'parse_error': "API-respons kon niet worden verwerkt.",
        'generic_error': "Er is een fout opgetreden: {e}",
        'terminal_size_error': "Zorg ervoor dat je terminalvenster groot genoeg is.",
        'mpv_not_found': "Fout: 'mpv' is niet geïnstalleerd. Lees de README voor instructies om het te installeren."
    }
}


def get_lang():
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

API_URL = "https://www.radioknop.nl/api.php"
CACHE_DIR = tempfile.gettempdir()
CACHE_FILE = os.path.join(CACHE_DIR, "radioknop_cache.json")
CACHE_DURATION = 24 * 60 * 60


def fetch_data():
    if os.path.exists(CACHE_FILE):
        try:
            cache_age = time.time() - os.path.getmtime(CACHE_FILE)
            if cache_age < CACHE_DURATION:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError):
            pass

    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = json.loads(response.text)

        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f)
        except IOError:
            pass

        return data
    except requests.exceptions.RequestException as e:
        return {"error": T['network_error'].format(e=e)}
    except json.JSONDecodeError:
        return {"error": T['parse_error']}


player_process = None


def play_stream(stream_url):
    global player_process
    if player_process:
        player_process.terminate()
        player_process.wait()

    try:
        player_process = subprocess.Popen(
            ["mpv", "--no-video", stream_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        player_process = None


def stop_player():
    global player_process
    if player_process:
        player_process.terminate()
        player_process.wait()
        player_process = None


def draw_menu(stdscr, title, items, current_row, scroll_offset, playing_info="", playing_item_name=None):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    if w == 0 or h == 0:
        return

    stdscr.attron(curses.color_pair(2))
    stdscr.addstr(0, 0, title.ljust(w)[:w - 1], curses.color_pair(2))
    stdscr.attroff(curses.color_pair(2))

    max_items = h - 5
    if max_items < 1:
        pass
    else:
        has_scrollbar = len(items) > max_items

        for i, item in enumerate(items[scroll_offset:scroll_offset + max_items]):
            actual_index = i + scroll_offset
            display_text = item
            if item == playing_item_name:
                display_text += f" [{T['playing'].split(':')[0]}]"

            margin = 7 if has_scrollbar else 4
            max_len = w - margin
            if max_len < 0:
                max_len = 0
            display_text = display_text[:max_len]

            line_num = i + 2
            if actual_index == current_row:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(line_num, 2, f"> {display_text}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(line_num, 2, f"  {display_text}")

        if has_scrollbar:
            scrollbar_height = max_items
            handle_height = max(
                1, round(scrollbar_height * max_items / len(items)))

            scroll_range = len(items) - max_items
            track_space = scrollbar_height - handle_height
            scroll_percent = scroll_offset / scroll_range if scroll_range > 0 else 0
            handle_y = round(scroll_percent * track_space)

            for i in range(scrollbar_height):
                char = '█' if i >= handle_y and i < handle_y + handle_height else '│'
                try:
                    stdscr.addstr(i + 2, w - 2, char)
                except curses.error:
                    pass

    instruction_parts = [
        T['instructions_nav'],
        T['instructions_play'],
        T['instructions_quit']
    ]
    if "Stations" in title or "Zenders" in title:
        instruction_parts.append(T['instructions_back'])
    instructions = " | ".join(instruction_parts)

    if h > 3:
        stdscr.addstr(h - 3, 2, instructions[:w - 4])

    if playing_info and h > 1:
        stdscr.attron(curses.color_pair(2))
        stdscr.addstr(h - 1, 0, playing_info.ljust(w)
                      [:w - 1], curses.color_pair(2))
        stdscr.attroff(curses.color_pair(2))

    stdscr.refresh()


def station_menu(stdscr, genre_name, stations):
    current_row = 0
    scroll_offset = 0
    station_names = [s.get('name')
                     for s in stations if isinstance(s, dict) and s.get('name')]

    if not station_names:
        stdscr.clear()
        stdscr.addstr(2, 2, T['no_stations'].format(genre_name=genre_name))
        stdscr.addstr(4, 2, T['press_back'])
        stdscr.refresh()
        stdscr.getch()
        return

    playing_info = ""
    currently_playing_name = None

    while True:
        h, w = stdscr.getmaxyx()
        max_items = h - 5
        if max_items < 1:
            max_items = 1

        title = T['stations_in'].format(genre_name=genre_name)
        draw_menu(stdscr, title, station_names, current_row, scroll_offset,
                  playing_info, playing_item_name=currently_playing_name)

        key = stdscr.getch()

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
        elif key == ord('b'):
            stop_player()
            break
        elif key == ord('q'):
            stop_player()
            return 'quit'
        elif key in [curses.KEY_ENTER, 10, 13]:
            selected_station_name = station_names[current_row]

            if currently_playing_name == selected_station_name:
                stop_player()
                playing_info = T['stopped'].format(
                    station_name=selected_station_name)
                currently_playing_name = None
            else:
                selected_station = next(
                    (s for s in stations if s.get('name') == selected_station_name), None)

                if selected_station and selected_station.get('url'):
                    play_stream(selected_station['url'])
                    playing_info = T['playing'].format(
                        station_name=selected_station['name'])
                    currently_playing_name = selected_station['name']
                else:
                    stdscr.clear()
                    stdscr.addstr(
                        2, 2, T['stream_error'].format(station_name=selected_station_name))
                    stdscr.addstr(4, 2, T['press_continue'])
                    stdscr.refresh()
                    stdscr.getch()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)

    if shutil.which("mpv") is None:
        stdscr.clear()
        error_message = T['mpv_not_found']
        quit_message = T['press_quit']

        h, w = stdscr.getmaxyx()
        y = h // 2
        x_error = w // 2 - len(error_message) // 2
        x_quit = w // 2 - len(quit_message) // 2

        stdscr.addstr(y - 1, x_error, error_message)
        stdscr.addstr(y + 1, x_quit, quit_message)

        stdscr.refresh()
        stdscr.getch()
        return

    stdscr.addstr(0, 0, T['fetching'])
    stdscr.refresh()

    data = fetch_data()

    if "error" in data:
        stdscr.clear()
        stdscr.addstr(0, 0, f"{T['error_prefix']}{data['error']}")
        stdscr.addstr(2, 0, T['press_quit'])
        stdscr.refresh()
        stdscr.getch()
        return

    genres = list(data.keys())
    current_row = 0
    scroll_offset = 0

    while True:
        h, w = stdscr.getmaxyx()
        max_items = h - 5
        if max_items < 1:
            max_items = 1

        draw_menu(stdscr, T['select_genre'], genres,
                  current_row, scroll_offset)

        key = stdscr.getch()

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
        elif key == ord('q'):
            break
        elif key in [curses.KEY_ENTER, 10, 13]:
            selected_genre = genres[current_row]
            stations = data[selected_genre]
            if isinstance(stations, list):
                if station_menu(stdscr, selected_genre, stations) == 'quit':
                    break
            else:
                stdscr.clear()
                stdscr.addstr(
                    2, 2, T['invalid_genre'].format(genre_name=selected_genre))
                stdscr.addstr(4, 2, T['press_continue'])
                stdscr.refresh()
                stdscr.getch()

    stop_player()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(T['generic_error'].format(e=e))
        print(T['terminal_size_error'])
