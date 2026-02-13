#!/bin/bash
# Disk Analyzer GUI Launcher

echo "╔════════════════════════════════════════════════╗"
echo "║   Disk Usage Analyzer - Native GUI Edition    ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if Tkinter is installed
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "❌ ERROR: Python Tkinter not found!"
    echo ""
    echo "Installing Tkinter..."
    echo "Please run: sudo apt-get install python3-tk"
    echo ""
    exit 1
fi

# Launch the GUI
echo "✅ Launching Disk Analyzer..."
python3 "$(dirname "$0")/disk_analyzer_gui.py"
