# Makefile for radioknop-ncurses

# Define the virtual environment directory
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python

.PHONY: all install run clean help

all: help

help:
	@echo "Available commands:"
	@echo "  make install - Detects OS, installs dependencies, and creates a virtual environment"
	@echo "  make run     - Runs the application"
	@echo "  make clean   - Removes the virtual environment"

install:
	@echo ">>> Detecting OS and installing system dependencies (mpv, python3)..."
	@if [ -f /etc/os-release ]; then \
		. /etc/os-release; \
		if [[ "$$ID" = "bazzite" || "$$ID" = "aurora" || "$$ID" = "bluefin" ]]; then \
			OS_ID="$$ID"; \
		else \
			OS_ID=$${ID_LIKE:-$${ID}}; \
		fi; \
	elif [ "$$(uname -s)" = "Darwin" ]; then \
		OS_ID="macos"; \
	else \
		OS_ID="unknown"; \
	fi; \
	case "$$OS_ID" in \
		debian|ubuntu) \
			echo ">>> Detected Debian-based system. Trying to install dependencies..."; \
			sudo apt-get update && sudo apt-get install -y mpv python3-pip python3-venv; \
			;; \
		fedora|rhel|centos) \
			echo ">>> Detected Red Hat-based system. Trying to install dependencies..."; \
			sudo dnf install -y mpv python3-pip; \
			;; \
		bazzite|aurora|bluefin) \
			echo ">>> Detected Universal Blue-based system. Checking for dependencies..."; \
			TO_INSTALL=""; \
			for pkg in mpv python3-pip; do \
				if ! rpm -q $$pkg >/dev/null 2>&1; then \
					TO_INSTALL="$$TO_INSTALL $$pkg"; \
				fi; \
			done; \
			if [ -n "$$TO_INSTALL" ]; then \
				echo ">>> Installing missing packages:$$TO_INSTALL"; \
				echo "    Note: This will layer new packages. A system reboot may be required for them to become available."; \
				rpm-ostree install --idempotent $$TO_INSTALL; \
			else \
				echo ">>> All required dependencies are already installed."; \
			fi; \
			;; \
		arch) \
			echo ">>> Detected Arch-based system. Trying to install dependencies..."; \
			sudo pacman -Syu --noconfirm mpv python-pip; \
			;; \
		opensuse|suse) \
			echo ">>> Detected SUSE-based system. Trying to install dependencies..."; \
			sudo zypper -n install mpv python-pip; \
			;; \
		alpine) \
			echo ">>> Detected Alpine-based system. Trying to install dependencies..."; \
			sudo apk add mpv python3 py3-pip; \
			;; \
		slackware) \
			echo ">>> Detected Slackware-based system. Trying to install dependencies..."; \
			sudo sbopkg -i mpv; \
			;; \
		macos) \
			echo ">>> Detected macOS. Trying to install dependencies with Homebrew..."; \
			if ! command -v brew >/dev/null 2>&1; then \
				echo "Homebrew not found. Please install it from https://brew.sh/" && exit 1; \
			fi; \
			brew install mpv python3; \
			;; \
		*) \
			echo ">>> WARNING: OS '$$OS_ID' not automatically supported. Please ensure 'mpv' and 'python3' are installed manually."; \
			;; \
	esac
	@echo ">>> Proceeding with virtual environment setup."
	@$(MAKE) $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: requirements.txt
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo ">>> Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
	fi
	@echo ">>> Installing dependencies..."
	@$(PYTHON) -m pip install -r requirements.txt
	@touch $(VENV_DIR)/bin/activate

run: $(VENV_DIR)/bin/activate
	@echo ">>> Starting radioknop-ncurses..."
	@$(PYTHON) radioknop_tui.py

clean:
	@echo ">>> Cleaning up..."
	@rm -rf $(VENV_DIR)
	@echo ">>> Done."

