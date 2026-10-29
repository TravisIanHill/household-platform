#!/bin/bash
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo 'Python 3 is required. Install Python 3 from python.org, then reopen this launcher.'
  read -r -p 'Press Return to close.'
  exit 1
fi
python3 catalog.py
read -r -p 'Press Return to close.'
