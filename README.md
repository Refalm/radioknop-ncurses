# RADIOKNOP NCurses TUI

A terminal-based application to browse and play radio stations from [radioknop.nl](https://www.radioknop.nl)

![Scherm­afbeelding 2025-12-24 om 16 07 55](https://github.com/user-attachments/assets/23a6534c-8cb0-4a0b-a899-b57390a1f214)

![Scherm­afbeelding 2025-12-24 om 16 07 06](https://github.com/user-attachments/assets/5185c8be-26ce-4aa7-b793-8b5141349df0)

## Installation & Usage

This project uses a `Makefile` to simplify setup and execution.

1. **Install dependencies:**
    This command will install mpv and Python.

    ```shell
    make install
    ```

2. **Run the application:**
    This command will start the TUI application.

    ```shell
    make run
    ```

### Manual Setup (Alternative)

If you prefer not to use `make`, you can follow these steps:

1. Install mpv and Python

    Refer to your distribution documentation on how to install mpv and Python.

2. Run the application:

    ```shell
    python3 radioknop_tui.py
    ```

### Windows

Maybe if you

- [install windows-curses](https://pypi.org/project/windows-curses/)
- [install mpv with Chocolatey](https://community.chocolatey.org/packages/mpvio)

it might work, but I want to stay away from Windows as much as possible, so let me know if that actually works.
