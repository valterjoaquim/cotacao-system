from flask import Flask, render_template, request, redirect, session, send_file
import psycopg2
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
from urllib.parse import quote
app = Flask(__name__)
app.secret_key = "cotacao123"

SENHA_RH = "rh123"

SENHA_MANUTENCAO = "1234"


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
# =========================
# BACKUP DO SISTEMA
# =========================
def fazer_backup():

    import subprocess

    # cria pasta backups
    os.makedirs("backups", exist_ok=True)

    # data/hora
    data = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # nome do arquivo
    nome_arquivo = f"backups/backup_{data}.sql"

    # caminho do pg_dump
    pg_dump = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

    # verifica se existe
    if not os.path.exists(pg_dump):
        raise Exception(
            f"pg_dump não encontrado: {pg_dump}"
        )

    # senha PostgreSQL
    env = os.environ.copy()
    env["PGPASSWORD"] = "1234"

    # comando backup
    comando = [
        pg_dump,
        "-h", "localhost",
        "-U", "postgres",
        "-d", "cotacao_db",
        "-f", nome_arquivo
    ]

    resultado = subprocess.run(
        comando,
        env=env,
        capture_output=True,
        text=True
    )

    # erro
    if resultado.returncode != 0:
        raise Exception(
            f"Erro ao fazer backup:\n{resultado.stderr}"
        )

    return nome_arquivo

def rh_autorizado():
    return session.get("rh_autorizado") == True

def tem_permissao(*tipos_permitidos):
    tipo = session.get("tipo")

    if tipo == "admin":
        return True

    return tipo in tipos_permitidos


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

    cursor.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'Funcionário'")
    cursor.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS bi TEXT")
    cursor.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS nuit TEXT")
    cursor.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS email TEXT")
    cursor.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS endereco TEXT")
    cursor.execute("ALTER TABLE funcionarios ALTER COLUMN salario_hora SET DEFAULT 0")

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


    # =========================
    # TABELA PRODUTOS / ESTOQUE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        categoria TEXT,
        codigo TEXT,
        quantidade REAL DEFAULT 0,
        unidade TEXT,
        preco_compra REAL DEFAULT 0
    )
    """)
    cursor.execute("""
ALTER TABLE produtos
ADD COLUMN IF NOT EXISTS estoque_minimo REAL DEFAULT 5
""")
    cursor.execute("""
    ALTER TABLE itens_cotacao
    ADD COLUMN IF NOT EXISTS produto_id INTEGER REFERENCES produtos(id) ON DELETE SET NULL
    """)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
    funcionario_id INTEGER REFERENCES funcionarios(id) ON DELETE SET NULL,
    tipo_movimento TEXT,
    tipo_saida TEXT,
    quantidade REAL DEFAULT 0,
    responsavel TEXT,
    servico_obra TEXT,
    observacao TEXT,
    data_movimento TEXT,
    data_prevista_devolucao TEXT,
    estado_devolucao TEXT DEFAULT 'Não aplicável',
    confirmado TEXT DEFAULT 'Não'
)
""")
        # =========================
    # TABELA CLIENTES
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        nuit TEXT UNIQUE,
        morada TEXT,
        celular TEXT,
        email TEXT,
        data_criacao TEXT
    )
    """)
    cursor.execute("""
    ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS endereco TEXT
    """)


    cursor.execute("""
    ALTER TABLE movimentacoes_estoque
    ADD COLUMN IF NOT EXISTS assinatura TEXT
    """)
        # =========================
# TABELAS DE FACTURAÇÃO
# =========================
    cursor.execute("""
CREATE TABLE IF NOT EXISTS facturas (
    id SERIAL PRIMARY KEY,
    numero TEXT UNIQUE,
    cliente TEXT,
    morada TEXT,
    celular TEXT,
    nuit TEXT,
    data_factura TEXT,
    data_vencimento TEXT,
    subtotal REAL DEFAULT 0,
    iva REAL DEFAULT 0,
    total REAL DEFAULT 0,
    estado TEXT DEFAULT 'Em Aberto'
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS itens_factura (
    id SERIAL PRIMARY KEY,
    factura_id INTEGER REFERENCES facturas(id) ON DELETE CASCADE,
    quantidade REAL DEFAULT 1,
    descricao TEXT,
    preco_unitario REAL DEFAULT 0,
    subtotal REAL DEFAULT 0
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS recibos (
    id SERIAL PRIMARY KEY,
    numero TEXT UNIQUE,
    factura_id INTEGER REFERENCES facturas(id) ON DELETE CASCADE,
    numero_factura TEXT,
    cliente TEXT,
    valor_pago REAL DEFAULT 0,
    data_pagamento TEXT
)
""")
    cursor.execute("""
ALTER TABLE facturas
ADD COLUMN IF NOT EXISTS recibo_gerado TEXT DEFAULT 'Não'
""")
    cursor.execute("""
ALTER TABLE recibos
ADD COLUMN IF NOT EXISTS forma_pagamento TEXT DEFAULT 'Dinheiro'
""")

    cursor.execute("SELECT * FROM usuarios")

    if not cursor.fetchall():
        cursor.execute("""
        INSERT INTO usuarios (username, password, tipo)
        VALUES (%s, %s, %s)
        """, ("admin", "1234", "admin"))
        # =========================
# TABELA DESPESAS BÁSICAS
# =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        descricao TEXT NOT NULL,
        categoria TEXT,
        valor REAL DEFAULT 0,
        data_vencimento TEXT,
        mes TEXT,
        ano INTEGER,
        estado TEXT DEFAULT 'Pendente',
        recorrente TEXT DEFAULT 'Sim',
        observacao TEXT,
        data_criacao TEXT
    )
    """)
    # =========================
# ITENS DAS DESPESAS DE VIAGEM
# =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_despesa_viagem (
        id SERIAL PRIMARY KEY,
        despesa_id INTEGER REFERENCES despesas(id) ON DELETE CASCADE,
        data_gasto TEXT,
        descricao TEXT,
        valor REAL DEFAULT 0,
        documento TEXT,
        forma_pagamento TEXT
    )
    """)
    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS responsavel_viagem TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS data_saida TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS data_regresso TEXT
    """)
    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS empresa TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS departamento TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS centro_custo TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS destino TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS roteiro TEXT
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS hospedagem REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS alimentacao REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS combustivel REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS portagens REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS passagens REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS outras_viagem REAL DEFAULT 0
    """)

    cursor.execute("""
    ALTER TABLE despesas
    ADD COLUMN IF NOT EXISTS tipo_viagem TEXT
    """)
# =========================
# EMPRESAS DE MANUTENÇÃO
# =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas_manutencao (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        localizacao TEXT,
        contacto TEXT,
        responsavel TEXT,
        tipo_equipamento TEXT,
        quantidade_equipamentos INTEGER DEFAULT 0,
        estado TEXT DEFAULT 'Ativo',
        data_criacao TEXT
    )
    """)

    # =========================
# MANUTENÇÕES
# =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manutencoes (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER REFERENCES empresas_manutencao(id) ON DELETE CASCADE,
        data_manutencao TEXT,
        tipo_manutencao TEXT,
        tecnico TEXT,
        descricao_servico TEXT,
        estado TEXT DEFAULT 'Pendente',
        proxima_manutencao TEXT,
        observacao TEXT,
        data_criacao TEXT
    )
    """)
# =========================
# AVARIAS
# =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avarias (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER REFERENCES empresas_manutencao(id) ON DELETE CASCADE,
        data_avaria TEXT,
        equipamento TEXT,
        descricao TEXT,
        prioridade TEXT,
        estado TEXT DEFAULT 'Aberta',
        tecnico TEXT,
        solucao TEXT,
        data_resolucao TEXT,
        data_criacao TEXT
    )
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS equipamentos_manutencao (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_manutencao(id) ON DELETE CASCADE,
    nome TEXT,
    marca TEXT,
    modelo TEXT,
    numero_serie TEXT,
    localizacao TEXT,
    estado TEXT DEFAULT 'Activo',
    data_criacao TEXT
)
""")
    
    
    

    conn.commit()
    conn.close()


init_db()


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

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
            session['tipo_usuario'] = user[3]

            return redirect('/')

        return render_template(
            "login.html",
            erro="Usuário ou senha inválidos."
        )

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
# ======================
# RESUMO FINANCEIRO
# =========================
    atualizar_facturas_vencidas()

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE estado='Pago'
    """)
    qtd_facturas_pagas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE estado='Em Aberto'
    """)
    qtd_facturas_abertas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE estado='Dívida'
    """)
    qtd_facturas_divida = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COALESCE(SUM(total), 0)
    FROM facturas
    WHERE estado='Dívida'
    """)
    total_divida_dashboard = cursor.fetchone()[0]

    conn.close()

    return render_template(
    "dashboard.html",
    total_cotacoes=total_cotacoes,
    total_gerado=round(total_gerado, 2),
    ultimas_cotacoes=ultimas_cotacoes,
    qtd_facturas_pagas=qtd_facturas_pagas,
    qtd_facturas_abertas=qtd_facturas_abertas,
    qtd_facturas_divida=qtd_facturas_divida,
    total_divida_dashboard=total_divida_dashboard
)




def baixar_estoque_por_produto_id(cursor, produto_id, quantidade, cotacao_id):
    """
    Baixa estoque usando o ID do produto selecionado na cotação.
    É mais seguro do que procurar pelo nome.
    """

    if not produto_id:
        return False

    cursor.execute("""
    SELECT id, nome, quantidade
    FROM produtos
    WHERE id=%s
    LIMIT 1
    """, (produto_id,))

    produto = cursor.fetchone()

    if not produto:
        return False

    quantidade_atual = float(produto[2] or 0)

    if quantidade > quantidade_atual:
        return False

    data_movimento = datetime.now().strftime("%d/%m/%Y %H:%M")

    cursor.execute("""
    UPDATE produtos
    SET quantidade = quantidade - %s
    WHERE id=%s
    """, (quantidade, produto_id))

    cursor.execute("""
    INSERT INTO movimentacoes_estoque (
        produto_id,
        tipo_movimento,
        tipo_saida,
        quantidade,
        responsavel,
        servico_obra,
        observacao,
        data_movimento,
        estado_devolucao,
        confirmado
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        produto_id,
        "Saída",
        "Consumo",
        quantidade,
        session.get("user", ""),
        f"Cotação #{cotacao_id}",
        "Baixa automática através da cotação",
        data_movimento,
        "Não aplicável",
        "Sim"
    ))

    return True


def baixar_estoque_por_cotacao(cursor, descricao, quantidade, cotacao_id):
    """
    Procura um produto no estoque com nome igual à descrição do item da cotação.
    Se encontrar e tiver quantidade suficiente, baixa automaticamente o estoque
    e regista a movimentação como saída por consumo.
    """

    cursor.execute("""
    SELECT id, nome, quantidade
    FROM produtos
    WHERE LOWER(nome) = LOWER(%s)
    LIMIT 1
    """, (descricao,))

    produto = cursor.fetchone()

    if not produto:
        return

    produto_id = produto[0]
    quantidade_atual = float(produto[2] or 0)

    if quantidade > quantidade_atual:
        return

    data_movimento = datetime.now().strftime("%d/%m/%Y %H:%M")

    cursor.execute("""
    UPDATE produtos
    SET quantidade = quantidade - %s
    WHERE id=%s
    """, (quantidade, produto_id))

    cursor.execute("""
    INSERT INTO movimentacoes_estoque (
        produto_id,
        tipo_movimento,
        tipo_saida,
        quantidade,
        responsavel,
        servico_obra,
        observacao,
        data_movimento,
        estado_devolucao,
        confirmado
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        produto_id,
        "Saída",
        "Consumo",
        quantidade,
        session.get("user", ""),
        f"Cotação #{cotacao_id}",
        "Baixa automática através da cotação",
        data_movimento,
        "Não aplicável",
        "Sim"
    ))

@app.route('/nova-cotacao', methods=['GET', 'POST'])
def nova_cotacao():

    if "user" not in session:
        return redirect('/login')
    if not tem_permissao("comercial"):
        return "Acesso negado"

    if request.method == 'POST':
        cliente = request.form.get('cliente', '').strip()
        endereco = request.form.get('endereco', '').strip()
        nuit = request.form.get('nuit', '').strip()
        servico = request.form.get('servico', '').strip()
        pagamento = request.form.get('pagamento', '').strip()
        prazo = request.form.get('prazo', '').strip()
        nb = request.form.get('nb', '').strip()

        produto_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        unidades = request.form.getlist('unidade[]')
        descricoes = request.form.getlist('descricao[]')
        precos = request.form.getlist('preco[]')

        subtotal_geral = 0
        itens_validos = []

        maior_tamanho = max(
            len(produto_ids),
            len(quantidades),
            len(unidades),
            len(descricoes),
            len(precos)
        )

        for i in range(maior_tamanho):
            produto_id_txt = produto_ids[i].strip() if i < len(produto_ids) else ""
            quantidade_txt = quantidades[i].strip() if i < len(quantidades) else ""
            unidade = unidades[i].strip() if i < len(unidades) else ""
            descricao = descricoes[i].strip() if i < len(descricoes) else ""
            preco_txt = precos[i].strip() if i < len(precos) else ""

            if not quantidade_txt and not descricao and not preco_txt:
                continue

            if not quantidade_txt or not descricao or not preco_txt:
                continue

            try:
                produto_id = int(produto_id_txt) if produto_id_txt else None
                quantidade = float(quantidade_txt.replace(',', '.'))
                preco = float(preco_txt.replace(',', '.'))
            except ValueError:
                continue

            if quantidade <= 0 or preco < 0:
                continue

            subtotal_item = quantidade * preco
            subtotal_geral += subtotal_item

            itens_validos.append({
                "produto_id": produto_id,
                "quantidade": quantidade,
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

        try:
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
                    cotacao_id,
                    produto_id,
                    quantidade,
                    unidade,
                    descricao,
                    preco,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    cotacao_id,
                    item["produto_id"],
                    item["quantidade"],
                    item["unidade"],
                    item["descricao"],
                    item["preco"],
                    item["subtotal"]
                ))

                # Baixar estoque automaticamente
                if item["produto_id"]:
                    baixar_estoque_por_produto_id(
                        cursor,
                        item["produto_id"],
                        item["quantidade"],
                        cotacao_id
                    )
                else:
                    baixar_estoque_por_cotacao(
                        cursor,
                        item["descricao"],
                        item["quantidade"],
                        cotacao_id
                    )

            conn.commit()

        except Exception as erro:
            conn.rollback()
            conn.close()
            return f"Erro ao salvar cotação: {erro}"

        conn.close()
        return redirect('/historico')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, codigo, quantidade, unidade, preco_compra
    FROM produtos
    ORDER BY nome ASC
    """)

    produtos = cursor.fetchall()
    conn.close()

    return render_template(
        "nova_cotacao.html",
        produtos=produtos
    )


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

    cursor.execute("""
    SELECT *
    FROM itens_cotacao
    WHERE cotacao_id=%s
    ORDER BY id ASC
    """, (id,))

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
            teste = (linha + " " + palavra).strip()

            if len(teste) <= limite:
                linha = teste
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
    vermelho = colors.HexColor("#d32f2f")

    data = datetime.now().strftime("%d/%m/%Y")

    def desenhar_logos_parceiros():

        pasta = "static/parceiros"

        if not os.path.exists(pasta):
            return

        ordem_logos = [
            "01_schindler",
            "02_monarch",
            "03_mitsubishi",
            "04_honda_generators",
            "05_firman",
            "06_lingtran",
            "07_gree",
            "08_hisense",
            "09_syinix"
        ]

        extensoes = [".png", ".jpg", ".jpeg"]

        logos = []

        for nome in ordem_logos:
            for ext in extensoes:
                caminho = os.path.join(pasta, nome + ext)

                if os.path.exists(caminho):
                    logos.append(caminho)
                    break

        if not logos:
            return

        logo_w = 36
        logo_h = 24
        gap = 4

        total_w = (len(logos) * logo_w) + ((len(logos) - 1) * gap)

        x = (width - total_w) / 2
        y = 28 

        for logo in logos:
            try:
                pdf.drawImage(
                    logo,
                    x,
                    y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask='auto'
                )

                x += logo_w + gap

            except Exception:
                pass

    def desenhar_rodape():
        desenhar_logos_parceiros()

        pdf.setFont("Helvetica", 6)
        pdf.setFillColor(colors.grey)
        pdf.drawString(40, 18, f"Documento gerado automaticamente | {data}")

    def desenhar_cabecalho_tabela(y_pos):
        pdf.setFillColor(azul)
        pdf.rect(40, y_pos, 515, 20, fill=1)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 8)

        pdf.drawString(48, y_pos + 7, "Qtd")
        pdf.drawString(82, y_pos + 7, "Un")
        pdf.drawString(122, y_pos + 7, "DESCRIÇÃO")
        pdf.drawString(405, y_pos + 7, "P.Unit")
        pdf.drawString(488, y_pos + 7, "Subtotal")

        pdf.setFillColor(colors.black)

        return y_pos - 18

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
        logo_path,
        25,
        height - 105,
        width=130,
        height=85,
        preserveAspectRatio=True,
        mask='auto'
    )

    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(azul)
    pdf.drawCentredString(
        width / 2,
        height - 42,
        f"COTAÇÃO N° {id:05d}/2026"
    )

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    x_info = 370
    pdf.drawString(x_info, height - 58, "Av. Armando Tivane – Goto")
    pdf.drawString(x_info, height - 71, "Cell: (+258) 878340748 / 847891715")
    pdf.drawString(x_info, height - 84, "Email: transporteverticalmz@gmail.com")
    pdf.drawString(x_info, height - 97, "NUIT: 401560671 | Beira - Moçambique")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 112, 555, height - 112)

    box_y = height - 205

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, box_y, 515, 78, 6, fill=0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(azul)
    pdf.drawString(52, box_y + 61, "DADOS DA EMPRESA CLIENTE")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 8)

    pdf.drawString(52, box_y + 44, "Empresa:")
    pdf.drawString(52, box_y + 28, "Endereço:")
    pdf.drawString(52, box_y + 12, "NUIT:")
    pdf.drawString(300, box_y + 44, "Serviço:")

    pdf.setFont("Helvetica", 8)

    pdf.drawString(105, box_y + 44, str(c[1] or "")[:34])
    pdf.drawString(110, box_y + 28, str(c[3] or "")[:34])
    pdf.drawString(105, box_y + 12, str(c[4] or "")[:25])

    servico_linhas = quebrar_texto(c[2], 40)
    servico_y = box_y + 44

    for linha in servico_linhas[:4]:
        pdf.drawString(350, servico_y, linha)
        servico_y -= 10

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(azul)
    pdf.drawRightString(545, box_y + 61, f"Data: {data}")

    y = height - 235
    y = desenhar_cabecalho_tabela(y)

    limite_inferior_tabela = 260

    for item in itens:

        desc_linhas = quebrar_texto(item[4], 55)
        linhas_usadas = desc_linhas[:2]

        altura_item = max(18, len(linhas_usadas) * 9 + 6)

        if y - altura_item < limite_inferior_tabela:
            pdf.setFont("Helvetica-Oblique", 7)
            pdf.setFillColor(vermelho)
            pdf.drawString(
                45,
                y,
                "Nota: existem mais itens nesta cotação. Reduza descrições ou itens para manter uma página."
            )
            pdf.setFillColor(colors.black)
            break

        pdf.setStrokeColor(cinza)
        pdf.line(40, y - 4, 555, y - 4)

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.black)

        pdf.drawString(48, y, str(item[2]))
        pdf.drawString(82, y, str(item[3] or "")[:8])

        desc_y = y

        for linha_desc in linhas_usadas:
            pdf.drawString(122, desc_y, linha_desc)
            desc_y -= 9

        pdf.drawRightString(462, y, f"{safe(item[5]):,.2f}")
        pdf.drawRightString(545, y, f"{safe(item[6]):,.2f}")

        y -= altura_item

    subtotal = safe(c[8])
    iva = safe(c[9])
    total = safe(c[10])

    termos_y = 185
    total_box_y = 185

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, termos_y, 300, 58, 6, fill=0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(azul)
    pdf.drawString(52, termos_y + 42, "TERMOS DE PAGAMENTO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 7)

    pagamento = str(c[5] or "")

    if pagamento == "100":
        pdf.drawString(60, termos_y + 27, "• 100% no ato da adjudicação")
    else:
        pdf.drawString(60, termos_y + 27, "• 60% no ato da adjudicação")
        pdf.drawString(60, termos_y + 15, "• 40% no ato da entrega")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(azul)
    pdf.drawString(215, termos_y + 42, "PRAZO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(215, termos_y + 27, str(c[6] or "")[:20])

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(360, total_box_y, 195, 58, 6, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(375, total_box_y + 40, "Subtotal:")
    pdf.drawRightString(540, total_box_y + 40, f"{subtotal:,.2f} MT")

    pdf.drawString(375, total_box_y + 24, "IVA 16%:")
    pdf.drawRightString(540, total_box_y + 24, f"{iva:,.2f} MT")

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(375, total_box_y + 7, "TOTAL:")
    pdf.drawRightString(540, total_box_y + 7, f"{total:,.2f} MT")

    nb = str(c[7] or "").strip()

    info_y = 115

    pdf.setStrokeColor(azul)
    pdf.roundRect(40, info_y, 515, 55, 6, fill=0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(azul)
    pdf.drawString(52, info_y + 38, "Detalhes bancários:")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(52, info_y + 24, "BANCO BCI – CONTA N°24512268710001")
    pdf.drawString(52, info_y + 12, "NIB - 000800004512268710113")

    if nb:
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(azul)
        pdf.drawString(300, info_y + 38, "NB:")

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 7)

        nb_linhas = quebrar_texto(nb, 42)
        nb_y = info_y + 24

        for linha_nb in nb_linhas[:2]:
            pdf.drawString(325, nb_y, linha_nb)
            nb_y -= 10

    desenhar_rodape()

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"COTACAO_{id}.pdf"
    )


@app.route('/produtos', methods=['GET', 'POST'])
def produtos():

    if "user" not in session:
        return redirect('/login')
    if not tem_permissao("estoque"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        quantidade = float(request.form.get('quantidade') or 0)
        unidade = request.form.get('unidade', '').strip()
        preco_compra = float(request.form.get('preco_compra') or 0)
        estoque_minimo = float(request.form.get('estoque_minimo') or 5)

        if not nome:
            conn.close()
            return "Erro: informe o nome do produto."

        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM produtos")
        proximo_id = cursor.fetchone()[0]

        codigo = f"PROD-{proximo_id:04d}"

        cursor.execute("""
        INSERT INTO produtos (
            nome,
            categoria,
            codigo,
            quantidade,
            unidade,
            preco_compra,
            estoque_minimo
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            nome,
            categoria,
            codigo,
            quantidade,
            unidade,
            preco_compra,
            estoque_minimo
        ))

        conn.commit()
        conn.close()

        return redirect('/produtos')

    cursor.execute("""
    SELECT
        id,
        nome,
        categoria,
        codigo,
        quantidade,
        unidade,
        preco_compra,
        estoque_minimo
    FROM produtos
    ORDER BY id DESC
    """)

    produtos = cursor.fetchall()

    conn.close()

    return render_template(
        "produtos.html",
        produtos=produtos
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
    if not tem_permissao("rh"):
        return "Acesso negado"

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
        tipo = request.form.get('tipo', 'Funcionário')
        cargo = request.form.get('cargo', '')
        telefone = request.form.get('telefone', '')
        bi = request.form.get('bi', '')
        nuit = request.form.get('nuit', '')
        email = request.form.get('email', '')
        endereco = request.form.get('endereco', '')

        if tipo == "Estagiário":
            salario_hora = 0
        else:
            salario_hora = float(request.form.get('salario_hora') or 0)

        cursor.execute("""
        INSERT INTO funcionarios (
            nome,
            tipo,
            cargo,
            salario_hora,
            telefone,
            bi,
            nuit,
            email,
            endereco,
            estado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nome,
            tipo,
            cargo,
            salario_hora,
            telefone,
            bi,
            nuit,
            email,
            endereco,
            'Ativo'
        ))

        conn.commit()
        conn.close()

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
        tipo = request.form.get('tipo', 'Funcionário')
        cargo = request.form.get('cargo', '')
        telefone = request.form.get('telefone', '')
        bi = request.form.get('bi', '')
        nuit = request.form.get('nuit', '')
        email = request.form.get('email', '')
        endereco = request.form.get('endereco', '')
        estado = request.form.get('estado', 'Ativo')

        if tipo == "Estagiário":
            salario_hora = 0
        else:
            salario_hora = float(request.form.get('salario_hora') or 0)

        cursor.execute("""
        UPDATE funcionarios
        SET nome=%s,
            tipo=%s,
            cargo=%s,
            salario_hora=%s,
            telefone=%s,
            bi=%s,
            nuit=%s,
            email=%s,
            endereco=%s,
            estado=%s
        WHERE id=%s
        """, (
            nome,
            tipo,
            cargo,
            salario_hora,
            telefone,
            bi,
            nuit,
            email,
            endereco,
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
        DELETE FROM funcionarios
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/funcionarios')


@app.route('/nova-folha', methods=['GET', 'POST'])
def nova_folha():

    # 🔐 Segurança: login
    if "user" not in session:
        return redirect('/login')

    # 🔐 Segurança: permissão RH
    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    # =========================
    # POST → CRIAR FOLHA
    # =========================
    if request.method == 'POST':

        funcionario_id = request.form.get('funcionario_id')
        mes = request.form.get('mes')
        ano = request.form.get('ano')

        horas_normais = float(request.form.get('horas_normais', 0))
        horas_extra_50 = float(request.form.get('horas_extra_50', 0))
        horas_extra_100 = float(request.form.get('horas_extra_100', 0))
        outros_descontos = float(request.form.get('outros_descontos', 0))

        # 🔍 Buscar funcionário com validação
        cursor.execute("""
            SELECT salario_hora, tipo, estado
            FROM funcionarios
            WHERE id = %s
        """, (funcionario_id,))

        funcionario = cursor.fetchone()

        if not funcionario:
            conn.close()
            return "Funcionário não encontrado"

        salario_hora, tipo, estado = funcionario

        # 🚫 Só funcionários ativos
        if tipo != "Funcionario" or estado != "Ativo":
            conn.close()
            return "Só funcionários ativos podem receber folha salarial"

        # 💰 Cálculos
        valor_horas_normais = horas_normais * salario_hora
        valor_extra_50 = horas_extra_50 * salario_hora * 1.5
        valor_extra_100 = horas_extra_100 * salario_hora * 2

        total_bruto = valor_horas_normais + valor_extra_50 + valor_extra_100
        inss = total_bruto * 0.03
        total_liquido = total_bruto - inss - outros_descontos

        data_criacao = datetime.now().strftime("%d/%m/%Y")

        # 🧾 Inserir folha
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
            int(ano) if ano else datetime.now().year,
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

    # =========================
    # GET → LISTAR FUNCIONÁRIOS
    # =========================
    cursor.execute("""
        SELECT id, nome, cargo, salario_hora
        FROM funcionarios
        WHERE estado = 'Ativo'
        AND tipo = 'Funcionario'
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
    vermelho = colors.HexColor("#d32f2f")
    data = datetime.now().strftime("%d/%m/%Y")

    def money(v):
        return f"{float(v or 0):,.2f} MT"

    def desenhar_via(y_topo, titulo_via):
        """
        Desenha uma via do recibo.
        A página A4 fica dividida em duas partes:
        - Via superior
        - Via inferior
        """

        logo_path = "static/logo/logo.png"

        # =========================
        # CABEÇALHO
        # =========================
        if os.path.exists(logo_path):
            pdf.drawImage(
                logo_path,
                40,
                y_topo - 70,
                width=75,
                height=48,
                preserveAspectRatio=True,
                mask='auto'
            )

        pdf.setFillColor(azul)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(130, y_topo - 25, "RECIBO SALARIAL")

        pdf.setFillColor(vermelho)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawRightString(555, y_topo - 25, titulo_via)

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 7)

        pdf.drawString(130, y_topo - 42, "Av. Armando Tivane – Goto")
        pdf.drawString(130, y_topo - 54, "Cell: (+258) 878340748 / 847891715")
        pdf.drawString(130, y_topo - 66, "Email: transporteverticalmz@gmail.com")
        pdf.drawString(130, y_topo - 78, "NUIT: 401560671 | Beira - Moçambique")

        pdf.setStrokeColor(azul)
        pdf.line(40, y_topo - 88, 555, y_topo - 88)

        # =========================
        # DADOS DO FUNCIONÁRIO
        # =========================
        box_y = y_topo - 162

        pdf.setStrokeColor(cinza)
        pdf.roundRect(40, box_y, 515, 60, 6, fill=0)

        pdf.setFillColor(azul)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(55, box_y + 44, "DADOS DO FUNCIONÁRIO")

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 8)

        pdf.drawString(55, box_y + 28, "Nome:")
        pdf.drawString(55, box_y + 13, "Cargo:")
        pdf.drawString(300, box_y + 28, "Mês/Ano:")
        pdf.drawString(300, box_y + 13, "Salário/Hora:")

        pdf.setFont("Helvetica", 8)

        pdf.drawString(100, box_y + 28, str(folha[1] or ""))
        pdf.drawString(100, box_y + 13, str(folha[2] or ""))
        pdf.drawString(365, box_y + 28, f"{folha[4]}/{folha[5]}")
        pdf.drawString(385, box_y + 13, money(folha[3]))

        # =========================
        # TABELA
        # =========================
        y = box_y - 28

        pdf.setFillColor(azul)
        pdf.rect(40, y, 515, 18, fill=1)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 8)

        pdf.drawString(55, y + 6, "Descrição")
        pdf.drawString(300, y + 6, "Horas")
        pdf.drawString(430, y + 6, "Valor")

        y -= 18

        linhas = [
            ("Horas normais 100%", folha[6], folha[9]),
            ("Horas extra 50%", folha[7], folha[10]),
            ("Horas extra 100%", folha[8], folha[11]),
        ]

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 8)

        for desc, horas, valor in linhas:
            pdf.drawString(55, y, desc)
            pdf.drawRightString(340, y, f"{float(horas or 0):,.2f}")
            pdf.drawRightString(520, y, money(valor))

            pdf.setStrokeColor(cinza)
            pdf.line(40, y - 5, 555, y - 5)

            y -= 17

        # =========================
        # RESUMO
        # =========================
        resumo_y = y - 8

        pdf.setFillColor(azul_claro)
        pdf.setStrokeColor(azul)
        pdf.roundRect(330, resumo_y - 72, 225, 82, 6, fill=1)

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 8)

        pdf.drawString(345, resumo_y - 8, "Total Bruto:")
        pdf.drawRightString(540, resumo_y - 8, money(folha[14]))

        pdf.drawString(345, resumo_y - 25, "INSS 3%:")
        pdf.drawRightString(540, resumo_y - 25, money(folha[12]))

        pdf.drawString(345, resumo_y - 42, "Outros Descontos:")
        pdf.drawRightString(540, resumo_y - 42, money(folha[13]))

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(345, resumo_y - 62, "TOTAL LÍQUIDO:")
        pdf.drawRightString(540, resumo_y - 62, money(folha[15]))

        # =========================
        # ASSINATURAS
        # =========================
        assinatura_y = resumo_y - 82

        pdf.setStrokeColor(colors.black)
        pdf.line(55, assinatura_y, 225, assinatura_y)
        pdf.line(330, assinatura_y, 520, assinatura_y)

        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(140, assinatura_y - 12, "Assinatura do Funcionário")
        pdf.drawCentredString(425, assinatura_y - 12, "Assinatura da Empresa")

        # =========================
        # RODAPÉ DA VIA
        # =========================
        pdf.setFont("Helvetica", 6)
        pdf.setFillColor(colors.grey)
        pdf.drawString(
            40,
            assinatura_y - 28,
            f"Documento gerado automaticamente em {data}"
        )

    # =========================
    # DESENHAR DUAS VIAS NA MESMA PÁGINA
    # =========================
    desenhar_via(height - 35, "Orginal")

    # Linha tracejada para corte/separação
    pdf.setStrokeColor(colors.grey)
    pdf.setDash(4, 4)
    pdf.line(35, height / 2, width - 35, height / 2)
    pdf.setDash()

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, (height / 2) + 5, "-------------------------------------------------------------------")

    desenhar_via((height / 2) - 20, "Copia")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RECIBO_SALARIAL_{id}.pdf"
    )
@app.route('/editar-produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # =========================
    # SALVAR ALTERAÇÕES
    # =========================
    if request.method == 'POST':

        nome = request.form.get('nome', '')
        categoria = request.form.get('categoria', '')
        codigo = request.form.get('codigo', '')
        quantidade = float(request.form.get('quantidade') or 0)
        unidade = request.form.get('unidade', '')
        preco_compra = float(request.form.get('preco_compra') or 0)

        cursor.execute("""
        UPDATE produtos
        SET nome=%s,
            categoria=%s,
            codigo=%s,
            quantidade=%s,
            unidade=%s,
            preco_compra=%s
        WHERE id=%s
        """, (
            nome,
            categoria,
            codigo,
            quantidade,
            unidade,
            preco_compra,
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/produtos')

    # =========================
    # BUSCAR PRODUTO
    # =========================
    cursor.execute("""
    SELECT *
    FROM produtos
    WHERE id=%s
    """, (id,))

    produto = cursor.fetchone()

    conn.close()

    if not produto:
        return "Produto não encontrado"

    return render_template(
        "editar_produto.html",
        p=produto
    )
@app.route('/apagar-produto/<int:id>')
def apagar_produto(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM produtos
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/produtos')
@app.route('/entrada-estoque/<int:id>', methods=['GET', 'POST'])
def entrada_estoque(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM produtos
    WHERE id=%s
    """, (id,))

    produto = cursor.fetchone()

    if not produto:
        conn.close()
        return "Produto não encontrado"

    if request.method == 'POST':

        quantidade = float(request.form.get('quantidade') or 0)
        responsavel = request.form.get('responsavel', '')
        observacao = request.form.get('observacao', '')
        data_movimento = datetime.now().strftime("%d/%m/%Y %H:%M")

        if quantidade <= 0:
            conn.close()
            return "Erro: informe uma quantidade válida."

        cursor.execute("""
        UPDATE produtos
        SET quantidade = quantidade + %s
        WHERE id=%s
        """, (quantidade, id))

        cursor.execute("""
        INSERT INTO movimentacoes_estoque (
            produto_id,
            tipo_movimento,
            tipo_saida,
            quantidade,
            responsavel,
            servico_obra,
            observacao,
            data_movimento,
            data_prevista_devolucao,
            estado_devolucao,
            confirmado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id,
            "Entrada",
            "Não aplicável",
            quantidade,
            responsavel,
            "",
            observacao,
            data_movimento,
            "",
            "Não aplicável",
            "Sim"
        ))

        conn.commit()
        conn.close()

        return redirect('/produtos')

    conn.close()

    return render_template(
        "entrada_estoque.html",
        produto=produto
    )
@app.route('/saida-estoque/<int:id>', methods=['GET', 'POST'])
def saida_estoque(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM produtos
    WHERE id=%s
    """, (id,))

    produto = cursor.fetchone()

    if not produto:
        conn.close()
        return "Produto não encontrado"

    cursor.execute("""
    SELECT id, nome, cargo
    FROM funcionarios
    WHERE estado='Ativo'
    ORDER BY nome ASC
    """)

    funcionarios = cursor.fetchall()

    if request.method == 'POST':

        funcionario_id = request.form.get('funcionario_id')
        tipo_saida = request.form.get('tipo_saida', '')
        quantidade = float(request.form.get('quantidade') or 0)
        responsavel = request.form.get('responsavel', '')
        servico_obra = request.form.get('servico_obra', '')
        observacao = request.form.get('observacao', '')
        confirmado = request.form.get('confirmado', 'Não')
        data_prevista_devolucao = request.form.get('data_prevista_devolucao', '')

        # =========================
        # ASSINATURA DIGITAL
        # =========================
        assinatura = request.form.get('assinatura', '')

        data_movimento = datetime.now().strftime("%d/%m/%Y %H:%M")

        quantidade_atual = float(produto[4] or 0)

        if quantidade <= 0:
            conn.close()
            return "Erro: informe uma quantidade válida."

        if quantidade > quantidade_atual:
            conn.close()
            return "Erro: quantidade insuficiente em estoque."

        if not funcionario_id:
            conn.close()
            return "Erro: selecione quem levou o material."

        estado_devolucao = "Não aplicável"

        if tipo_saida == "Empréstimo":
            estado_devolucao = "Pendente"

        cursor.execute("""
        UPDATE produtos
        SET quantidade = quantidade - %s
        WHERE id=%s
        """, (quantidade, id))

        cursor.execute("""
        INSERT INTO movimentacoes_estoque (
            produto_id,
            funcionario_id,
            tipo_movimento,
            tipo_saida,
            quantidade,
            responsavel,
            servico_obra,
            observacao,
            data_movimento,
            data_prevista_devolucao,
            estado_devolucao,
            confirmado,
            assinatura
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        """, (
            id,
            funcionario_id,
            "Saída",
            tipo_saida,
            quantidade,
            responsavel,
            servico_obra,
            observacao,
            data_movimento,
            data_prevista_devolucao,
            estado_devolucao,
            confirmado,
            assinatura
        ))

        conn.commit()
        conn.close()

        return redirect('/produtos')

    conn.close()

    return render_template(
        "saida_estoque.html",
        produto=produto,
        funcionarios=funcionarios
    )
@app.route('/historico-estoque')
def historico_estoque():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        movimentacoes_estoque.id,
        produtos.nome,
        produtos.codigo,
        funcionarios.nome,
        movimentacoes_estoque.tipo_movimento,
        movimentacoes_estoque.tipo_saida,
        movimentacoes_estoque.quantidade,
        produtos.unidade,
        movimentacoes_estoque.responsavel,
        movimentacoes_estoque.servico_obra,
        movimentacoes_estoque.data_movimento,
        movimentacoes_estoque.data_prevista_devolucao,
        movimentacoes_estoque.estado_devolucao,
        movimentacoes_estoque.confirmado,
        movimentacoes_estoque.observacao,
        movimentacoes_estoque.assinatura
    FROM movimentacoes_estoque
    INNER JOIN produtos
    ON movimentacoes_estoque.produto_id = produtos.id
    LEFT JOIN funcionarios
    ON movimentacoes_estoque.funcionario_id = funcionarios.id
    ORDER BY movimentacoes_estoque.id DESC
    """)

    movimentacoes = cursor.fetchall()

    conn.close()

    return render_template(
        "historico_estoque.html",
        movimentacoes=movimentacoes
    )
@app.route('/ferramentas-pendentes')
def ferramentas_pendentes():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        movimentacoes_estoque.id,
        produtos.nome,
        produtos.codigo,
        funcionarios.nome,
        funcionarios.cargo,
        movimentacoes_estoque.quantidade,
        produtos.unidade,
        movimentacoes_estoque.data_movimento,
        movimentacoes_estoque.data_prevista_devolucao,
        movimentacoes_estoque.responsavel,
        movimentacoes_estoque.servico_obra,
        movimentacoes_estoque.observacao
    FROM movimentacoes_estoque
    INNER JOIN produtos
    ON movimentacoes_estoque.produto_id = produtos.id
    LEFT JOIN funcionarios
    ON movimentacoes_estoque.funcionario_id = funcionarios.id
    WHERE movimentacoes_estoque.tipo_movimento='Saída'
    AND movimentacoes_estoque.tipo_saida='Empréstimo'
    AND movimentacoes_estoque.estado_devolucao='Pendente'
    ORDER BY movimentacoes_estoque.id DESC
    """)

    pendentes = cursor.fetchall()

    conn.close()

    return render_template(
        "ferramentas_pendentes.html",
        pendentes=pendentes
    )
@app.route('/devolver-ferramenta/<int:id>')
def devolver_ferramenta(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT produto_id, quantidade
    FROM movimentacoes_estoque
    WHERE id=%s
    AND tipo_movimento='Saída'
    AND tipo_saida='Empréstimo'
    AND estado_devolucao='Pendente'
    """, (id,))

    mov = cursor.fetchone()

    if not mov:
        conn.close()
        return "Movimentação não encontrada ou já devolvida."

    produto_id = mov[0]
    quantidade = float(mov[1] or 0)

    data_movimento = datetime.now().strftime("%d/%m/%Y %H:%M")

    cursor.execute("""
    UPDATE produtos
    SET quantidade = quantidade + %s
    WHERE id=%s
    """, (quantidade, produto_id))

    cursor.execute("""
    UPDATE movimentacoes_estoque
    SET estado_devolucao='Devolvido'
    WHERE id=%s
    """, (id,))

    cursor.execute("""
    INSERT INTO movimentacoes_estoque (
        produto_id,
        tipo_movimento,
        tipo_saida,
        quantidade,
        responsavel,
        servico_obra,
        observacao,
        data_movimento,
        data_prevista_devolucao,
        estado_devolucao,
        confirmado
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        produto_id,
        "Devolução",
        "Empréstimo",
        quantidade,
        session.get("user", ""),
        "",
        "Ferramenta devolvida ao estoque",
        data_movimento,
        "",
        "Devolvido",
        "Sim"
    ))

    conn.commit()
    conn.close()

    return redirect('/ferramentas-pendentes')
# =========================
# BACKUP MANUAL
# =========================
@app.route('/backup')
def backup():

    if "user" not in session:
        return redirect('/login')

    arquivo = fazer_backup()

    return send_file(
        arquivo,
        as_attachment=True
    )
@app.route('/backups')
def listar_backups():

    if "user" not in session:
        return redirect('/login')

    os.makedirs("backups", exist_ok=True)

    arquivos = []

    for nome in os.listdir("backups"):
        if nome.endswith(".sql"):
            caminho = os.path.join("backups", nome)

            arquivos.append({
                "nome": nome,
                "data": datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%d/%m/%Y %H:%M"),
                "tamanho": round(os.path.getsize(caminho) / 1024, 2)
            })

    arquivos = sorted(arquivos, key=lambda x: x["nome"], reverse=True)

    return render_template("backups.html", arquivos=arquivos)


@app.route('/baixar-backup/<nome>')
def baixar_backup(nome):

    if "user" not in session:
        return redirect('/login')

    caminho = os.path.join("backups", nome)

    if not os.path.exists(caminho):
        return "Backup não encontrado"

    return send_file(caminho, as_attachment=True)
@app.route('/restaurar-backup/<nome>')
def restaurar_backup(nome):

    if "user" not in session:
        return redirect('/login')

    caminho = os.path.join("backups", nome)

    if not os.path.exists(caminho):
        return "Backup não encontrado"

    import subprocess

    psql = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"

    if not os.path.exists(psql):
        return "psql.exe não encontrado"

    env = os.environ.copy()
    env["PGPASSWORD"] = "1234"

    comando = [
        psql,
        "-h", "localhost",
        "-U", "postgres",
        "-d", "cotacao_system",
        "-f", caminho
    ]

    resultado = subprocess.run(
        comando,
        env=env,
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        return f"""
        <h2>Erro ao restaurar backup</h2>
        <pre>{resultado.stderr}</pre>
        """

    return """
    <h2>✅ Backup restaurado com sucesso</h2>
    <a href='/backups'>Voltar</a>
    """
# =========================
# ATUALIZAR FACTURAS VENCIDAS
# =========================
def atualizar_facturas_vencidas():

    conn = conectar()
    cursor = conn.cursor()

    hoje = datetime.now()

    cursor.execute("""
    SELECT id, data_vencimento, estado
    FROM facturas
    WHERE estado='Em Aberto'
    """)

    facturas = cursor.fetchall()

    for f in facturas:
        factura_id = f[0]
        data_vencimento = f[1]

        try:
            vencimento = datetime.strptime(data_vencimento, "%d/%m/%Y")
        except:
            continue

        if hoje > vencimento:
            cursor.execute("""
            UPDATE facturas
            SET estado='Dívida'
            WHERE id=%s
            """, (factura_id,))

    conn.commit()
    conn.close()


# =========================
# NOVA FACTURA
# =========================
@app.route('/nova-factura', methods=['GET', 'POST'])
def nova_factura():

    if "user" not in session:
        return redirect('/login')

    if not tem_permissao("financeiro"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        cliente_id = request.form.get('cliente_id', '')

        cursor.execute("""
        SELECT nome, endereco, nuit
        FROM clientes
        WHERE id=%s
        """, (cliente_id,))

        cliente_dados = cursor.fetchone()

        if not cliente_dados:
            conn.close()
            return "Erro: selecione um cliente válido."

        cliente = cliente_dados[0]
        morada = cliente_dados[1]
        nuit = cliente_dados[2]
        celular = ""

        quantidades = request.form.getlist('quantidade[]')
        descricoes = request.form.getlist('descricao[]')
        precos = request.form.getlist('preco_unitario[]')

        itens = []
        subtotal_geral = 0

        for i in range(len(descricoes)):

            descricao = descricoes[i].strip()
            qtd = float(quantidades[i] or 0)
            preco = float(precos[i] or 0)

            if not descricao or qtd <= 0:
                continue

            subtotal = qtd * preco
            subtotal_geral += subtotal

            itens.append({
                "quantidade": qtd,
                "descricao": descricao,
                "preco": preco,
                "subtotal": subtotal
            })

        if not itens:
            conn.close()
            return "Erro: adicione pelo menos um item válido."

        iva = subtotal_geral * 0.16
        total = subtotal_geral + iva

        data_factura = datetime.now()

        from datetime import timedelta
        vencimento = data_factura + timedelta(days=30)

        data_factura_txt = data_factura.strftime("%d/%m/%Y")
        data_vencimento_txt = vencimento.strftime("%d/%m/%Y")

        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM facturas")
        proximo_id = cursor.fetchone()[0]

        numero = f"FT-{proximo_id:05d}"

        cursor.execute("""
        INSERT INTO facturas (
            numero,
            cliente,
            morada,
            celular,
            nuit,
            data_factura,
            data_vencimento,
            subtotal,
            iva,
            total,
            estado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            numero,
            cliente,
            morada,
            celular,
            nuit,
            data_factura_txt,
            data_vencimento_txt,
            subtotal_geral,
            iva,
            total,
            "Em Aberto"
        ))

        factura_id = cursor.fetchone()[0]

        for item in itens:
            cursor.execute("""
            INSERT INTO itens_factura (
                factura_id,
                quantidade,
                descricao,
                preco_unitario,
                subtotal
            )
            VALUES (%s, %s, %s, %s, %s)
            """, (
                factura_id,
                item["quantidade"],
                item["descricao"],
                item["preco"],
                item["subtotal"]
            ))

        conn.commit()
        conn.close()

        return redirect('/facturas')

    cursor.execute("""
    SELECT id, nome, endereco, nuit
    FROM clientes
    ORDER BY nome
    """)

    clientes = cursor.fetchall()

    conn.close()

    return render_template(
        "nova_factura.html",
        clientes=clientes
    )

# =========================
# LISTAR FACTURAS
# =========================
@app.route('/facturas')
def facturas():

    if "user" not in session:
        return redirect('/login')

    atualizar_facturas_vencidas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM facturas
    ORDER BY id DESC
    """)

    facturas = cursor.fetchall()

    conn.close()

    return render_template(
        "facturas.html",
        facturas=facturas
    )
    # =========================
# PDF DA FACTURA
# =========================
@app.route('/pdf-factura/<int:id>')
def pdf_factura(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM facturas WHERE id=%s", (id,))
    factura = cursor.fetchone()

    cursor.execute("""
    SELECT quantidade, descricao, preco_unitario, subtotal
    FROM itens_factura
    WHERE factura_id=%s
    ORDER BY id ASC
    """, (id,))

    itens = cursor.fetchall()
    conn.close()

    if not factura:
        return "Factura não encontrada"

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/factura_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    vermelho = colors.HexColor("#d32f2f")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")

    def money(v):
        return f"{float(v or 0):,.2f} MT"

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 105,
            width=90,
            height=60,
            preserveAspectRatio=True,
            mask='auto'
        )

    # Cabeçalho empresa
    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(160, height - 50, "FACTURA")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(160, height - 75, "TRANSPORTES VERTICAL, LDA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(160, height - 92, "Av. Armando Tivane – Goto")
    pdf.drawString(160, height - 107, "Cell: (+258) 878340748 / 847891715")
    pdf.drawString(160, height - 122, "Email: transporteverticalmz@gmail.com")
    pdf.drawString(160, height - 137, "NUIT: 401560671 | Beira - Moçambique")

    # Número factura
    pdf.setFillColor(vermelho)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawRightString(555, height - 55, f"Nº {factura[1]}")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(555, height - 78, f"Data: {factura[6]}")
    pdf.drawRightString(555, height - 95, f"Vencimento: {factura[7]}")
    pdf.drawRightString(555, height - 112, f"Estado: {factura[11]}")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 155, 555, height - 155)

    # Dados cliente
    y_cliente = height - 245

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y_cliente, 515, 75, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, y_cliente + 55, "DADOS DO CLIENTE")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y_cliente + 35, "Cliente:")
    pdf.drawString(55, y_cliente + 18, "Morada:")
    pdf.drawString(320, y_cliente + 35, "Celular:")
    pdf.drawString(320, y_cliente + 18, "NUIT:")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(110, y_cliente + 35, str(factura[2] or ""))
    pdf.drawString(110, y_cliente + 18, str(factura[3] or ""))
    pdf.drawString(375, y_cliente + 35, str(factura[4] or ""))
    pdf.drawString(375, y_cliente + 18, str(factura[5] or ""))

    # Tabela
    y = height - 300

    pdf.setFillColor(azul)
    pdf.rect(40, y, 515, 24, fill=1)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y + 8, "Qtd")
    pdf.drawString(105, y + 8, "Descrição")
    pdf.drawString(390, y + 8, "Preço Unit.")
    pdf.drawString(485, y + 8, "Subtotal")

    y -= 26

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    for item in itens:
        quantidade = item[0]
        descricao = item[1]
        preco = item[2]
        subtotal = item[3]

        if y < 140:
            pdf.showPage()
            y = height - 80

        pdf.drawString(55, y, str(quantidade))
        pdf.drawString(105, y, str(descricao)[:45])
        pdf.drawRightString(455, y, money(preco))
        pdf.drawRightString(545, y, money(subtotal))

        pdf.setStrokeColor(cinza)
        pdf.line(40, y - 7, 555, y - 7)

        y -= 22

    # Totais
    total_y = y - 85

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(355, total_y, 200, 75, 6, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)

    pdf.drawString(370, total_y + 52, "Subtotal:")
    pdf.drawRightString(540, total_y + 52, money(factura[8]))

    pdf.drawString(370, total_y + 32, "IVA 16%:")
    pdf.drawRightString(540, total_y + 32, money(factura[9]))

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(370, total_y + 10, "TOTAL:")
    pdf.drawRightString(540, total_y + 10, money(factura[10]))

    # Nota prazo
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 85, "Condição: pagamento no prazo de 30 dias após emissão da factura.")
    pdf.drawString(40, 70, "Após o vencimento, a factura passa para o estado de Dívida.")

    # Rodapé
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 35, "Documento gerado automaticamente pelo sistema.")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"FACTURA_{factura[1]}.pdf"
    )
# =========================
# MARCAR FACTURA COMO PAGA
# =========================
@app.route('/marcar-pago/<int:id>', methods=['POST'])
def marcar_pago(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM facturas
    WHERE id=%s
    """, (id,))

    factura = cursor.fetchone()

    if not factura:
        conn.close()
        return "Factura não encontrada"

    # Atualiza estado
    cursor.execute("""
    UPDATE facturas
    SET estado='Pago',
        recibo_gerado='Sim'
    WHERE id=%s
    """, (id,))

    # gerar número recibo
    cursor.execute("""
    SELECT COALESCE(MAX(id), 0) + 1
    FROM recibos
    """)

    prox = cursor.fetchone()[0]

    numero_recibo = f"RC-{prox:05d}"

    data_pagamento = datetime.now().strftime("%d/%m/%Y")

    # criar recibo
    forma_pagamento = request.form.get(
    "forma_pagamento",
    "Dinheiro"
      )
    cursor.execute("""
    INSERT INTO recibos (
        numero,
        factura_id,
        numero_factura,
        cliente,
        valor_pago,
        data_pagamento,
        forma_pagamento
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        numero_recibo,
        id,
        factura[1],
        factura[2],
        factura[10],
        data_pagamento,
        forma_pagamento
    ))

    conn.commit()
    conn.close()

    return redirect('/facturas')

# =========================
# LISTAR RECIBOS
# =========================
@app.route('/recibos')
def recibos():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM recibos
    ORDER BY id DESC
    """)

    recibos = cursor.fetchall()

    conn.close()

    return render_template(
        "recibos.html",
        recibos=recibos
    )

# =========================
# PDF DO RECIBO
# =========================
@app.route('/pdf-recibo/<int:id>')
def pdf_recibo(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM recibos
    WHERE id=%s
    """, (id,))

    recibo = cursor.fetchone()
    conn.close()

    if not recibo:
        return "Recibo não encontrado"

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/recibo_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    vermelho = colors.HexColor("#d32f2f")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")

    def money(v):
        return f"{float(v or 0):,.2f} MT"

    def numero_por_extenso(valor):
        unidades = [
            "", "um", "dois", "três", "quatro", "cinco",
            "seis", "sete", "oito", "nove", "dez", "onze",
            "doze", "treze", "catorze", "quinze", "dezasseis",
            "dezassete", "dezoito", "dezanove"
        ]

        dezenas = [
            "", "", "vinte", "trinta", "quarenta",
            "cinquenta", "sessenta", "setenta", "oitenta", "noventa"
        ]

        centenas = [
            "", "cento", "duzentos", "trezentos", "quatrocentos",
            "quinhentos", "seiscentos", "setecentos",
            "oitocentos", "novecentos"
        ]

        def extenso_ate_999(n):
            n = int(n)

            if n == 0:
                return ""

            if n == 100:
                return "cem"

            if n < 20:
                return unidades[n]

            if n < 100:
                dez = n // 10
                uni = n % 10

                if uni == 0:
                    return dezenas[dez]

                return dezenas[dez] + " e " + unidades[uni]

            cen = n // 100
            resto = n % 100

            if resto == 0:
                return centenas[cen]

            return centenas[cen] + " e " + extenso_ate_999(resto)

        valor_int = int(float(valor or 0))

        if valor_int == 0:
            return "zero meticais"

        partes = []

        milhoes = valor_int // 1000000
        resto = valor_int % 1000000

        milhares = resto // 1000
        centenas_resto = resto % 1000

        if milhoes > 0:
            if milhoes == 1:
                partes.append("um milhão")
            else:
                partes.append(extenso_ate_999(milhoes) + " milhões")

        if milhares > 0:
            if milhares == 1:
                partes.append("mil")
            else:
                partes.append(extenso_ate_999(milhares) + " mil")

        if centenas_resto > 0:
            partes.append(extenso_ate_999(centenas_resto))

        texto = " e ".join(partes)

        if valor_int == 1:
            return texto + " metical"

        return texto + " meticais"

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

    forma_pagamento = "Dinheiro"

    try:
        forma_pagamento = recibo[7] or "Dinheiro"
    except:
        forma_pagamento = "Dinheiro"

    valor_extenso = numero_por_extenso(recibo[5])

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 105,
            width=90,
            height=60,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(160, height - 55, "RECIBO")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(160, height - 78, "TRANSPORTES VERTICAL, LDA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(160, height - 95, "Av. Armando Tivane – Goto")
    pdf.drawString(160, height - 110, "Cell: (+258) 878340748 / 847891715")
    pdf.drawString(160, height - 125, "Email: transporteverticalmz@gmail.com")
    pdf.drawString(160, height - 140, "NUIT: 401560671 | Beira - Moçambique")

    pdf.setFillColor(vermelho)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawRightString(555, height - 60, f"Nº {recibo[1]}")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(555, height - 85, f"Data: {recibo[6]}")
    pdf.drawRightString(555, height - 105, f"Factura Nº: {recibo[3]}")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 160, 555, height - 160)

    y = height - 245

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y, 515, 95, 8, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, y + 70, "DADOS DO PAGAMENTO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, y + 48, "Recebemos do(s) Sr(s):")
    pdf.drawString(55, y + 28, "Forma de pagamento:")
    pdf.drawString(300, y + 28, "Valor Pago:")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(205, y + 48, str(recibo[4] or ""))
    pdf.drawString(180, y + 28, forma_pagamento)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(385, y + 28, money(recibo[5]))

    resumo_y = y - 125

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(40, resumo_y, 515, 105, 8, fill=1)

    texto_recibo = (
        f"Recebemos do(s) Sr(s) {recibo[4]}, a importância de "
        f"{money(recibo[5])} ({valor_extenso}), proveniente da Factura nº {recibo[3]}."
    )

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)

    linhas = quebrar_texto(texto_recibo, 95)
    texto_y = resumo_y + 72

    for linha in linhas[:4]:
        pdf.drawString(60, texto_y, linha)
        texto_y -= 16

    pdf.drawString(
        60,
        resumo_y + 18,
        f"Forma de pagamento: {forma_pagamento}."
    )

    assinatura_y = resumo_y - 90

    pdf.setStrokeColor(colors.black)
    pdf.line(330, assinatura_y, 520, assinatura_y)

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(425, assinatura_y - 15, "Assinatura / Carimbo da Empresa")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 35, "Documento gerado automaticamente pelo sistema.")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RECIBO_{recibo[1]}.pdf"
    )
    # =========================
# EXTRATO FINANCEIRO
# =========================
@app.route('/extrato')
def extrato():

    if "user" not in session:
        return redirect('/login')

    atualizar_facturas_vencidas()

    conn = conectar()
    cursor = conn.cursor()

    # totais
    cursor.execute("""
    SELECT COALESCE(SUM(total), 0)
    FROM facturas
    WHERE estado='Pago'
    """)
    total_pago = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COALESCE(SUM(total), 0)
    FROM facturas
    WHERE estado='Em Aberto'
    """)
    total_aberto = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COALESCE(SUM(total), 0)
    FROM facturas
    WHERE estado='Dívida'
    """)
    total_divida = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    """)
    total_facturas = cursor.fetchone()[0]

    # lista
    cursor.execute("""
    SELECT numero,
           cliente,
           data_factura,
           data_vencimento,
           total,
           estado
    FROM facturas
    ORDER BY id DESC
    """)

    facturas = cursor.fetchall()

    conn.close()

    return render_template(
        "extrato.html",
        total_pago=total_pago,
        total_aberto=total_aberto,
        total_divida=total_divida,
        total_facturas=total_facturas,
        facturas=facturas
    )

# =========================
# GERAR FACTURA A PARTIR DA COTAÇÃO
# =========================
@app.route('/gerar-factura-cotacao/<int:id>')
def gerar_factura_cotacao(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # buscar cotação
    cursor.execute("""
    SELECT *
    FROM cotacoes
    WHERE id=%s
    """, (id,))

    cotacao = cursor.fetchone()

    if not cotacao:
        conn.close()
        return "Cotação não encontrada"

    # buscar itens da cotação
    cursor.execute("""
    SELECT quantidade, descricao, preco, subtotal
    FROM itens_cotacao
    WHERE cotacao_id=%s
    ORDER BY id ASC
    """, (id,))

    itens = cursor.fetchall()

    if not itens:
        conn.close()
        return "Esta cotação não tem itens."

    from datetime import timedelta

    data_factura = datetime.now()
    vencimento = data_factura + timedelta(days=30)

    data_factura_txt = data_factura.strftime("%d/%m/%Y")
    data_vencimento_txt = vencimento.strftime("%d/%m/%Y")

    # próximo número da factura
    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM facturas")
    proximo_id = cursor.fetchone()[0]

    numero = f"FT-{proximo_id:05d}"

    # dados vindos da cotação
    cliente = cotacao[1]
    morada = cotacao[3]
    celular = ""
    nuit = cotacao[4]
    subtotal = float(cotacao[8] or 0)
    iva = float(cotacao[9] or 0)
    total = float(cotacao[10] or 0)

    try:
        cursor.execute("""
        INSERT INTO facturas (
            numero,
            cliente,
            morada,
            celular,
            nuit,
            data_factura,
            data_vencimento,
            subtotal,
            iva,
            total,
            estado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            numero,
            cliente,
            morada,
            celular,
            nuit,
            data_factura_txt,
            data_vencimento_txt,
            subtotal,
            iva,
            total,
            "Em Aberto"
        ))

        factura_id = cursor.fetchone()[0]

        for item in itens:
            quantidade = item[0]
            descricao = item[1]
            preco = item[2]
            subtotal_item = item[3]

            cursor.execute("""
            INSERT INTO itens_factura (
                factura_id,
                quantidade,
                descricao,
                preco_unitario,
                subtotal
            )
            VALUES (%s, %s, %s, %s, %s)
            """, (
                factura_id,
                quantidade,
                descricao,
                preco,
                subtotal_item
            ))

        conn.commit()

    except Exception as erro:
        conn.rollback()
        conn.close()
        return f"Erro ao gerar factura da cotação: {erro}"

    conn.close()

    return redirect('/facturas')

@app.route('/financeiro')
def financeiro():

    if "user" not in session:
        return redirect('/login')
    if not tem_permissao("financeiro"):
         return "Acesso negado"

    atualizar_facturas_vencidas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM facturas WHERE estado='Pago'")
    total_pago = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM facturas WHERE estado='Em Aberto'")
    total_aberto = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM facturas WHERE estado='Dívida'")
    total_divida = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM facturas WHERE estado='Pago'")
    qtd_pagas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM facturas WHERE estado='Em Aberto'")
    qtd_abertas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM facturas WHERE estado='Dívida'")
    qtd_divida = cursor.fetchone()[0]

    cursor.execute("""
    SELECT numero, cliente, total, estado, data_factura
    FROM facturas
    ORDER BY id DESC
    LIMIT 6
    """)
    ultimas_facturas = cursor.fetchall()
    

    conn.close()

    return render_template(
        "financeiro.html",
        total_pago=total_pago,
        total_aberto=total_aberto,
        total_divida=total_divida,
        qtd_pagas=qtd_pagas,
        qtd_abertas=qtd_abertas,
        qtd_divida=qtd_divida,
        ultimas_facturas=ultimas_facturas
    )

    # =========================
# CANCELAR FACTURA
# =========================
@app.route('/cancelar-factura/<int:id>')
def cancelar_factura(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE facturas
    SET estado='Cancelada'
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/facturas')


# =========================
# APAGAR FACTURA DEFINITIVAMENTE
# =========================
@app.route('/apagar-factura/<int:id>')
def apagar_factura(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM recibos
    WHERE factura_id=%s
    """, (id,))

    cursor.execute("""
    DELETE FROM itens_factura
    WHERE factura_id=%s
    """, (id,))

    cursor.execute("""
    DELETE FROM facturas
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/facturas')

@app.route('/despesas')
def despesas():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM despesas
    ORDER BY id DESC
    """)

    despesas = cursor.fetchall()

    conn.close()

    return render_template(
        "despesas.html",
        despesas=despesas
    )

@app.route('/nova-despesa', methods=['GET', 'POST'])
def nova_despesa():

    if "user" not in session:
        return redirect('/login')

    if request.method == 'POST':

        descricao = request.form.get('descricao', '')
        categoria = request.form.get('categoria', '')
        valor = float(request.form.get('valor') or 0)
        data_vencimento = request.form.get('data_vencimento', '')
        mes = request.form.get('mes', '')
        ano = int(request.form.get('ano') or 0)
        recorrente = request.form.get('recorrente', 'Sim')
        observacao = request.form.get('observacao', '')
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO despesas (
            descricao, categoria, valor, data_vencimento,
            mes, ano, estado, recorrente, observacao, data_criacao
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            descricao, categoria, valor, data_vencimento,
            mes, ano, "Pendente", recorrente, observacao, data_criacao
        ))

        conn.commit()
        conn.close()

        return redirect('/despesas')

    return render_template("nova_despesa.html")

@app.route('/pagar-despesa/<int:id>')
def pagar_despesa(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE despesas
    SET estado='Pago'
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/despesas')

@app.route('/whatsapp-despesas')
def whatsapp_despesas():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT descricao, categoria, valor, data_vencimento
    FROM despesas
    WHERE estado='Pendente'
    ORDER BY data_vencimento ASC
    """)

    despesas = cursor.fetchall()
    conn.close()

    if not despesas:
        mensagem = "Olá, não existem despesas pendentes no momento."
    else:
        total = sum(float(d[2] or 0) for d in despesas)

        mensagem = "Olá, lembrete financeiro:%0A%0A"
        mensagem += "Existem despesas pendentes:%0A%0A"

        for d in despesas:
            mensagem += f"- {d[0]} ({d[1]}): {float(d[2] or 0):,.2f} MT | Vence: {d[3]}%0A"

        mensagem += f"%0ATotal pendente: {total:,.2f} MT"

    url = "https://wa.me/?text=" + mensagem

    return redirect(url)

@app.route('/nova-despesa-viagem', methods=['GET', 'POST'])
def nova_despesa_viagem():

    if "user" not in session:
        return redirect('/login')

    if request.method == 'POST':

        empresa = request.form.get('empresa', '')
        departamento = request.form.get('departamento', '')
        centro_custo = request.form.get('centro_custo', '')
        destino = request.form.get('destino', '')
        roteiro = request.form.get('roteiro', '')
        motivo = request.form.get('motivo', '')
        responsavel_viagem = request.form.get('responsavel_viagem', '')
        data_saida = request.form.get('data_saida', '')
        data_regresso = request.form.get('data_regresso', '')
        tipo_viagem = request.form.get('tipo_viagem', '')

        datas = request.form.getlist('data_gasto[]')
        descricoes = request.form.getlist('descricao_gasto[]')
        valores = request.form.getlist('valor_gasto[]')
        documentos = request.form.getlist('documento[]')
        pagamentos = request.form.getlist('forma_pagamento[]')

        total = 0

        for v in valores:
            try:
                total += float(v or 0)
            except:
                pass

        descricao = f"Viagem - {destino}"

        data_vencimento = datetime.now().strftime("%Y-%m-%d")
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO despesas (
            descricao,
            categoria,
            valor,
            data_vencimento,
            mes,
            ano,
            estado,
            recorrente,
            observacao,
            data_criacao,
            empresa,
            departamento,
            centro_custo,
            destino,
            roteiro,
            responsavel_viagem,
            data_saida,
            data_regresso,
            tipo_viagem
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        RETURNING id
        """, (
            descricao,
            "Viagens",
            total,
            data_vencimento,
            datetime.now().strftime("%B"),
            datetime.now().year,
            "Pendente",
            "Não",
            motivo,
            data_criacao,
            empresa,
            departamento,
            centro_custo,
            destino,
            roteiro,
            responsavel_viagem,
            data_saida,
            data_regresso,
            tipo_viagem
        ))

        despesa_id = cursor.fetchone()[0]

        for i in range(len(descricoes)):

            descricao_item = descricoes[i].strip() if i < len(descricoes) else ""

            if not descricao_item:
                continue

            data_item = datas[i] if i < len(datas) else ""
            valor_item = float(valores[i] or 0) if i < len(valores) else 0
            documento_item = documentos[i] if i < len(documentos) else ""
            pagamento_item = pagamentos[i] if i < len(pagamentos) else ""

            cursor.execute("""
            INSERT INTO itens_despesa_viagem (
                despesa_id,
                data_gasto,
                descricao,
                valor,
                documento,
                forma_pagamento
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                despesa_id,
                data_item,
                descricao_item,
                valor_item,
                documento_item,
                pagamento_item
            ))

        conn.commit()
        conn.close()

        return redirect('/despesas')

    return render_template("nova_despesa_viagem.html")
@app.route('/pdf-viagem/<int:id>')
def pdf_viagem(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM despesas
    WHERE id=%s
    """, (id,))

    despesa_row = cursor.fetchone()

    colunas = [desc[0] for desc in cursor.description]

    despesa = dict(zip(colunas, despesa_row)) if despesa_row else None

    cursor.execute("""
    SELECT data_gasto, descricao, valor, documento, forma_pagamento
    FROM itens_despesa_viagem
    WHERE despesa_id=%s
    ORDER BY id ASC
    """, (id,))

    itens = cursor.fetchall()
    conn.close()

    if not despesa:
        return "Despesa não encontrada"

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/viagem_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")

    def money(v):
        return f"{float(v or 0):,.2f} MT"

    def texto(campo):
        return str(despesa.get(campo) or "")

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 100,
            width=90,
            height=55,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(150, height - 50, "RELATÓRIO DE DESPESAS DE VIAGEM")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(150, height - 70, "Transporte Vertical, LDA")
    pdf.drawString(150, height - 85, "Av. Armando Tivane – Goto | Beira - Moçambique")
    pdf.drawString(150, height - 100, "Cell: (+258) 878340748 / 847891715")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(555, height - 55, f"Nº REL-{id:05d}/2026")
    pdf.drawRightString(555, height - 75, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 120, 555, height - 120)

    y = height - 215

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y, 515, 95, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y + 78, "DADOS DA VIAGEM")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(55, y + 60, f"Empresa: {texto('empresa')}")
    pdf.drawString(55, y + 45, f"Departamento: {texto('departamento')}")
    pdf.drawString(55, y + 30, f"Centro de Custo: {texto('centro_custo')}")
    pdf.drawString(55, y + 15, f"Saída: {texto('data_saida')}")
    pdf.drawString(180, y + 15, f"Regresso: {texto('data_regresso')}")

    pdf.drawString(300, y + 60, f"Destino: {texto('destino')}")
    pdf.drawString(300, y + 45, f"Roteiro: {texto('roteiro')}")
    pdf.drawString(300, y + 30, f"Responsável: {texto('responsavel_viagem')}")

    pdf.setFillColor(azul_claro)
    pdf.roundRect(300, y + 8, 245, 17, 4, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(310, y + 13, f"Tipo de Viagem: {texto('tipo_viagem')}")

    pdf.setFont("Helvetica", 8)
    pdf.drawString(55, y - 18, f"Motivo: {texto('observacao')[:95]}")

    tabela_y = y - 55

    pdf.setFillColor(azul)
    pdf.rect(40, tabela_y, 515, 22, fill=1)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8)

    pdf.drawString(48, tabela_y + 8, "Data")
    pdf.drawString(110, tabela_y + 8, "Descrição")
    pdf.drawString(300, tabela_y + 8, "Documento")
    pdf.drawString(400, tabela_y + 8, "Pagamento")
    pdf.drawString(500, tabela_y + 8, "Valor")

    y_item = tabela_y - 18

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    for item in itens:

        if y_item < 120:
            break

        data_gasto = item[0] or ""
        descricao = item[1] or ""
        valor = float(item[2] or 0)
        documento = item[3] or ""
        pagamento = item[4] or ""

        pdf.drawString(48, y_item, data_gasto)
        pdf.drawString(110, y_item, descricao[:35])
        pdf.drawString(300, y_item, documento[:18])
        pdf.drawString(400, y_item, pagamento[:18])
        pdf.drawRightString(545, y_item, money(valor))

        pdf.setStrokeColor(cinza)
        pdf.line(40, y_item - 5, 555, y_item - 5)

        y_item -= 18

    total_y = y_item - 35

    pdf.setFillColor(azul_claro)
    pdf.setStrokeColor(azul)
    pdf.roundRect(360, total_y, 195, 45, 6, fill=1)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(375, total_y + 17, "TOTAL:")
    pdf.drawRightString(540, total_y + 17, money(despesa.get("valor")))

    assinatura_y = 75

    pdf.setStrokeColor(colors.black)
    pdf.line(55, assinatura_y, 225, assinatura_y)
    pdf.line(330, assinatura_y, 520, assinatura_y)

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(140, assinatura_y - 15, "Preparado por")
    pdf.drawCentredString(425, assinatura_y - 15, "Aprovado por")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 30, "Documento gerado automaticamente pelo sistema.")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RELATORIO_VIAGEM_{id}.pdf"
    )
@app.route('/clientes-financeiros')
def clientes_financeiros():

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        cliente,
        nuit,
        COUNT(*) as total_facturas,
        SUM(total) as valor_total
    FROM facturas
    GROUP BY cliente, nuit
    ORDER BY cliente
    """)

    clientes = cursor.fetchall()
    

    conn.close()

    return render_template(
        "clientes_financeiros.html",
        clientes=clientes
    )
@app.route('/cliente-financeiro/<nuit>')
def cliente_financeiro(nuit):

    if "user" not in session:
        return redirect('/login')

    if not tem_permissao("financeiro"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM facturas
    WHERE nuit=%s
    ORDER BY id DESC
    """, (nuit,))

    facturas = cursor.fetchall()

    cursor.execute("""
    SELECT *
    FROM recibos
    WHERE numero_factura IN (
        SELECT numero
        FROM facturas
        WHERE nuit=%s
    )
    ORDER BY id DESC
    """, (nuit,))

    recibos = cursor.fetchall()

    cursor.execute("""
    SELECT
        COALESCE(SUM(total), 0),
        COUNT(*)
    FROM facturas
    WHERE nuit=%s
    """, (nuit,))

    resumo_facturas = cursor.fetchone()

    cursor.execute("""
    SELECT COALESCE(SUM(valor_pago), 0)
    FROM recibos
    WHERE numero_factura IN (
        SELECT numero
        FROM facturas
        WHERE nuit=%s
    )
    """, (nuit,))

    total_recebido = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COALESCE(SUM(total), 0)
    FROM facturas
    WHERE nuit=%s AND estado!='Pago'
    """, (nuit,))

    total_pendente = cursor.fetchone()[0]

    cursor.execute("""
    SELECT cliente, morada, celular
    FROM facturas
    WHERE nuit=%s
    ORDER BY id DESC
    LIMIT 1
    """, (nuit,))

    dados_cliente = cursor.fetchone()

    conn.close()

    return render_template(
        "cliente_financeiro.html",
        nuit=nuit,
        facturas=facturas,
        recibos=recibos,
        resumo_facturas=resumo_facturas,
        total_recebido=total_recebido,
        total_pendente=total_pendente,
        dados_cliente=dados_cliente
    )

@app.route('/clientes', methods=['GET', 'POST'])
def clientes():

    if "user" not in session:
        return redirect('/login')

    if not tem_permissao("financeiro"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        nuit = request.form.get('nuit', '').strip()
        endereco = request.form.get('endereco', '').strip()
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        if not nome:
            conn.close()
            return "Erro: informe o nome do cliente."

        if nuit:
            cursor.execute("""
            SELECT id
            FROM clientes
            WHERE nuit=%s
            """, (nuit,))

            cliente_existente = cursor.fetchone()

            if cliente_existente:
                conn.close()
                return "⚠️ Já existe um cliente com este NUIT."

        cursor.execute("""
        INSERT INTO clientes (
            nome,
            nuit,
            endereco,
            data_criacao
        )
        VALUES (%s, %s, %s, %s)
        """, (
            nome,
            nuit,
            endereco,
            data_criacao
        ))

        conn.commit()

    cursor.execute("""
    SELECT
        c.id,
        c.nome,
        c.nuit,
        c.endereco,
        c.data_criacao,
        COUNT(f.id) AS total_facturas,
        COALESCE(SUM(f.total), 0) AS total_facturado,
        MAX(f.data_factura) AS ultima_factura
    FROM clientes c
    LEFT JOIN facturas f
        ON c.nuit = f.nuit
    GROUP BY
        c.id,
        c.nome,
        c.nuit,
        c.endereco,
        c.data_criacao
    ORDER BY c.nome
    """)

    clientes = cursor.fetchall()

    conn.close()

    return render_template(
        "clientes.html",
        clientes=clientes
    )
@app.route('/editar-cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):

    if "user" not in session:
        return redirect('/login')

    if not tem_permissao("financeiro"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        nuit = request.form.get('nuit', '').strip()
        endereco = request.form.get('endereco', '').strip()

        cursor.execute("""
        UPDATE clientes
        SET
            nome=%s,
            nuit=%s,
            endereco=%s
        WHERE id=%s
        """, (
            nome,
            nuit,
            endereco,
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/clientes')

    cursor.execute("""
    SELECT *
    FROM clientes
    WHERE id=%s
    """, (id,))

    cliente = cursor.fetchone()

    conn.close()

    return render_template(
        "editar_cliente.html",
        cliente=cliente
    )

@app.route('/apagar-cliente/<int:id>')
def apagar_cliente(id):

    if "user" not in session:
        return redirect('/login')

    if not tem_permissao("financeiro"):
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nuit
    FROM clientes
    WHERE id=%s
    """, (id,))

    cliente = cursor.fetchone()

    if not cliente:
        conn.close()
        return "Cliente não encontrado."

    nuit = cliente[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE nuit=%s
    """, (nuit,))

    total_facturas = cursor.fetchone()[0]

    if total_facturas > 0:
        conn.close()
        return "Não é possível eliminar este cliente porque possui facturas registadas."

    cursor.execute("""
    DELETE FROM clientes
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/clientes')

@app.route('/empresas-manutencao', methods=['GET', 'POST'])
def empresas_manutencao():

    if "user" not in session:
        return redirect('/login')
    if not session.get("manutencao_autorizado"):
        return redirect('/acesso-manutencao')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        contacto = request.form.get('contacto', '').strip()
        responsavel = request.form.get('responsavel', '').strip()
        tipo_equipamento = request.form.get('tipo_equipamento', '').strip()
        quantidade_equipamentos = int(request.form.get('quantidade_equipamentos') or 0)
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
        INSERT INTO empresas_manutencao (
            nome,
            localizacao,
            contacto,
            responsavel,
            tipo_equipamento,
            quantidade_equipamentos,
            estado,
            data_criacao
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            nome,
            localizacao,
            contacto,
            responsavel,
            tipo_equipamento,
            quantidade_equipamentos,
            "Ativo",
            data_criacao
        ))

        conn.commit()

    cursor.execute("""
    SELECT *
    FROM empresas_manutencao
    ORDER BY id DESC
    """)

    empresas = cursor.fetchall()

    conn.close()

    return render_template(
        "empresas_manutencao.html",
        empresas=empresas
    )

@app.route('/nova-manutencao', methods=['GET', 'POST'])
def nova_manutencao():

    if "user" not in session:
        return redirect('/login')
    if not session.get("manutencao_autorizado"):
        return redirect('/acesso-manutencao')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        empresa_id = request.form.get('empresa_id')
        data_manutencao = request.form.get('data_manutencao', '')
        tipo_manutencao = request.form.get('tipo_manutencao', '')
        tecnico = request.form.get('tecnico', '')
        descricao_servico = request.form.get('descricao_servico', '')
        proxima_manutencao = request.form.get('proxima_manutencao', '')
        observacao = request.form.get('observacao', '')
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
        INSERT INTO manutencoes (
            empresa_id,
            data_manutencao,
            tipo_manutencao,
            tecnico,
            descricao_servico,
            estado,
            proxima_manutencao,
            observacao,
            data_criacao
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            empresa_id,
            data_manutencao,
            tipo_manutencao,
            tecnico,
            descricao_servico,
            "Concluída",
            proxima_manutencao,
            observacao,
            data_criacao
        ))

        conn.commit()
        conn.close()

        return redirect('/empresas-manutencao')

    cursor.execute("""
    SELECT id, nome
    FROM empresas_manutencao
    WHERE estado='Ativo'
    ORDER BY nome
    """)

    empresas = cursor.fetchall()

    conn.close()

    return render_template(
        "nova_manutencao.html",
        empresas=empresas
    )

@app.route('/nova-avaria', methods=['GET', 'POST'])
def nova_avaria():

    if "user" not in session:
        return redirect('/login')
    if not session.get("manutencao_autorizado"):
        return redirect('/acesso-manutencao')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        empresa_id = request.form.get('empresa_id')
        data_avaria = request.form.get('data_avaria', '')
        equipamento = request.form.get('equipamento', '')
        descricao = request.form.get('descricao', '')
        prioridade = request.form.get('prioridade', '')
        tecnico = request.form.get('tecnico', '')
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
        INSERT INTO avarias (
            empresa_id,
            data_avaria,
            equipamento,
            descricao,
            prioridade,
            estado,
            tecnico,
            data_criacao
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            empresa_id,
            data_avaria,
            equipamento,
            descricao,
            prioridade,
            "Aberta",
            tecnico,
            data_criacao
        ))

        conn.commit()
        conn.close()

        return redirect('/empresas-manutencao')

    cursor.execute("""
    SELECT id, nome
    FROM empresas_manutencao
    WHERE estado='Ativo'
    ORDER BY nome
    """)

    empresas = cursor.fetchall()

    conn.close()

    return render_template(
        "nova_avaria.html",
        empresas=empresas
    )
@app.route('/empresa-manutencao/<int:id>')
def empresa_manutencao(id):

    if "user" not in session:
        return redirect('/login')
    if not session.get("manutencao_autorizado"):
        return redirect('/acesso-manutencao')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM empresas_manutencao
    WHERE id=%s
    """, (id,))

    empresa = cursor.fetchone()

    if not empresa:
        conn.close()
        return "Empresa não encontrada."

    cursor.execute("""
    SELECT *
    FROM manutencoes
    WHERE empresa_id=%s
    ORDER BY id DESC
    """, (id,))

    manutencoes = cursor.fetchall()

    cursor.execute("""
    SELECT *
    FROM avarias
    WHERE empresa_id=%s
    ORDER BY id DESC
    """, (id,))

    avarias = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*)
    FROM manutencoes
    WHERE empresa_id=%s
    """, (id,))

    total_manutencoes = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM avarias
    WHERE empresa_id=%s AND estado!='Resolvida'
    """, (id,))

    avarias_abertas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM avarias
    WHERE empresa_id=%s AND estado='Resolvida'
    """, (id,))

    avarias_resolvidas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT proxima_manutencao
    FROM manutencoes
    WHERE empresa_id=%s
    ORDER BY id DESC
    LIMIT 1
    """, (id,))

    prox = cursor.fetchone()
    proxima_manutencao = prox[0] if prox else ""
    cursor.execute("""
    SELECT *
    FROM equipamentos_manutencao
    WHERE empresa_id=%s
    ORDER BY id DESC
    """, (id,))

    equipamentos = cursor.fetchall()

    conn.close()

    return render_template(
        "empresa_manutencao.html",
        empresa=empresa,
        manutencoes=manutencoes,
        avarias=avarias,
        total_manutencoes=total_manutencoes,
        avarias_abertas=avarias_abertas,
        avarias_resolvidas=avarias_resolvidas,
        proxima_manutencao=proxima_manutencao,
        equipamentos=equipamentos
    )
@app.route('/resolver-avaria/<int:id>', methods=['GET', 'POST'])
def resolver_avaria(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM avarias
    WHERE id=%s
    """, (id,))

    avaria = cursor.fetchone()

    if not avaria:
        conn.close()
        return "Avaria não encontrada."

    if request.method == 'POST':

        tecnico = request.form.get('tecnico', '')
        solucao = request.form.get('solucao', '')
        data_resolucao = request.form.get('data_resolucao', '')

        cursor.execute("""
        UPDATE avarias
        SET
            tecnico=%s,
            solucao=%s,
            data_resolucao=%s,
            estado='Resolvida'
        WHERE id=%s
        """, (
            tecnico,
            solucao,
            data_resolucao,
            id
        ))

        conn.commit()
        empresa_id = avaria[1]
        conn.close()

        return redirect(f'/empresa-manutencao/{empresa_id}')

    conn.close()

    return render_template(
        "resolver_avaria.html",
        avaria=avaria
    )


@app.route('/dashboard-manutencao')
def dashboard_manutencao():

    if "user" not in session:
        return redirect('/login')
    if not session.get("manutencao_autorizado"):
        return redirect('/acesso-manutencao')
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM empresas_manutencao
    WHERE estado='Ativo'
    """)
    empresas_ativas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM manutencoes
    """)
    total_manutencoes = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM avarias
    WHERE estado!='Resolvida'
    """)
    avarias_abertas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM avarias
    WHERE estado='Resolvida'
    """)
    avarias_resolvidas = cursor.fetchone()[0]

    cursor.execute("""
    SELECT
        a.id,
        e.nome,
        a.equipamento,
        a.descricao,
        a.prioridade,
        a.estado,
        a.data_avaria
    FROM avarias a
    JOIN empresas_manutencao e
        ON a.empresa_id = e.id
    WHERE a.estado!='Resolvida'
    ORDER BY a.id DESC
    LIMIT 10
    """)
    avarias_pendentes = cursor.fetchall()

    cursor.execute("""
    SELECT
        m.id,
        e.nome,
        m.data_manutencao,
        m.tipo_manutencao,
        m.tecnico,
        m.proxima_manutencao
    FROM manutencoes m
    JOIN empresas_manutencao e
        ON m.empresa_id = e.id
    ORDER BY m.id DESC
    LIMIT 10
    """)
    ultimas_manutencoes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard_manutencao.html",
        empresas_ativas=empresas_ativas,
        total_manutencoes=total_manutencoes,
        avarias_abertas=avarias_abertas,
        avarias_resolvidas=avarias_resolvidas,
        avarias_pendentes=avarias_pendentes,
        ultimas_manutencoes=ultimas_manutencoes
    )

@app.route('/pdf-manutencao/<int:id>')
def pdf_manutencao(id):

    if "user" not in session:
        return redirect('/login')
    

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        m.id,
        m.data_manutencao,
        m.tipo_manutencao,
        m.tecnico,
        m.descricao_servico,
        m.estado,
        m.proxima_manutencao,
        m.observacao,
        e.nome,
        e.localizacao,
        e.contacto,
        e.responsavel,
        e.tipo_equipamento
    FROM manutencoes m
    JOIN empresas_manutencao e
        ON m.empresa_id = e.id
    WHERE m.id=%s
    """, (id,))

    dados = cursor.fetchone()
    conn.close()

    if not dados:
        return "Manutenção não encontrada."

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/manutencao_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 105,
            width=120,
            height=75,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(175, height - 50, "RELATÓRIO TÉCNICO DE MANUTENÇÃO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(175, height - 70, "Transporte Vertical, LDA")
    pdf.drawString(175, height - 85, "Av. Armando Tivane – Goto | Beira - Moçambique")
    pdf.drawString(175, height - 100, "Cell: (+258) 878340748 / 847891715")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(555, height - 55, f"Nº RT-{id:05d}/2026")
    pdf.drawRightString(555, height - 75, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    pdf.setStrokeColor(azul)
    pdf.line(40, height - 125, 555, height - 125)

    y = height - 215

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y, 515, 85, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y + 68, "DADOS DO CLIENTE / EQUIPAMENTO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(55, y + 50, f"Empresa: {dados[8] or ''}")
    pdf.drawString(55, y + 35, f"Localização: {dados[9] or ''}")
    pdf.drawString(55, y + 20, f"Contacto: {dados[10] or ''}")

    pdf.drawString(310, y + 50, f"Responsável: {dados[11] or ''}")
    pdf.drawString(310, y + 35, f"Equipamento: {dados[12] or ''}")
    pdf.drawString(310, y + 20, f"Estado: {dados[5] or ''}")

    y2 = y - 120

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y2, 515, 100, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y2 + 82, "DADOS DA MANUTENÇÃO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(55, y2 + 62, f"Data da Manutenção: {dados[1] or ''}")
    pdf.drawString(55, y2 + 47, f"Tipo: {dados[2] or ''}")
    pdf.drawString(55, y2 + 32, f"Técnico: {dados[3] or ''}")
    pdf.drawString(310, y2 + 62, f"Próxima Manutenção: {dados[6] or ''}")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(55, y2 + 12, "Serviço Executado:")

    pdf.setFont("Helvetica", 8)
    servico = str(dados[4] or "")
    linhas = [servico[i:i+85] for i in range(0, len(servico), 85)]

    texto_y = y2 - 8

    for linha in linhas[:5]:
        pdf.drawString(55, texto_y, linha)
        texto_y -= 12

    obs_y = texto_y - 25

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, obs_y, 515, 65, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, obs_y + 48, "OBSERVAÇÕES")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    observacao = str(dados[7] or "")
    obs_linhas = [observacao[i:i+95] for i in range(0, len(observacao), 95)]

    obs_text_y = obs_y + 30

    for linha in obs_linhas[:3]:
        pdf.drawString(55, obs_text_y, linha)
        obs_text_y -= 12

    assinatura_y = 90

    pdf.setStrokeColor(colors.black)
    pdf.line(55, assinatura_y, 225, assinatura_y)
    pdf.line(330, assinatura_y, 520, assinatura_y)

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(140, assinatura_y - 15, "Assinatura do Técnico")
    pdf.drawCentredString(425, assinatura_y - 15, "Assinatura do Cliente")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 30, "Documento gerado automaticamente pelo sistema.")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RELATORIO_MANUTENCAO_{id}.pdf"
    )
@app.route('/editar-manutencao/<int:id>', methods=['GET', 'POST'])
def editar_manutencao(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM manutencoes
    WHERE id=%s
    """, (id,))

    manutencao = cursor.fetchone()

    if not manutencao:
        conn.close()
        return "Manutenção não encontrada."

    if request.method == 'POST':

        data_manutencao = request.form.get('data_manutencao')
        tipo_manutencao = request.form.get('tipo_manutencao')
        tecnico = request.form.get('tecnico')
        descricao_servico = request.form.get('descricao_servico')
        estado = request.form.get('estado')
        proxima_manutencao = request.form.get('proxima_manutencao')
        observacao = request.form.get('observacao')

        cursor.execute("""
        UPDATE manutencoes
        SET
            data_manutencao=%s,
            tipo_manutencao=%s,
            tecnico=%s,
            descricao_servico=%s,
            estado=%s,
            proxima_manutencao=%s,
            observacao=%s
        WHERE id=%s
        """, (
            data_manutencao,
            tipo_manutencao,
            tecnico,
            descricao_servico,
            estado,
            proxima_manutencao,
            observacao,
            id
        ))

        conn.commit()

        empresa_id = manutencao[1]

        conn.close()

        return redirect(f'/empresa-manutencao/{empresa_id}')

    conn.close()

    return render_template(
        'editar_manutencao.html',
        manutencao=manutencao
    )
@app.route('/apagar-manutencao/<int:id>')
def apagar_manutencao(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT empresa_id
    FROM manutencoes
    WHERE id=%s
    """, (id,))

    manutencao = cursor.fetchone()

    if not manutencao:
        conn.close()
        return "Manutenção não encontrada."

    empresa_id = manutencao[0]

    cursor.execute("""
    DELETE FROM manutencoes
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(f'/empresa-manutencao/{empresa_id}')

@app.route('/pdf-avaria/<int:id>')
def pdf_avaria(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        a.id,
        a.data_avaria,
        a.equipamento,
        a.descricao,
        a.prioridade,
        a.estado,
        a.tecnico,
        a.solucao,
        a.data_resolucao,
        e.nome,
        e.localizacao,
        e.contacto,
        e.responsavel,
        e.tipo_equipamento
    FROM avarias a
    JOIN empresas_manutencao e
        ON a.empresa_id = e.id
    WHERE a.id=%s
    """, (id,))

    dados = cursor.fetchone()
    conn.close()

    if not dados:
        return "Avaria não encontrada."

    os.makedirs("pdfs", exist_ok=True)

    file_path = f"pdfs/avaria_{id}.pdf"

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    azul = colors.HexColor("#0d47a1")
    vermelho = colors.HexColor("#d32f2f")
    cinza = colors.HexColor("#eeeeee")
    azul_claro = colors.HexColor("#e3f2fd")

    logo_path = "static/logo/logo.png"

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            40,
            height - 105,
            width=120,
            height=75,
            preserveAspectRatio=True,
            mask='auto'
        )

    pdf.setFillColor(vermelho)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(175, height - 50, "RELATÓRIO TÉCNICO DE AVARIA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(175, height - 70, "Transporte Vertical, LDA")
    pdf.drawString(175, height - 85, "Av. Armando Tivane – Goto | Beira - Moçambique")
    pdf.drawString(175, height - 100, "Cell: (+258) 878340748 / 847891715")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(555, height - 55, f"Nº RA-{id:05d}/2026")
    pdf.drawRightString(555, height - 75, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    pdf.setStrokeColor(vermelho)
    pdf.line(40, height - 125, 555, height - 125)

    y = height - 215

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y, 515, 85, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y + 68, "DADOS DO CLIENTE / EQUIPAMENTO")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(55, y + 50, f"Empresa: {dados[9] or ''}")
    pdf.drawString(55, y + 35, f"Localização: {dados[10] or ''}")
    pdf.drawString(55, y + 20, f"Contacto: {dados[11] or ''}")

    pdf.drawString(310, y + 50, f"Responsável: {dados[12] or ''}")
    pdf.drawString(310, y + 35, f"Tipo Equipamento: {dados[13] or ''}")
    pdf.drawString(310, y + 20, f"Equipamento: {dados[2] or ''}")

    y2 = y - 125

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, y2, 515, 115, 6, fill=0)

    pdf.setFillColor(vermelho)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y2 + 97, "DADOS DA AVARIA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(55, y2 + 78, f"Data da Avaria: {dados[1] or ''}")
    pdf.drawString(55, y2 + 63, f"Prioridade: {dados[4] or ''}")
    pdf.drawString(55, y2 + 48, f"Estado: {dados[5] or ''}")

    pdf.drawString(310, y2 + 78, f"Técnico: {dados[6] or ''}")
    pdf.drawString(310, y2 + 63, f"Data de Resolução: {dados[8] or ''}")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(55, y2 + 25, "Descrição da Avaria:")

    pdf.setFont("Helvetica", 8)
    descricao = str(dados[3] or "")
    linhas = [descricao[i:i+95] for i in range(0, len(descricao), 95)]

    texto_y = y2 + 10
    for linha in linhas[:3]:
        pdf.drawString(55, texto_y, linha)
        texto_y -= 12

    solucao_y = y2 - 95

    pdf.setStrokeColor(cinza)
    pdf.roundRect(40, solucao_y, 515, 85, 6, fill=0)

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, solucao_y + 68, "SOLUÇÃO APLICADA")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    solucao = str(dados[7] or "Avaria ainda não resolvida.")
    sol_linhas = [solucao[i:i+95] for i in range(0, len(solucao), 95)]

    sol_text_y = solucao_y + 50
    for linha in sol_linhas[:4]:
        pdf.drawString(55, sol_text_y, linha)
        sol_text_y -= 12

    assinatura_y = 90

    pdf.setStrokeColor(colors.black)
    pdf.line(55, assinatura_y, 225, assinatura_y)
    pdf.line(330, assinatura_y, 520, assinatura_y)

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(140, assinatura_y - 15, "Assinatura do Técnico")
    pdf.drawCentredString(425, assinatura_y - 15, "Assinatura do Cliente")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 30, "Documento gerado automaticamente pelo sistema.")

    pdf.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"RELATORIO_AVARIA_{id}.pdf"
    )
@app.route('/editar-avaria/<int:id>', methods=['GET', 'POST'])
def editar_avaria(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM avarias
    WHERE id=%s
    """, (id,))

    avaria = cursor.fetchone()

    if not avaria:
        conn.close()
        return "Avaria não encontrada."

    if request.method == 'POST':

        equipamento = request.form.get('equipamento')
        descricao = request.form.get('descricao')
        prioridade = request.form.get('prioridade')
        estado = request.form.get('estado')
        tecnico = request.form.get('tecnico')

        cursor.execute("""
        UPDATE avarias
        SET
            equipamento=%s,
            descricao=%s,
            prioridade=%s,
            estado=%s,
            tecnico=%s
        WHERE id=%s
        """, (
            equipamento,
            descricao,
            prioridade,
            estado,
            tecnico,
            id
        ))

        conn.commit()

        empresa_id = avaria[1]

        conn.close()

        return redirect(f'/empresa-manutencao/{empresa_id}')

    conn.close()

    return render_template(
        'editar_avaria.html',
        avaria=avaria
    )

@app.route('/apagar-avaria/<int:id>')
def apagar_avaria(id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT empresa_id
    FROM avarias
    WHERE id=%s
    """, (id,))

    avaria = cursor.fetchone()

    if not avaria:
        conn.close()
        return "Avaria não encontrada."

    empresa_id = avaria[0]

    cursor.execute("""
    DELETE FROM avarias
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(f'/empresa-manutencao/{empresa_id}')

@app.route('/novo-equipamento/<int:empresa_id>', methods=['GET', 'POST'])
def novo_equipamento(empresa_id):

    if "user" not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        nome = request.form.get('nome', '')
        marca = request.form.get('marca', '')
        modelo = request.form.get('modelo', '')
        numero_serie = request.form.get('numero_serie', '')
        localizacao = request.form.get('localizacao', '')

        cursor.execute("""
        INSERT INTO equipamentos_manutencao (
            empresa_id,
            nome,
            marca,
            modelo,
            numero_serie,
            localizacao,
            data_criacao
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            empresa_id,
            nome,
            marca,
            modelo,
            numero_serie,
            localizacao,
            datetime.now().strftime("%d/%m/%Y")
        ))

        conn.commit()
        conn.close()

        return redirect(f'/empresa-manutencao/{empresa_id}')

    cursor.execute("""
    SELECT nome
    FROM empresas_manutencao
    WHERE id=%s
    """, (empresa_id,))

    empresa = cursor.fetchone()

    conn.close()

    return render_template(
        'novo_equipamento.html',
        empresa=empresa,
        empresa_id=empresa_id
    )
    
@app.route('/acesso-manutencao', methods=['GET', 'POST'])
def acesso_manutencao():

    if "user" not in session:
        return redirect('/login')

    if request.method == 'POST':

        senha = request.form.get('senha_manutencao', '')

        if senha == SENHA_MANUTENCAO:
            session['manutencao_autorizado'] = True
            return redirect('/dashboard-manutencao')

        return render_template(
    "acesso_manutencao.html",
    erro="Senha de manutenção inválida."
)

    return render_template("acesso_manutencao.html")

@app.route('/sair-manutencao')
def sair_manutencao():

    session.pop("manutencao_autorizado", None)

    return redirect('/')  

@app.route('/apagar-folha/<int:id>')
def apagar_folha(id):

    if "user" not in session:
        return redirect('/login')

    if not rh_autorizado():
        return redirect('/acesso-rh')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM folhas_salariais
    WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/folhas') 

    
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