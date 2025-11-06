"""
Flask app: Lista de Materiais para Instalação de Placas Solares (local e acessível por celular)
- Rodar localmente e acessível via rede Wi-Fi (host=0.0.0.0)
- SQLite para histórico
- Gera PDF com layout visual mais bonito (ReportLab)
- Permite upload de logo (opcional)
- Fornece link de WhatsApp com mensagem pré-preenchida (não anexa o PDF automaticamente)

Dependências:
    pip install Flask reportlab - OK

Como rodar:
    python flask_solar_materials_app.py

Abra no navegador:
    - Computador: http://192.168.100.139:5000
    - Celular (mesma rede Wi-Fi): http://SEU_IP_LOCAL:5000

Para descobrir seu IP local (Windows): ipconfig
Para Linux/Mac: ifconfig
"""

import os
import sqlite3
import json
from datetime import datetime
from urllib.parse import quote
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, send_file,
    flash, g
)

from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PDF_FOLDER = os.path.join(BASE_DIR, 'pdfs')
DB_PATH = os.path.join(BASE_DIR, 'history.db')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

app = Flask(__name__)
# Carrega os materiais do arquivo JSON
with open("materials.json", "r", encoding="utf-8") as f:
    materials = json.load(f)

# --- Leitura da configuração da empresa ---
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {
        "company_name": "Sua Empresa",
        "logo_path": None
    }

# --- DB helpers ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            technician TEXT,
            date TEXT,
            items TEXT,
            pdf_path TEXT
        )
    ''')
    db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Utilities ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_pdf(list_id, client, technician, items, company_name='Sua Empresa', logo_path=None):
    now = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f'lista_{list_id}_{now}.pdf'
    filepath = os.path.join(PDF_FOLDER, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Cabeçalho
    if logo_path and os.path.exists(logo_path):
        elements.append(Image(logo_path, width=4*cm, height=2*cm))
        elements.append(Spacer(1, 0.3*cm))

    title = Paragraph(f'<b>{company_name}</b>', styles['Title'])
    info = Paragraph(f'<b>Cliente:</b> {client}<br/><b>Responsável técnico:</b> {technician}<br/><b>Data de emissão:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal'])

    elements.extend([title, Spacer(1, 0.2*cm), info, Spacer(1, 0.5*cm)])

    # Tabela de materiais
    data = [['CÓDIGO', 'DESCRIÇÃO', 'QTD', 'UN']]
    for it in items:
        data.append([it['code'], it['name'], str(it['qty']), it['unit']])

    table = Table(data, colWidths=[4*cm, 8*cm, 2*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#00796B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('BOTTOMPADDING',(0,0),(-1,0),8),
        ('BACKGROUND',(0,1),(-1,-1),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)
    return filepath

# --- Rotas principais ---
@app.route('/')
def index():
    return render_template(
        'index.html',
        materials=materials,
        company_name=CONFIG["company_name"],
        logo_path=CONFIG["logo_path"]
    )


@app.route('/create', methods=['POST'])
def create():
    client = request.form['client']
    technician = request.form['technician']
    company_name = request.form.get('company_name', 'Sua Empresa')

    count = int(request.form.get('count', 0))
    items = []

    # Materiais fixos
    for i in range(count):
        qty = request.form.get(f'qty_{i}')
        if qty and float(qty) > 0:
            items.append({
                'code': request.form[f'code_{i}'],
                'name': request.form[f'name_{i}'],
                'unit': request.form[f'unit_{i}'],
                'qty': float(qty)
            })

    # Materiais adicionados dinamicamente
    for key in request.form:
        if key.startswith('code_extra_'):
            suffix = key.replace('code_extra_', '')
            qty = request.form.get(f'qty_extra_{suffix}')
            if qty and float(qty) > 0:
                items.append({
                    'code': request.form[f'code_extra_{suffix}'],
                    'name': request.form[f'name_extra_{suffix}'],
                    'unit': request.form[f'unit_extra_{suffix}'],
                    'qty': float(qty)
                })


    # Monta lista de itens
    items = []
    for i in range(int(request.form['count'])):
        qty = request.form.get(f'qty_{i}')
        if qty and int(qty) > 0:
            items.append({
                'code': request.form[f'code_{i}'],
                'name': request.form[f'name_{i}'],
                'unit': request.form[f'unit_{i}'],
                'qty': int(qty)
            })

    # Salva no banco
    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO lists (client, technician, date, items, pdf_path) VALUES (?, ?, ?, ?, ?)',
                (client, technician, datetime.now().isoformat(), json.dumps(items), ''))
    db.commit()
    list_id = cur.lastrowid

    # Gera PDF
    pdf_path = generate_pdf(
    list_id,
    client,
    technician,
    items,
    company_name=CONFIG["company_name"],
    logo_path=CONFIG["logo_path"]
)
    db.execute('UPDATE lists SET pdf_path = ? WHERE id = ?', (pdf_path, list_id))
    db.commit()

    flash('PDF gerado e salvo com sucesso!')
    return redirect(url_for('history'))

@app.route('/history')
def history():
    db = get_db()
    rows = db.execute('SELECT * FROM lists ORDER BY id DESC').fetchall()
    return render_template('history.html', listas=rows, company_name=CONFIG["company_name"], logo_path=CONFIG["logo_path"])

@app.route('/download/<int:list_id>')
def download_pdf(list_id):
    db = get_db()
    l = db.execute('SELECT pdf_path FROM lists WHERE id = ?', (list_id,)).fetchone()
    if l and os.path.exists(l['pdf_path']):
        return send_file(l['pdf_path'], as_attachment=True)
    flash('Arquivo PDF não encontrado!')
    return redirect(url_for('history'))

@app.route('/whatsapp/<int:list_id>')
def whatsapp_msg(list_id):
    db = get_db()
    l = db.execute('SELECT client, technician FROM lists WHERE id = ?', (list_id,)).fetchone()
    if not l:
        flash('Lista não encontrada!')
        return redirect(url_for('history'))
    msg = f"Lista de materiais pronta para o cliente {l['client']}.\nResponsável técnico: {l['technician']}."
    wa_link = f"https://wa.me/?text={quote(msg)}"
    return redirect(wa_link)

@app.route('/delete/<int:list_id>')
def delete(list_id):
    db = get_db()
    db.execute('DELETE FROM lists WHERE id = ?', (list_id,))
    db.commit()
    flash('Registro excluído.')
    return redirect(url_for('history'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    # Permite acesso por celular na mesma rede Wi-Fi
    app.run(host='0.0.0.0', port=5000, debug=True)
