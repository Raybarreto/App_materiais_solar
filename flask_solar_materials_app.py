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
app.secret_key = os.urandom(24)

# Carrega materiais do JSON
with open("materials.json", "r", encoding="utf-8") as f:
    materials = json.load(f)

# --- Definição dos Kits Prontos ---
KITS = {
    "Kit 3 KWp - Básico": [
        {"name": "Painel Solar 550W", "code": "PNL550", "qty": 6, "unit": "un"},
        {"name": "Inversor 3KW", "code": "INV003", "qty": 1, "unit": "un"},
        {"name": "Cabo Solar 6mm Vermelho", "code": "CABV6", "qty": 50, "unit": "m"},
        {"name": "Cabo Solar 6mm Preto", "code": "CABP6", "qty": 50, "unit": "m"},
        {"name": "Conector MC4 Par", "code": "MC4PAR", "qty": 4, "unit": "par"},
        {"name": "Estrutura de Fixação Telhado", "code": "ESTTEL", "qty": 1, "unit": "cj"},
        {"name": "String Box CC", "code": "STRBX1", "qty": 1, "unit": "un"}
    ],
    "Kit 5 KWp - Intermediário": [
        {"name": "Painel Solar 550W", "code": "PNL550", "qty": 10, "unit": "un"},
        {"name": "Inversor 5KW", "code": "INV005", "qty": 1, "unit": "un"},
        {"name": "Cabo Solar 6mm Vermelho", "code": "CABV6", "qty": 80, "unit": "m"},
        {"name": "Cabo Solar 6mm Preto", "code": "CABP6", "qty": 80, "unit": "m"},
        {"name": "Conector MC4 Par", "code": "MC4PAR", "qty": 6, "unit": "par"},
        {"name": "Estrutura de Fixação Solo", "code": "ESTSOL", "qty": 1, "unit": "cj"},
        {"name": "String Box CC/CA", "code": "STRBX2", "qty": 1, "unit": "un"}
    ]
}

CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {"company_name": "Sua Empresa", "logo_path": None}

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

def generate_pdf(list_id, client, technician, items, company_name='Sua Empresa', logo_path=None):
    now = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f'lista_{list_id}_{now}.pdf'
    filepath = os.path.join(PDF_FOLDER, filename)

    # Margens ajustadas
    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    elements = []
    
    # --- 1. Cabeçalho ---
    if logo_path and os.path.exists(logo_path):
        elements.append(Image(logo_path, width=5*cm, height=2.5*cm))
        elements.append(Spacer(1, 0.3*cm))

    title = Paragraph(f'<b>{company_name}</b>', styles['Title'])
    
    # Informações do Projeto
    info_text = f'''
    <b>Cliente:</b> {client}<br/>
    <b>Responsável técnico:</b> {technician}<br/>
    <b>Data de emissão:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}
    '''
    info = Paragraph(info_text, styles['Normal'])
    
    elements.extend([title, Spacer(1, 0.5*cm), info, Spacer(1, 0.5*cm)])

    # --- 2. Tabela de Materiais ---
    data = [['CÓDIGO', 'DESCRIÇÃO', 'QTD', 'UN']]
    if items:
        for it in items:
            try:
                q_val = float(it.get('qty', 0))
                qty_str = f"{int(q_val)}" if q_val.is_integer() else f"{q_val}".replace('.', ',')
            except:
                qty_str = str(it.get('qty', 0))

            descricao_paragrafo = Paragraph(it.get('name', 'N/A'), styleN)
            data.append([
                it.get('code', ''), 
                descricao_paragrafo,
                qty_str, 
                it.get('unit', '')
            ])

    # Larguras das colunas ajustadas para A4
    col_widths = [3.5*cm, 10.5*cm, 2*cm, 2*cm]
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8C42')), 
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'), 
        ('ALIGN',(1,0),(-1,-1),'LEFT'),   
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('BOTTOMPADDING',(0,0),(-1,0),8),
        ('BACKGROUND',(0,1),(-1,-1),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    elements.append(table)

    # --- 3. Área de Assinaturas ---
    elements.append(Spacer(1, 2.5*cm))    
    ass_data = [
        ["___________________________________", "___________________________________"],
        ["Responsável pela Separação/Entrega", "Técnico responsável pela retirada"],
        ["Data: ______/______/___________",    "CPF/RG: _______________________"]
    ]

    ass_table = Table(ass_data, colWidths=[9*cm, 9*cm])
    
    ass_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,1), (-1,1), 5), 
        ('LINEBELOW', (0,0), (-1,-1), 0, colors.white),
    ]))

    elements.append(ass_table)
    
    # Gera o PDF
    doc.build(elements)
    return filepath

@app.route('/')
def index():
    # Passamos 'kits' para o template
    return render_template('index.html', materials=materials, kits=KITS, company_name=CONFIG["company_name"])

@app.route('/create', methods=['POST'])
def create():
    client = request.form['client']
    technician = request.form['technician']
    items = []

    # Processa todos os itens (tanto manuais quanto de kits) usando a logica "extra"
    for key in request.form.keys():
        if key.startswith("qty_extra_"):
            unique_id = key.split("qty_extra_")[1]
            qty = request.form.get(key)
            
            if qty and float(qty) > 0:
                item = {
                    "code": request.form.get(f"code_extra_{unique_id}", ""),
                    "name": request.form.get(f"name_extra_{unique_id}", ""),
                    "unit": request.form.get(f"unit_extra_{unique_id}", ""),
                    "qty": float(qty)
                }
                items.append(item)

    if not items:
        flash('Nenhum material selecionado.', 'warning')
        return redirect(url_for('index')) 

    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO lists (client, technician, date, items, pdf_path) VALUES (?, ?, ?, ?, ?)',
                (client, technician, datetime.now().isoformat(), json.dumps(items), ''))
    db.commit()
    list_id = cur.lastrowid

    pdf_path = generate_pdf(list_id, client, technician, items, company_name=CONFIG["company_name"], logo_path=CONFIG["logo_path"])
    db.execute('UPDATE lists SET pdf_path = ? WHERE id = ?', (pdf_path, list_id))
    db.commit()

    flash('PDF gerado com sucesso!')
    return redirect(url_for('history'))

@app.route('/history')
def history():
    db = get_db()
    rows = db.execute('SELECT * FROM lists ORDER BY id DESC').fetchall()
    return render_template('history.html', listas=rows)

@app.route('/download/<int:list_id>')
def download_pdf(list_id):
    db = get_db()
    l = db.execute('SELECT pdf_path FROM lists WHERE id = ?', (list_id,)).fetchone()
    if l and os.path.exists(l['pdf_path']):
        return send_file(l['pdf_path'], as_attachment=True)
    flash('Arquivo não encontrado!')
    return redirect(url_for('history'))

@app.route('/whatsapp/<int:list_id>')
def whatsapp_msg(list_id):
    db = get_db()
    l = db.execute('SELECT client, technician FROM lists WHERE id = ?', (list_id,)).fetchone()
    if not l:
        return redirect(url_for('history'))
    msg = f"Olá! Segue a solicitação de materiais para o cliente {l['client']},\nsob responsabilidade técnica de {l['technician']}."
    return redirect(f"https://wa.me/?text={quote(msg)}")

@app.route('/delete/<int:list_id>')
def delete(list_id):
    db = get_db()
    db.execute('DELETE FROM lists WHERE id = ?', (list_id,))
    db.commit()
    flash('Registro excluído.')
    return redirect(url_for('history'))

# --- Rota de Relatórios com Filtros ---
@app.route('/relatorio')
def relatorio():
    db = get_db()
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = "SELECT items, date FROM lists"
    params = []

    # Se tiver datas selecionadas, filtra no SQL
    if start_date and end_date:
        query += " WHERE date >= ? AND date <= ?"
        params.append(start_date + "T00:00:00")
        params.append(end_date + "T23:59:59")
    
    # Executa a busca
    rows = db.execute(query, params).fetchall()
    
    totais = {}
    
    for row in rows:
        try:
            itens_lista = json.loads(row['items'])
            for item in itens_lista:
                nome = item.get('name', 'Sem Nome')
                try:
                    qtd = float(item.get('qty', 0))
                except ValueError:
                    qtd = 0
                
                if nome in totais:
                    totais[nome] += qtd
                else:
                    totais[nome] = qtd
        except:
            continue

    ranking = sorted(totais.items(), key=lambda x: x[1], reverse=True)
    
    data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    return render_template(
        'relatorio.html', 
        ranking=ranking, 
        data_geracao=data_geracao,
        start_date=start_date,
        end_date=end_date
    )

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
