# Makefile for radioknop-ncurses

PYTHON = python3
SCRIPT_NAME = radioknop_tui.py
SHELL := /bin/bash

.PHONY: all install run help

all: help

help:
	@echo "Available commands:"
	@echo "  make install - Installs dependencies (mpv, python3)"
	@echo "  make run     - Runs the application"

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
			echo ">>> Detected Debian/Ubuntu-based system..."; \
			sudo apt-get update && sudo apt-get install -y mpv python3; \
			;; \
		fedora|rhel|centos) \
			echo ">>> Detected Fedora/RHEL-based system..."; \
			sudo dnf install -y mpv python3; \
			;; \
		bazzite|aurora|bluefin) \
			echo ">>> Detected Atomic/Universal Blue system..."; \
			TO_INSTALL=""; \
			for pkg in mpv python3; do \
				if ! rpm -q $$pkg >/dev/null 2>&1; then \
					TO_INSTALL="$$TO_INSTALL $$pkg"; \
				fi; \
			done; \
			if [ -n "$$TO_INSTALL" ]; then \
				echo ">>> Installing missing packages:$$TO_INSTALL"; \
				echo "    Note: A system reboot may be required after installation."; \
				rpm-ostree install --idempotent $$TO_INSTALL; \
			else \
				echo ">>> All dependencies already installed."; \
			fi; \
			;; \
		arch|manjaro) \
			echo ">>> Detected Arch-based system..."; \
			sudo pacman -S --needed --noconfirm mpv python; \
			;; \
		opensuse*|suse|gecko) \
			echo ">>> Detected SUSE-based system..."; \
			sudo zypper -n install mpv python3; \
			;; \
		alpine) \
			echo ">>> Detected Alpine Linux..."; \
			sudo apk add mpv python3; \
			;; \
		macos) \
			echo ">>> Detected macOS..."; \
			if ! command -v brew >/dev/null 2>&1; then \
				echo "Homebrew not found. Install from https://brew.sh/" && exit 1; \
			fi; \
			brew install mpv python3; \
			;; \
		*) \
			echo ">>> WARNING: OS '$$OS_ID' not automatically supported."; \
			echo ">>> Please install 'mpv' and 'python3' manually."; \
			;; \
	esac

run:
	@if [ ! -f $(SCRIPT_NAME) ]; then \
		echo "Error: $(SCRIPT_NAME) not found!"; \
		exit 1; \
	fi
	@echo ">>> Starting RadioKnop TUI..."
	@$(PYTHON) $(SCRIPT_NAME)
