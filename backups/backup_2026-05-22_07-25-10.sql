--
-- PostgreSQL database dump
--

\restrict ICd1v3zZaekn0eSct9f4fRmSzVqB6S8gPdtZswwSRbO73XaeFvRqDM4qM4FwcsJ

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cotacoes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cotacoes (
    id integer NOT NULL,
    cliente text,
    empresa text,
    endereco text,
    nuit text,
    pagamento text,
    prazo text,
    nb text,
    subtotal real,
    iva real,
    total real
);


ALTER TABLE public.cotacoes OWNER TO postgres;

--
-- Name: cotacoes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cotacoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cotacoes_id_seq OWNER TO postgres;

--
-- Name: cotacoes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cotacoes_id_seq OWNED BY public.cotacoes.id;


--
-- Name: folhas_salariais; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.folhas_salariais (
    id integer NOT NULL,
    funcionario_id integer,
    mes text,
    ano integer,
    horas_normais real,
    horas_extras real,
    valor_horas_normais real,
    valor_horas_extras real,
    descontos real,
    total_bruto real,
    total_liquido real,
    data_criacao text,
    horas_extra_50 real DEFAULT 0,
    horas_extra_100 real DEFAULT 0,
    valor_extra_50 real DEFAULT 0,
    valor_extra_100 real DEFAULT 0,
    inss real DEFAULT 0,
    outros_descontos real DEFAULT 0
);


ALTER TABLE public.folhas_salariais OWNER TO postgres;

--
-- Name: folhas_salariais_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.folhas_salariais_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.folhas_salariais_id_seq OWNER TO postgres;

--
-- Name: folhas_salariais_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.folhas_salariais_id_seq OWNED BY public.folhas_salariais.id;


--
-- Name: funcionarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.funcionarios (
    id integer NOT NULL,
    nome text NOT NULL,
    cargo text,
    salario_hora real DEFAULT 0 NOT NULL,
    telefone text,
    estado text DEFAULT 'Ativo'::text,
    tipo text DEFAULT 'Funcionário'::text,
    bi text,
    nuit text,
    email text,
    endereco text
);


ALTER TABLE public.funcionarios OWNER TO postgres;

--
-- Name: funcionarios_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.funcionarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.funcionarios_id_seq OWNER TO postgres;

--
-- Name: funcionarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.funcionarios_id_seq OWNED BY public.funcionarios.id;


--
-- Name: itens_cotacao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.itens_cotacao (
    id integer NOT NULL,
    cotacao_id integer,
    quantidade real,
    unidade text,
    descricao text,
    preco real,
    subtotal real,
    produto_id integer
);


ALTER TABLE public.itens_cotacao OWNER TO postgres;

--
-- Name: itens_cotacao_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.itens_cotacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.itens_cotacao_id_seq OWNER TO postgres;

--
-- Name: itens_cotacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.itens_cotacao_id_seq OWNED BY public.itens_cotacao.id;


--
-- Name: movimentacoes_estoque; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.movimentacoes_estoque (
    id integer NOT NULL,
    produto_id integer,
    funcionario_id integer,
    tipo_movimento text,
    tipo_saida text,
    quantidade real DEFAULT 0,
    responsavel text,
    servico_obra text,
    observacao text,
    data_movimento text,
    data_prevista_devolucao text,
    estado_devolucao text DEFAULT 'Não aplicável'::text,
    confirmado text DEFAULT 'Não'::text,
    assinatura text
);


ALTER TABLE public.movimentacoes_estoque OWNER TO postgres;

--
-- Name: movimentacoes_estoque_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.movimentacoes_estoque_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.movimentacoes_estoque_id_seq OWNER TO postgres;

--
-- Name: movimentacoes_estoque_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.movimentacoes_estoque_id_seq OWNED BY public.movimentacoes_estoque.id;


--
-- Name: produtos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.produtos (
    id integer NOT NULL,
    nome text NOT NULL,
    categoria text,
    codigo text,
    quantidade real DEFAULT 0,
    unidade text,
    preco_compra real DEFAULT 0,
    estoque_minimo real DEFAULT 5
);


ALTER TABLE public.produtos OWNER TO postgres;

--
-- Name: produtos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.produtos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.produtos_id_seq OWNER TO postgres;

--
-- Name: produtos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.produtos_id_seq OWNED BY public.produtos.id;


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    username text,
    password text,
    tipo text DEFAULT 'normal'::text
);


ALTER TABLE public.usuarios OWNER TO postgres;

--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuarios_id_seq OWNER TO postgres;

--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;


--
-- Name: cotacoes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotacoes ALTER COLUMN id SET DEFAULT nextval('public.cotacoes_id_seq'::regclass);


--
-- Name: folhas_salariais id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.folhas_salariais ALTER COLUMN id SET DEFAULT nextval('public.folhas_salariais_id_seq'::regclass);


--
-- Name: funcionarios id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.funcionarios ALTER COLUMN id SET DEFAULT nextval('public.funcionarios_id_seq'::regclass);


--
-- Name: itens_cotacao id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.itens_cotacao ALTER COLUMN id SET DEFAULT nextval('public.itens_cotacao_id_seq'::regclass);


--
-- Name: movimentacoes_estoque id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimentacoes_estoque ALTER COLUMN id SET DEFAULT nextval('public.movimentacoes_estoque_id_seq'::regclass);


--
-- Name: produtos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.produtos ALTER COLUMN id SET DEFAULT nextval('public.produtos_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Data for Name: cotacoes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cotacoes (id, cliente, empresa, endereco, nuit, pagamento, prazo, nb, subtotal, iva, total) FROM stdin;
3	CFM-Centro	Fornecimento, reposição dos acessórios e reparação de elevador "A e B" 	Largos dos CFM-Beira	6000000047	60/40	15 dias após aprovação da proposta		2.75775e+06	441240	3.19899e+06
5	CFM	manutenção do elevador	MATACUANE	1152325	60/40	15 dias após aprovação da proposta		276	44.16	320.16
6	CFM	manutenção do elevador	MATACUANE	1152325	60/40	15 dias após aprovação da proposta		11	1.76	12.76
4	CFM-Centro	Fornecimento, reposição dos acessórios e reparação de elevador "A e C"	Largos dos CFM-Beira	6000000047	60/40	15 dias após aprovação da proposta		2.49665e+06	399464	2.896114e+06
7	TMCEL	trwrrewe	Beira	000012	100	15 dias após aprovação da proposta		19029	3044.64	22073.64
\.


--
-- Data for Name: folhas_salariais; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.folhas_salariais (id, funcionario_id, mes, ano, horas_normais, horas_extras, valor_horas_normais, valor_horas_extras, descontos, total_bruto, total_liquido, data_criacao, horas_extra_50, horas_extra_100, valor_extra_50, valor_extra_100, inss, outros_descontos) FROM stdin;
1	1	Janeiro	2026	250	\N	25000	\N	\N	29500	28615	18/05/2026	10	15	1500	3000	885	0
2	1	Janeiro	2026	240	\N	24000	\N	\N	26700	25899	19/05/2026	14	3	2100	600	801	0
3	3	Janeiro	2026	240	\N	12000	\N	\N	14750	14307.5	19/05/2026	10	20	750	2000	442.5	0
4	3	Janeiro	2026	240	\N	12000	\N	\N	13750	13337.5	19/05/2026	10	10	750	1000	412.5	0
5	1	Maio	2026	240	\N	24000	\N	\N	26800	25996	20/05/2026	12	5	1800	1000	804	0
\.


--
-- Data for Name: funcionarios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.funcionarios (id, nome, cargo, salario_hora, telefone, estado, tipo, bi, nuit, email, endereco) FROM stdin;
1	valter	TI	100	867662019	Ativo	Funcionário	\N	\N	\N	\N
3	Maria fzimbe	Motorista	50	85621581	Ativo	Funcionário	\N	\N	\N	\N
2	Maria frascisco	Motorista	166	856625165	Inativo	Funcionário	\N	\N	\N	\N
\.


--
-- Data for Name: itens_cotacao; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.itens_cotacao (id, cotacao_id, quantidade, unidade, descricao, preco, subtotal, produto_id) FROM stdin;
3	3	50	un	Base de Roçadeiras  (Elevador - A)	5336	266800	\N
4	3	72	un	Rodas de excêntricas (Elevador - A e B)	7200	518400	\N
5	3	72	un	Roçadeira de portas  (Elevador - A e B)	1200	86400	\N
6	3	4	un	Correia de operadores de portas  (Elevador - A e B)	4100	16400	\N
7	3	2	un	Placas de indicador de piso  (Elevador - A)	28725	57450	\N
8	3	41	un	Roletes de araste de portas  (Elevador - A e B)	9100	373100	\N
9	3	2	un	Vedante de Regulador de velocidade  (Elevador - A e B)	3900	7800	\N
10	3	4	un	Borracha de base de motor e de contra peso (Elevador - A e B)	7150	28600	\N
11	3	200	un	Cabo de regulador de velocidade  (Elevador - A e B)	6900	1.38e+06	\N
12	3	8	un	Cabos de arraste de portas (Elevador - A e B)	2850	22800	\N
23	5	12	un	Concordo que o ambiente e o marketing influenciam bastante	23	276	\N
24	6	1	un	Concordo que o ambiente e o marketing influenciam bastante	11	11	\N
57	4	50	un	Manufactura de pecas conforme a amostra (Elevador - C)	4600	230000	\N
58	4	72	un	Rodas de excêntricas (Elevador - A )	7200	518400	\N
59	4	72	un	Roçadeira de portas (Elevador - A )	1200	86400	\N
60	4	4	un	Correia de operadores de portas (Elevador - A)	4100	16400	\N
61	4	2	un	Placas de indicador de piso (Elevador - A)	28725	57450	\N
62	4	8	un	Roletes de araste de portas (Elevador - A )	9100	72800	\N
63	4	2	un	Vedante de Regulador de velocidade (Elevador - A )	3900	7800	\N
64	4	4	un	Borracha de base de motor e de contra peso (Elevador - A)	7150	28600	\N
65	4	200	m	Cabo de regulador de velocidade (Elevador - A)	6900	1.38e+06	\N
66	4	8	un	Cabos de arraste de portas (Elevador - A)	2850	22800	\N
67	4	4	un	Base de Rocadeiras-C	19000	76000	\N
68	7	54	un	Rodas Execentricas	300	16200	\N
69	7	23	m²	Cabo de aco	123	2829	\N
\.


--
-- Data for Name: movimentacoes_estoque; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.movimentacoes_estoque (id, produto_id, funcionario_id, tipo_movimento, tipo_saida, quantidade, responsavel, servico_obra, observacao, data_movimento, data_prevista_devolucao, estado_devolucao, confirmado, assinatura) FROM stdin;
6	4	3	Saída	Consumo	5	admin	CFM		22/05/2026 05:00		Não aplicável	Sim	data:image/png;base64,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
\.


--
-- Data for Name: produtos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.produtos (id, nome, categoria, codigo, quantidade, unidade, preco_compra, estoque_minimo) FROM stdin;
4	cabo	Material Elétrico	PROD-0001	15	m	100	5
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuarios (id, username, password, tipo) FROM stdin;
1	admin	1234	admin
\.


--
-- Name: cotacoes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cotacoes_id_seq', 7, true);


--
-- Name: folhas_salariais_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.folhas_salariais_id_seq', 5, true);


--
-- Name: funcionarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.funcionarios_id_seq', 3, true);


--
-- Name: itens_cotacao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.itens_cotacao_id_seq', 69, true);


--
-- Name: movimentacoes_estoque_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.movimentacoes_estoque_id_seq', 6, true);


--
-- Name: produtos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.produtos_id_seq', 4, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usuarios_id_seq', 1, true);


--
-- Name: cotacoes cotacoes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotacoes
    ADD CONSTRAINT cotacoes_pkey PRIMARY KEY (id);


--
-- Name: folhas_salariais folhas_salariais_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.folhas_salariais
    ADD CONSTRAINT folhas_salariais_pkey PRIMARY KEY (id);


--
-- Name: funcionarios funcionarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.funcionarios
    ADD CONSTRAINT funcionarios_pkey PRIMARY KEY (id);


--
-- Name: itens_cotacao itens_cotacao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.itens_cotacao
    ADD CONSTRAINT itens_cotacao_pkey PRIMARY KEY (id);


--
-- Name: movimentacoes_estoque movimentacoes_estoque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimentacoes_estoque
    ADD CONSTRAINT movimentacoes_estoque_pkey PRIMARY KEY (id);


--
-- Name: produtos produtos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.produtos
    ADD CONSTRAINT produtos_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: folhas_salariais folhas_salariais_funcionario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.folhas_salariais
    ADD CONSTRAINT folhas_salariais_funcionario_id_fkey FOREIGN KEY (funcionario_id) REFERENCES public.funcionarios(id) ON DELETE CASCADE;


--
-- Name: itens_cotacao itens_cotacao_cotacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.itens_cotacao
    ADD CONSTRAINT itens_cotacao_cotacao_id_fkey FOREIGN KEY (cotacao_id) REFERENCES public.cotacoes(id) ON DELETE CASCADE;


--
-- Name: itens_cotacao itens_cotacao_produto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.itens_cotacao
    ADD CONSTRAINT itens_cotacao_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE SET NULL;


--
-- Name: movimentacoes_estoque movimentacoes_estoque_funcionario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimentacoes_estoque
    ADD CONSTRAINT movimentacoes_estoque_funcionario_id_fkey FOREIGN KEY (funcionario_id) REFERENCES public.funcionarios(id) ON DELETE SET NULL;


--
-- Name: movimentacoes_estoque movimentacoes_estoque_produto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimentacoes_estoque
    ADD CONSTRAINT movimentacoes_estoque_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ICd1v3zZaekn0eSct9f4fRmSzVqB6S8gPdtZswwSRbO73XaeFvRqDM4qM4FwcsJ

