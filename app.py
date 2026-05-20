from flask import Flask, render_template, request, redirect, session, send_file
import psycopg2
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cotacao123"

SENHA_RH = "rh123"


def conectar():
    """
    Conexão com PostgreSQL.

    No Render:
    - usa a variável de ambiente DATABASE_URL.

    No teu PC:
    - usa o PostgreSQL local.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host="localhost",
        database="cotacao_db",
        user="postgres",
        password="1234"
    )


def rh_autorizado():
    return session.get("rh_autorizado") == True


def init_db():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT,
        password TEXT,
        tipo TEXT DEFAULT 'normal'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotacoes (
        id SERIAL PRIMARY KEY,
        cliente TEXT,
        empresa TEXT,
        endereco TEXT,
        nuit TEXT,
        pagamento TEXT,
        prazo TEXT,
        nb TEXT,
        subtotal REAL,
        iva REAL,
        total REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_cotacao (
        id SERIAL PRIMARY KEY,
        cotacao_id INTEGER REFERENCES cotacoes(id) ON DELETE CASCADE,
        quantidade REAL,
        unidade TEXT,
        descricao TEXT,
        preco REAL,
        subtotal REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funcionarios (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        cargo TEXT,
        salario_hora REAL NOT NULL,
        telefone TEXT,
        estado TEXT DEFAULT 'Ativo'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folhas_salariais (
        id SERIAL PRIMARY KEY,
        funcionario_id INTEGER REFERENCES funcionarios(id) ON DELETE CASCADE,
        mes TEXT,
        ano INTEGER,
        horas_normais REAL DEFAULT 0,
        horas_extra_50 REAL DEFAULT 0,
        horas_extra_100 REAL DEFAULT 0,
        valor_horas_normais REAL DEFAULT 0,
        valor_extra_50 REAL DEFAULT 0,
        valor_extra_100 REAL DEFAULT 0,
        inss REAL DEFAULT 0,
        outros_descontos REAL DEFAULT 0,
        total_bruto REAL DEFAULT 0,
        total_liquido REAL DEFAULT 0,
        data_criacao TEXT
    )
    """)

    cursor.execute("SELECT * FROM usuarios")

    if not cursor.fetchall():
        cursor.execute("""
        INSERT INTO usuarios (username, password, tipo)
        VALUES (%s, %s, %s)
        """, ("admin", "1234", "admin"))

    conn.commit()
    conn.close()


init_db()


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, username, password, tipo
        FROM usuarios
        WHERE username=%s AND password=%s
        """, (username, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            session['tipo'] = user[3]
            session.pop("rh_autorizado", None)
            return redirect('/')

        return "Login inválido"

    return render_template("login.html")


@app.route('/')
def dashboard():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM cotacoes")
    total_cotacoes = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM cotacoes")
    total_gerado = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT cliente, total
    FROM cotacoes
    ORDER BY id DESC
    LIMIT 5
    """)
    ultimas_cotacoes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_cotacoes=total_cotacoes,
        total_gerado=round(total_gerado, 2),
        ultimas_cotacoes=ultimas_cotacoes
    )


@app.route('/nova-cotacao', methods=['GET', 'POST'])
def nova_cotacao():

    if "user" not in session:
        return redirect('/login')

    if request.method == 'POST':
        cliente = request.form.get('cliente', '')
        endereco = request.form.get('endereco', '')
        nuit = request.form.get('nuit', '')
        servico = request.form.get('servico', '')
        pagamento = request.form.get('pagamento', '')
        prazo = request.form.get('prazo', '')
        nb = request.form.get('nb', '')

        quantidades = request.form.getlist('quantidade[]')
        unidades = request.form.getlist('unidade[]')
        descricoes = request.form.getlist('descricao[]')
        precos = request.form.getlist('preco[]')

        subtotal_geral = 0
        itens_validos = []

        for i in range(len(descricoes)):

            descricao = descricoes[i].strip() if i < len(descricoes) else ""
            quantidade = quantidades[i].strip() if i < len(quantidades) else ""
            preco_txt = precos[i].strip() if i < len(precos) else ""
            unidade = unidades[i].strip() if i < len(unidades) else ""

            if not descricao or not quantidade or not preco_txt:
                continue

            qtd = float(quantidade)
            preco = float(preco_txt)
            subtotal_item = qtd * preco

            subtotal_geral += subtotal_item

            itens_validos.append({
                "quantidade": qtd,
                "unidade": unidade,
                "descricao": descricao,
                "preco": preco,
                "subtotal": subtotal_item
            })

        if not itens_validos:
            return "Erro: adicione pelo menos um item válido na cotação."

        iva = subtotal_geral * 0.16
        total = subtotal_geral + iva

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO cotacoes (
            cliente, empresa, endereco, nuit,
            pagamento, prazo, nb, subtotal, iva, total
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            cliente, servico, endereco, nuit,
            pagamento, prazo, nb,
            subtotal_geral, iva, total
        ))

        cotacao_id = cursor.fetchone()[0]

        for item in itens_validos:
            cursor.execute("""
            INSERT INTO itens_cotacao (
                cotacao_id, quantidade, unidade, descricao, preco, subtotal
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                cotacao_id,
                item["quantidade"],
                item["unidade"],
                item["descricao"],
                item["preco"],
                item["subtotal"]
            ))

        conn.commit()
        conn.close()

        return redirect('/historico')

    return render_template("nova_cotacao.html")


@app.route('/historico')
def historico():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM cotacoes
    ORDER BY id DESC
    """)

    cotacoes = cursor.fetchall()
    conn.close()

    return render_template("historico.html", cotacoes=cotacoes)


@app.route('/editar-cotacao/<int:id>', methods=['GET', 'POST'])
def editar_cotacao(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':
        cliente = request.form.get('cliente', '')
        endereco = request.form.get('endereco', '')
        nuit = request.form.get('nuit', '')
        servico = request.form.get('servico', '')
        pagamento = request.form.get('pagamento', '')
        prazo = request.form.get('prazo', '')
        nb = request.form.get('nb', '')

        quantidades = request.form.getlist('quantidade[]')
        unidades = request.form.getlist('unidade[]')
        descricoes = request.form.getlist('descricao[]')
        precos = request.form.getlist('preco[]')

        subtotal_geral = 0
        itens_validos = []

        maior_tamanho = max(
            len(quantidades),
            len(unidades),
            len(descricoes),
            len(precos)
        )

        for i in range(maior_tamanho):

            quantidade = quantidades[i].strip() if i < len(quantidades) else ""
            unidade = unidades[i].strip() if i < len(unidades) else ""
            descricao = descricoes[i].strip() if i < len(descricoes) else ""
            preco_txt = precos[i].strip() if i < len(precos) else ""

            if not quantidade and not unidade and not descricao and not preco_txt:
                continue

            if not quantidade or not descricao or not preco_txt:
                continue

            qtd = float(quantidade)
            preco = float(preco_txt)
            subtotal_item = qtd * preco

            subtotal_geral += subtotal_item

            itens_validos.append({
                "quantidade": qtd,
                "unidade": unidade,
                "descricao": descricao,
                "preco": preco,
                "subtotal": subtotal_item
            })

        if not itens_validos:
            conn.close()
            return "Erro: a cotação deve ter pelo menos um item válido."

        iva = subtotal_geral * 0.16
        total = subtotal_geral + iva

        cursor.execute("""
        UPDATE cotacoes
        SET cliente=%s,
            empresa=%s,
            endereco=%s,
            nuit=%s,
            pagamento=%s,
            prazo=%s,
            nb=%s,
            subtotal=%s,
            iva=%s,
            total=%s
        WHERE id=%s
        """, (
            cliente,
            servico,
            endereco,
            nuit,
            pagamento,
            prazo,
            nb,
            subtotal_geral,
            iva,
            total,
            id
        ))

        cursor.execute("""
        DELETE FROM itens_cotacao
        WHERE cotacao_id=%s
        """, (id,))

        for item in itens_validos:
            cursor.execute("""
            INSERT INTO itens_cotacao (
                cotacao_id,
                quantidade,
                unidade,
                descricao,
                preco,
                subtotal
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                id,
                item["quantidade"],
                item["unidade"],
                item["descricao"],
                item["preco"],
                item["subtotal"]
            ))

        conn.commit()
        conn.close()

        return redirect('/historico')

    cursor.execute("""
    SELECT *
    FROM cotacoes
    WHERE id=%s
    """, (id,))

    cotacao = cursor.fetchone()

    cursor.execute("""
    SELECT *
    FROM itens_cotacao
    WHERE cotacao_id=%s
    ORDER BY id ASC
    """, (id,))

    itens = cursor.fetchall()

    conn.close()

    if not cotacao:
        return "Cotação não encontrada"

    return render_template(
        "editar_cotacao.html",
        c=cotacao,
        itens=itens
    )


@app.route('/apagar-cotacao/<int:id>')
def apagar_cotacao(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM itens_cotacao WHERE cotacao_id=%s", (id,))
    cursor.execute("DELETE FROM cotacoes WHERE id=%s", (id,))

    conn.commit()
    conn.close()

    return redirect('/historico')


@app.route('/gerar-pdf/<int:id>')
def gerar_pdf(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cotacoes WHERE id=%s", (id,))
    c = cursor.fetchone()

    cursor.execute("SELECT * FROM itens_cotacao WHERE cotacao_id=%s", (id,))
    itens = cursor.fetchall()

    conn.close()

    if not c:
        return "Cotação não encontrada"

    def safe(v):
        return float(v) if v else 0.0

    def quebrar_texto(texto, limite):
        palavras = str(texto or "").split()
        linhas = []
        linha = ""

        for palavra in palavras:
            if len(linha + " " + palavra) <= limite:
                linha += " " + palavra
            else:
                if linha:
                    linhas.append(linha.strip())
                linha = palavra

        if linha:
            linhas.append(linha.strip())

        return linhas

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/cotacao_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    azul_claro = colors.HexColor("#e3f2fd")
    cinza = colors.HexColor("#eeeeee")
    data = datetime.now().strftime("%d/%m/%Y")

    def desenhar_logos_parceiros():
        pasta = "static/parceiros"

        if not os.path.exists(pasta):
            return

        logos = []

        for arquivo in os.listdir(pasta):
            if arquivo.lower().endswith((".png", ".jpg", ".jpeg")):
                logos.append(os.path.join(pasta, arquivo))

        if not logos:
            return

        logos = logos[:10]

        logo_w = 34
        logo_h = 20
        gap = 10

        total_w = (len(logos) * logo_w) + ((len(logos) - 1) * gap)
        x_inicio = (width - total_w) / 2
        y_logo = 28

        for logo in logos:
            pdf.drawImage(
                logo,
                x_inicio,
                y_logo,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask='auto'
            )
            x_inicio += logo_w + gap

    def desenhar_rodape():
        desenhar_logos_parceiros()
        pdf.setFont("Helvetica", 7)
        pdf.setFillColor(colors.grey)
        pdf.drawString(40, 15, f"Documento gerado automaticamente | {data}")

    def desenhar_cabecalho_tabela(y_pos):
        pdf.setFillColor(azul)
        pdf.rect(40, y_pos, 515, 24, fill=1)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 9)

        pdf.drawString(50, y_pos + 8, "Qtd")
        pdf.drawString(95, y_pos + 8, "Un")
        pdf.drawString(145, y_pos + 8, "DESCRIÇÃO")
        pdf.drawString(400, y_pos + 8, "P.Unit")
        pdf.drawString(485, y_pos + 8, "Subtotal")

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)

        return y_pos - 24

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            25,
            height - 145,
            width=125,
            height=85,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(azul)
    pdf.drawString(220, height - 55, f"COTAÇÃO N° {id:05d}/2026")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    x_info = 270
    pdf.drawString(x_info, height - 82, "Av. Armando Tivane – Goto")
    pdf.drawString(x_info, height - 97, "Cell: (+258) 878340748 / 847891715")
    pdf.drawString(x_info, height - 112, "Email: transporteverticalmz@gmail.com")
    pdf.drawString(x_info, height - 127, "NUIT: 401560671")
    pdf.drawString(x_info, height - 142, "Beira - Moçambique")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 160, 555, height - 160)

    box_cliente_y = height - 275

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, box_cliente_y - 20, 515, 115, 8, fill=0)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(azul)
    pdf.drawString(55, box_cliente_y + 75, "DADOS DA EMPRESA CLIENTE")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(55, box_cliente_y + 52, "Empresa:")
    pdf.drawString(55, box_cliente_y + 35, "Endereço:")
    pdf.drawString(55, box_cliente_y + 18, "NUIT:")
    pdf.drawString(300, box_cliente_y + 18, "Serviço:")

    pdf.setFont("Helvetica", 10)

    pdf.drawString(125, box_cliente_y + 52, str(c[1] or ""))
    pdf.drawString(125, box_cliente_y + 35, str(c[3] or ""))
    pdf.drawString(125, box_cliente_y + 18, str(c[4] or ""))

    servico_linhas = quebrar_texto(c[2], 28)
    servico_y = box_cliente_y + 18

    for linha in servico_linhas[:3]:
        pdf.drawString(355, servico_y, linha)
        servico_y -= 12

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(430, box_cliente_y + 75, "Data:")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(465, box_cliente_y + 75, data)

    y = height - 335
    y = desenhar_cabecalho_tabela(y)

    for item in itens:

        desc_linhas = quebrar_texto(item[4], 38)
        linhas_usadas = desc_linhas[:3]
        altura_item = max(24, len(linhas_usadas) * 12 + 10)

        if y - altura_item < 110:
            desenhar_rodape()
            pdf.showPage()
            y = height - 80
            y = desenhar_cabecalho_tabela(y)

        pdf.setStrokeColor(cinza)
        pdf.line(40, y - 5, 555, y - 5)

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)

        pdf.drawString(50, y, str(item[2]))
        pdf.drawString(95, y, str(item[3] or ""))

        desc_y = y

        for linha_desc in linhas_usadas:
            pdf.drawString(145, desc_y, linha_desc)
            desc_y -= 12

        pdf.drawRightString(455, y, f"{safe(item[5]):,.2f} MT")
        pdf.drawRightString(545, y, f"{safe(item[6]):,.2f} MT")

        y -= altura_item

    if y < 350:
        desenhar_rodape()
        pdf.showPage()
        y = height - 100

    subtotal = safe(c[8])
    iva = safe(c[9])
    total = safe(c[10])

    total_box_y = y - 55

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(360, total_box_y, 195, 65, 6, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)

    pdf.drawString(375, total_box_y + 45, "Subtotal:")
    pdf.drawRightString(540, total_box_y + 45, f"{subtotal:,.2f} MT")

    pdf.drawString(375, total_box_y + 27, "IVA 16%:")
    pdf.drawRightString(540, total_box_y + 27, f"{iva:,.2f} MT")

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(375, total_box_y + 8, "TOTAL:")
    pdf.drawRightString(540, total_box_y + 8, f"{total:,.2f} MT")

    termos_y = total_box_y - 85

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, termos_y - 55, 515, 70, 6, fill=0)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(azul)
    pdf.drawString(55, termos_y - 5, "TERMOS DE PAGAMENTO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    pagamento = str(c[5] or "")

    if pagamento == "100":
        pdf.drawString(65, termos_y - 25, "• 100% no ato da adjudicação")
    else:
        pdf.drawString(65, termos_y - 25, "• 60% do pagamento no ato da adjudicação")
        pdf.drawString(65, termos_y - 40, "• 40% no ato da entrega")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(azul)
    pdf.drawString(300, termos_y - 5, "PRAZO DE ENTREGA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(310, termos_y - 25, str(c[6] or ""))

    nb = str(c[7] or "").strip()

    if nb != "":
        nb_y = termos_y - 90

        pdf.setStrokeColor(cinza)
        pdf.roundRect(40, nb_y - 45, 515, 55, 6, fill=0)

        pdf.setFont("Helvetica-Bold", 10)
        pdf.setFillColor(azul)
        pdf.drawString(55, nb_y - 5, "NB:")

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)

        nb_linhas = quebrar_texto(nb, 95)
        nb_text_y = nb_y - 25

        for linha_nb in nb_linhas[:2]:
            pdf.drawString(75, nb_text_y, linha_nb)
            nb_text_y -= 12

        bank_y = nb_y - 125
    else:
        bank_y = termos_y - 135

    pdf.setStrokeColor(azul)
    pdf.roundRect(40, bank_y, 515, 65, 6, fill=0)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(azul)
    pdf.drawString(55, bank_y + 45, "Detalhes bancários:")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    pdf.drawString(55, bank_y + 28, "BANCO BCI – CONTA N°24512268710001")
    pdf.drawString(55, bank_y + 13, "NIB - 000800004512268710113")

    desenhar_rodape()

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"COTACAO_{id}.pdf"
    )


@app.route('/partilhar/<int:id>')
def partilhar(id):

    if "user" not in session:
        return redirect('/login')

    pdf_path = f"pdfs/cotacao_{id}.pdf"

    if not os.path.exists(pdf_path):
        gerar_pdf(id)

    pdf_url = request.host_url + f"gerar-pdf/{id}"

    whatsapp_url = f"https://wa.me/?text=Segue%20a%20cotação:%20{pdf_url}"
    email_url = f"mailto:?subject=Cotação&body=Segue%20a%20cotação:%20{pdf_url}"

    return render_template(
        "partilhar.html",
        whatsapp_url=whatsapp_url,
        email_url=email_url,
        pdf_url=pdf_url,
        cotacao_id=id
    )


@app.route('/acesso-rh', methods=['GET', 'POST'])
def acesso_rh():

    if "user" not in session:
        return redirect('/login')

    if request.method == 'POST':

        senha = request.form.get('senha_rh', '')

        if senha == SENHA_RH:
            session['rh_autorizado'] = True
            return redirect('/funcionarios')

        return "Senha de RH inválida"

    return render_template("acesso_rh.html")


@app.route('/sair-rh')
def sair_rh():

    if "user" not in session:
        return redirect('/login')

    session.pop("rh_autorizado", None)

    return redirect('/')


@app.route('/funcionarios', methods=['GET', 'POST'])
def funcionarios():

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '')
        cargo = request.form.get('cargo', '')
        salario_hora = request.form.get('salario_hora', '0')
        telefone = request.form.get('telefone', '')

        cursor.execute("""
        INSERT INTO funcionarios (
            nome,
            cargo,
            salario_hora,
            telefone
        )
        VALUES (%s, %s, %s, %s)
        """, (
            nome,
            cargo,
            float(salario_hora),
            telefone
        ))

        conn.commit()

        return redirect('/funcionarios')

    cursor.execute("""
    SELECT *
    FROM funcionarios
    ORDER BY id DESC
    """)

    funcionarios = cursor.fetchall()

    conn.close()

    return render_template(
        "funcionarios.html",
        funcionarios=funcionarios
    )


@app.route('/editar-funcionario/<int:id>', methods=['GET', 'POST'])
def editar_funcionario(id):

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '')
        cargo = request.form.get('cargo', '')
        salario_hora = request.form.get('salario_hora', '0')
        telefone = request.form.get('telefone', '')
        estado = request.form.get('estado', 'Ativo')

        cursor.execute("""
        UPDATE funcionarios
        SET nome=%s,
            cargo=%s,
            salario_hora=%s,
            telefone=%s,
            estado=%s
        WHERE id=%s
        """, (
            nome,
            cargo,
            float(salario_hora),
            telefone,
            estado,
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/funcionarios')

    cursor.execute("""
    SELECT *
    FROM funcionarios
    WHERE id=%s
    """, (id,))

    funcionario = cursor.fetchone()
    conn.close()

    if not funcionario:
        return "Funcionário não encontrado"

    return render_template("editar_funcionario.html", f=funcionario)


@app.route('/apagar-funcionario/<int:id>')
def apagar_funcionario(id):

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE funcionarios
    SET estado='Inativo'
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/funcionarios')


@app.route('/nova-folha', methods=['GET', 'POST'])
def nova_folha():

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        funcionario_id = request.form.get('funcionario_id')
        mes = request.form.get('mes')
        ano = request.form.get('ano')

        horas_normais = float(request.form.get('horas_normais', 0))
        horas_extra_50 = float(request.form.get('horas_extra_50', 0))
        horas_extra_100 = float(request.form.get('horas_extra_100', 0))
        outros_descontos = float(request.form.get('outros_descontos', 0))

        cursor.execute("""
        SELECT salario_hora
        FROM funcionarios
        WHERE id=%s
        """, (funcionario_id,))

        funcionario = cursor.fetchone()

        if not funcionario:
            conn.close()
            return "Funcionário não encontrado"

        salario_hora = float(funcionario[0])

        valor_horas_normais = horas_normais * salario_hora
        valor_extra_50 = horas_extra_50 * salario_hora * 1.5
        valor_extra_100 = horas_extra_100 * salario_hora * 2

        total_bruto = valor_horas_normais + valor_extra_50 + valor_extra_100
        inss = total_bruto * 0.03
        total_liquido = total_bruto - inss - outros_descontos
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
        INSERT INTO folhas_salariais (
            funcionario_id, mes, ano,
            horas_normais, horas_extra_50, horas_extra_100,
            valor_horas_normais, valor_extra_50, valor_extra_100,
            inss, outros_descontos, total_bruto, total_liquido,
            data_criacao
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            funcionario_id,
            mes,
            int(ano),
            horas_normais,
            horas_extra_50,
            horas_extra_100,
            valor_horas_normais,
            valor_extra_50,
            valor_extra_100,
            inss,
            outros_descontos,
            total_bruto,
            total_liquido,
            data_criacao
        ))

        conn.commit()
        conn.close()

        return redirect('/folhas')

    cursor.execute("""
    SELECT id, nome, cargo, salario_hora
    FROM funcionarios
    WHERE estado='Ativo'
    ORDER BY nome ASC
    """)

    funcionarios = cursor.fetchall()

    conn.close()

    return render_template(
        "nova_folha.html",
        funcionarios=funcionarios
    )


@app.route('/folhas')
def folhas():

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        folhas_salariais.id,
        funcionarios.nome,
        funcionarios.cargo,
        folhas_salariais.mes,
        folhas_salariais.ano,
        folhas_salariais.total_bruto,
        folhas_salariais.inss,
        folhas_salariais.outros_descontos,
        folhas_salariais.total_liquido,
        folhas_salariais.data_criacao
    FROM folhas_salariais
    INNER JOIN funcionarios
    ON folhas_salariais.funcionario_id = funcionarios.id
    ORDER BY folhas_salariais.id DESC
    """)

    folhas = cursor.fetchall()
    conn.close()

    return render_template("folhas.html", folhas=folhas)


@app.route('/recibo-folha/<int:id>')
def recibo_folha(id):

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        folhas_salariais.id,
        funcionarios.nome,
        funcionarios.cargo,
        funcionarios.salario_hora,
        folhas_salariais.mes,
        folhas_salariais.ano,
        folhas_salariais.horas_normais,
        folhas_salariais.horas_extra_50,
        folhas_salariais.horas_extra_100,
        folhas_salariais.valor_horas_normais,
        folhas_salariais.valor_extra_50,
        folhas_salariais.valor_extra_100,
        folhas_salariais.inss,
        folhas_salariais.outros_descontos,
        folhas_salariais.total_bruto,
        folhas_salariais.total_liquido,
        folhas_salariais.data_criacao
    FROM folhas_salariais
    INNER JOIN funcionarios
    ON folhas_salariais.funcionario_id = funcionarios.id
    WHERE folhas_salariais.id=%s
    """, (id,))

    folha = cursor.fetchone()
    conn.close()

    if not folha:
        return "Folha salarial não encontrada"

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/recibo_folha_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")
    data = datetime.now().strftime("%d/%m/%Y")

    def money(v):
        return f"{float(v or 0):,.2f} MT"

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 130,
            width=110,
            height=75,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 60, "RECIBO SALARIAL")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(200, height - 85, "Av. Armando Tivane – Goto")
    pdf.drawString(200, height - 100, "Cell: (+258) 878340748 / 847891715")
    pdf.drawString(200, height - 115, "Email: transporteverticalmz@gmail.com")
    pdf.drawString(200, height - 130, "NUIT: 401560671")
    pdf.drawString(200, height - 145, "Beira - Moçambique")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 165, 555, height - 165)

    box_y = height - 270

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, box_y, 515, 80, 8, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, box_y + 60, "DADOS DO FUNCIONÁRIO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, box_y + 38, "Nome:")
    pdf.drawString(55, box_y + 20, "Cargo:")
    pdf.drawString(320, box_y + 38, "Mês/Ano:")
    pdf.drawString(320, box_y + 20, "Salário/Hora:")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(110, box_y + 38, str(folha[1] or ""))
    pdf.drawString(110, box_y + 20, str(folha[2] or ""))
    pdf.drawString(395, box_y + 38, f"{folha[4]}/{folha[5]}")
    pdf.drawString(410, box_y + 20, money(folha[3]))

    y = height - 320

    pdf.setFillColor(azul)
    pdf.rect(40, y, 515, 24, fill=1)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y + 8, "Descrição")
    pdf.drawString(300, y + 8, "Horas")
    pdf.drawString(430, y + 8, "Valor")

    y -= 28

    linhas = [
        ("Horas normais 100%", folha[6], folha[9]),
        ("Horas extra 50%", folha[7], folha[10]),
        ("Horas extra 100%", folha[8], folha[11]),
    ]

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    for desc, horas, valor in linhas:
        pdf.drawString(55, y, desc)
        pdf.drawRightString(340, y, f"{float(horas or 0):,.2f}")
        pdf.drawRightString(520, y, money(valor))
        pdf.setStrokeColor(cinza)
        pdf.line(40, y - 6, 555, y - 6)
        y -= 24

    resumo_y = y - 25

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(330, resumo_y - 95, 225, 105, 6, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(345, resumo_y - 15, "Total Bruto:")
    pdf.drawRightString(540, resumo_y - 15, money(folha[14]))

    pdf.drawString(345, resumo_y - 35, "INSS 3%:")
    pdf.drawRightString(540, resumo_y - 35, money(folha[12]))

    pdf.drawString(345, resumo_y - 55, "Outros Descontos:")
    pdf.drawRightString(540, resumo_y - 55, money(folha[13]))

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(345, resumo_y - 80, "TOTAL LÍQUIDO:")
    pdf.drawRightString(540, resumo_y - 80, money(folha[15]))

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 105, f"Documento gerado automaticamente em {data}")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RECIBO_SALARIAL_{id}.pdf"
    )


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )