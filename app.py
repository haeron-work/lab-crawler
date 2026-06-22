"""
app.py — Flask API server for SNU Faculty Explorer
Run: python app.py
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import database
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)


# ─── Static ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ─── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/professors')
def get_professors():
    filters = {
        'college':    request.args.get('college'),
        'department': request.args.get('department'),
        'keyword':    request.args.get('keyword'),
        'search':     request.args.get('search'),
        'sort':       request.args.get('sort', 'name_kr'),
        'position':   request.args.get('position'),
    }
    profs = database.get_professors(filters)
    return jsonify(profs)


@app.route('/api/professors/<int:prof_id>')
def get_professor(prof_id):
    prof = database.get_professor_detail(prof_id)
    if not prof:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(prof)


@app.route('/api/keywords')
def get_keywords():
    return jsonify(database.get_all_keywords())


@app.route('/api/colleges')
def get_colleges():
    return jsonify(database.get_colleges())


@app.route('/api/stats')
def get_stats():
    return jsonify(database.get_stats())


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    database.init_db()
    port = int(os.environ.get('PORT', 5050))
    print(f'''
╔══════════════════════════════════════════════╗
║   SNU Faculty Explorer                       ║
║   http://localhost:{port}                      ║
╚══════════════════════════════════════════════╝
''')
    app.run(debug=True, port=port, host='127.0.0.1')
