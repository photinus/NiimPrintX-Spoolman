.DEFAULT_GOAL := help

PYTHON ?= $(shell command -v python3.12 || command -v python3.13 || command -v python3.14 || command -v python3)
VENV ?= .venv314
PYTHON_BIN := $(VENV)/bin/python
PIP := $(PYTHON_BIN) -m pip
BREW_PREFIX := $(shell command -v brew >/dev/null 2>&1 && brew --prefix || true)
CAIRO_PKG_CONFIG := $(shell command -v brew >/dev/null 2>&1 && brew --prefix cairo 2>/dev/null)/lib/pkgconfig
PKG_CONFIG_PATH := $(CAIRO_PKG_CONFIG):$(PKG_CONFIG_PATH)
UI_DEPS := appdirs loguru pillow pycairo devtools bleak

.PHONY: help macos-deps setup setup-full run-ui ui gui scan-b1 inspect-b1 rfid-b1 doctor clean-venv

help:
	@printf "NiimPrintX local commands\n\n"
	@printf "  make macos-deps  Install macOS UI build dependencies with Homebrew\n"
	@printf "  make setup       Create $(VENV) and install GUI dependencies\n"
	@printf "  make setup-full  Install pinned requirements.txt dependencies\n"
	@printf "  make run-ui      Start the graphical app\n"
	@printf "  make scan-b1     Scan for a B1 printer over Bluetooth\n"
	@printf "  make inspect-b1  Print B1 Bluetooth services and characteristics\n"
	@printf "  make rfid-b1     Read B1 roll/RFID data when available\n"
	@printf "  make doctor      Check Python and Tk availability\n"
	@printf "  make clean-venv  Remove $(VENV)\n"

macos-deps:
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "Homebrew is required for macOS native dependencies."; \
		exit 1; \
	fi
	brew install pkg-config cairo python-tk@3.14

$(PYTHON_BIN):
	@if [ -z "$(PYTHON)" ]; then \
		echo "No python3 interpreter found."; \
		exit 1; \
	fi
	$(PYTHON) -m venv $(VENV)

setup: $(PYTHON_BIN)
	$(PIP) install --upgrade pip setuptools wheel
	PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" $(PIP) install $(UI_DEPS)

setup-full: $(PYTHON_BIN)
	$(PIP) install --upgrade pip setuptools wheel
	PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" $(PIP) install -r requirements.txt

run-ui: setup
	PYTHONPATH=. $(PYTHON_BIN) -m NiimPrintX.ui

ui: run-ui

gui: run-ui

scan-b1: setup
	PYTHONPATH=. $(PYTHON_BIN) -c 'import asyncio; from NiimPrintX.nimmy.bluetooth import find_device; device = asyncio.run(find_device("b1")); print("{} {}".format(device.name, device.address))'

inspect-b1: setup
	PYTHONPATH=. $(PYTHON_BIN) bin/inspect_bluetooth.py b1

rfid-b1: setup
	PYTHONPATH=. $(PYTHON_BIN) bin/inspect_rfid.py b1

doctor:
	@echo "PYTHON=$(PYTHON)"
	@$(PYTHON) --version
	@$(PYTHON) -c 'import tkinter as tk; root = tk.Tk(); print("Tk={}".format(root.tk.call("info", "patchlevel"))); root.destroy()'

clean-venv:
	rm -rf $(VENV)
