#!/bin/zsh
# Double-click this file on macOS to launch the voice assistant
cd "$(dirname "$0")"
source venv/bin/activate
./venv/bin/python -m streamlit run main.py
