#!/usr/bin/env bash
# SNU Faculty Explorer — Quick start

echo """
╔══════════════════════════════════════════════════════════════╗
║          SNU Faculty Explorer — Setup & Run                 ║
╚══════════════════════════════════════════════════════════════╝
"""

# Check Python
python_cmd=$(command -v python3 || command -v python)
if [ -z "$python_cmd" ]; then
  echo "❌ Python 3 not found. Please install Python 3.9+"
  exit 1
fi

echo "✓ Python: $($python_cmd --version)"

# Create venv
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment…"
  $python_cmd -m venv venv
fi

# Activate venv
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "📥 Installing dependencies…"
pip install -r requirements.txt -q

echo """

╔══════════════════════════════════════════════════════════════╗
║  Ready! Choose one:                                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Crawl all departments (slow, ~30 min):                      ║
║    python crawler.py                                         ║
║                                                              ║
║  Crawl specific departments (e.g. EE, CSE, MSE):            ║
║    python crawler.py --dept ee,cse,mse                      ║
║                                                              ║
║  Crawl without fetching papers (faster):                     ║
║    python crawler.py --no-papers                             ║
║                                                              ║
║  List available departments:                                 ║
║    python crawler.py --list                                 ║
║                                                              ║
║  Then run the web server:                                    ║
║    python app.py                                             ║
║    → http://localhost:5050                                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

"""
