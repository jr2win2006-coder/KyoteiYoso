#!/bin/bash
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/anaconda3/bin:$HOME/miniconda3/bin:$PATH"

if [ -f "$HOME/venv/bin/activate" ]; then
    source "$HOME/venv/bin/activate"
fi

if command -v streamlit &> /dev/null; then
    streamlit run KyoteiYoso.py
else
    python3 -m streamlit run KyoteiYoso.py
fi
