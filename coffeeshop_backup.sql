--
-- PostgreSQL database dump
--

\restrict EpFKKZBcdDm57HjerLWwYZiPBffJgsNZmAF4Fnzeh8gbFrkLik6dfTTdG22KHdD

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

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
-- Name: budgets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.budgets (
    id integer NOT NULL,
    month character varying(7) NOT NULL,
    category text NOT NULL,
    amount numeric(12,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    subcategory text
);


ALTER TABLE public.budgets OWNER TO postgres;

--
-- Name: budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.budgets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.budgets_id_seq OWNER TO postgres;

--
-- Name: budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.budgets_id_seq OWNED BY public.budgets.id;


--
-- Name: checking_account_main; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.checking_account_main (
    date date,
    transaction_id text,
    description text,
    category text,
    type text,
    amount numeric,
    balance numeric
);


ALTER TABLE public.checking_account_main OWNER TO postgres;

--
-- Name: checking_account_secondary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.checking_account_secondary (
    date date NOT NULL,
    transaction_id integer NOT NULL,
    description text,
    category character varying(50),
    type character varying(10),
    amount numeric(12,2) NOT NULL,
    balance numeric(12,2) NOT NULL,
    CONSTRAINT checking_account_secondary_type_check CHECK (((type)::text = ANY ((ARRAY['credit'::character varying, 'debit'::character varying])::text[])))
);


ALTER TABLE public.checking_account_secondary OWNER TO postgres;

--
-- Name: checking_account_secondary_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.checking_account_secondary_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.checking_account_secondary_transaction_id_seq OWNER TO postgres;

--
-- Name: checking_account_secondary_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.checking_account_secondary_transaction_id_seq OWNED BY public.checking_account_secondary.transaction_id;


--
-- Name: company_budgets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_budgets (
    id integer NOT NULL,
    month character varying(7) NOT NULL,
    amount numeric(12,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.company_budgets OWNER TO postgres;

--
-- Name: company_budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.company_budgets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.company_budgets_id_seq OWNER TO postgres;

--
-- Name: company_budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.company_budgets_id_seq OWNED BY public.company_budgets.id;


--
-- Name: credit_card_account; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.credit_card_account (
    date date,
    transaction_id text,
    vendor text,
    category text,
    type text,
    amount numeric,
    balance numeric
);


ALTER TABLE public.credit_card_account OWNER TO postgres;

--
-- Name: monthly_balances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.monthly_balances (
    id integer NOT NULL,
    month_year date NOT NULL,
    starting_balance numeric(15,2) NOT NULL,
    ending_balance numeric(15,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.monthly_balances OWNER TO postgres;

--
-- Name: monthly_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.monthly_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.monthly_balances_id_seq OWNER TO postgres;

--
-- Name: monthly_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.monthly_balances_id_seq OWNED BY public.monthly_balances.id;


--
-- Name: overall_budgets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.overall_budgets (
    id integer NOT NULL,
    amount numeric(12,2) NOT NULL,
    description text,
    month text
);


ALTER TABLE public.overall_budgets OWNER TO postgres;

--
-- Name: overall_budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.overall_budgets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.overall_budgets_id_seq OWNER TO postgres;

--
-- Name: overall_budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.overall_budgets_id_seq OWNED BY public.overall_budgets.id;


--
-- Name: payroll_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payroll_history (
    employee_id text NOT NULL,
    employee_name text NOT NULL,
    role text,
    pay_date date NOT NULL,
    net_pay numeric(10,2) NOT NULL
);


ALTER TABLE public.payroll_history OWNER TO postgres;

--
-- Name: payroll_history_employee_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payroll_history_employee_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payroll_history_employee_id_seq OWNER TO postgres;

--
-- Name: payroll_history_employee_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payroll_history_employee_id_seq OWNED BY public.payroll_history.employee_id;


--
-- Name: budgets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets ALTER COLUMN id SET DEFAULT nextval('public.budgets_id_seq'::regclass);


--
-- Name: checking_account_secondary transaction_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.checking_account_secondary ALTER COLUMN transaction_id SET DEFAULT nextval('public.checking_account_secondary_transaction_id_seq'::regclass);


--
-- Name: company_budgets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_budgets ALTER COLUMN id SET DEFAULT nextval('public.company_budgets_id_seq'::regclass);


--
-- Name: monthly_balances id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthly_balances ALTER COLUMN id SET DEFAULT nextval('public.monthly_balances_id_seq'::regclass);


--
-- Name: overall_budgets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.overall_budgets ALTER COLUMN id SET DEFAULT nextval('public.overall_budgets_id_seq'::regclass);


--
-- Name: payroll_history employee_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_history ALTER COLUMN employee_id SET DEFAULT nextval('public.payroll_history_employee_id_seq'::regclass);


--
-- Data for Name: budgets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.budgets (id, month, category, amount, created_at, subcategory) FROM stdin;
133	2026-02	Operating expense	12.00	2026-02-08 20:16:24.991077	Local Print Shop
167	2026-02	COGS	2.00	2026-02-08 21:03:39.024871	Coffee Supplier Payment
134	2026-02	Operating expense	2.00	2026-02-08 20:18:24.058683	Rent Payment
135	2026-02	Operating expense	1.00	2026-02-08 20:20:02.883035	Miscellaneous
172	2022-01	Operating expense	45000.00	2026-02-08 21:40:00.625886	\N
173	2022-01	Operating expense	23000.00	2026-02-08 21:40:00.625886	Utilities
174	2022-01	Operating expense	4000.00	2026-02-08 21:40:00.625886	Utility Bill Payment
175	2022-01	Operating expense	3000.00	2026-02-08 21:40:00.625886	Marketing
176	2022-01	Operating expense	3000.00	2026-02-08 21:40:00.625886	Marketing / promotion
177	2022-01	Operating expense	7000.00	2026-02-08 21:41:02.63162	Rent Payment
178	2026-02	COGS	10.00	2026-02-08 21:59:31.202501	Supplies
107	2026-02	Operating expense	2000.00	2026-02-06 13:35:13.770323	\N
136	2026-02	Operating expense	1.00	2026-02-08 20:20:07.517406	Facebook Ads
137	2022-01	COGS	50000.00	2026-02-08 20:25:19.237065	\N
108	2026-02	Operating expense	23.00	2026-02-06 13:35:21.029312	Utilities
111	2026-04	COGS	50.00	2026-02-07 22:33:45.069323	\N
112	2026-04	Operating expense	50.00	2026-02-07 22:34:02.81902	\N
138	2022-01	COGS	20000.00	2026-02-08 20:25:19.237065	Bakery Payment
139	2022-01	COGS	12000.00	2026-02-08 20:25:19.237065	Supplies
140	2022-01	COGS	5000.00	2026-02-08 20:25:19.237065	Ingredients / Groceries
141	2022-01	COGS	13000.00	2026-02-08 20:25:19.237065	Packaging
105	2026-02	COGS	2000.00	2026-02-06 13:30:20.905117	\N
180	2026-02	COGS	1.00	2026-02-17 22:39:16.540623	Ingredients / Groceries
181	2026-02	COGS	1.00	2026-02-17 22:39:21.726279	Packaging
182	2026-02	COGS	1.00	2026-02-17 22:39:28.219988	Bakery Payment
183	2025-08	COGS	2500.00	2026-02-17 22:42:32.276478	Bakery Payment
184	2025-08	COGS	1800.00	2026-02-17 22:42:32.276478	Coffee Supplier Payment
185	2025-08	COGS	900.00	2026-02-17 22:42:32.276478	Supplies
186	2025-08	COGS	700.00	2026-02-17 22:42:32.276478	Ingredients / Groceries
187	2025-08	COGS	450.00	2026-02-17 22:42:32.276478	Packaging
188	2025-08	Operating expense	600.00	2026-02-17 22:42:32.276478	Utilities
189	2025-08	Operating expense	350.00	2026-02-17 22:42:32.276478	Marketing
190	2025-08	Operating expense	1200.00	2026-02-17 22:42:32.276478	Rent Payment
191	2025-08	Operating expense	300.00	2026-02-17 22:42:32.276478	Staff meal
192	2025-08	Operating expense	400.00	2026-02-17 22:42:32.276478	Facebook Ads
193	2025-08	Operating expense	250.00	2026-02-17 22:42:32.276478	Miscellaneous
194	2025-09	COGS	2600.00	2026-02-17 22:46:38.575443	Bakery Payment
195	2025-09	COGS	1900.00	2026-02-17 22:46:38.575443	Coffee Supplier Payment
196	2025-09	COGS	950.00	2026-02-17 22:46:38.575443	Supplies
197	2025-09	COGS	720.00	2026-02-17 22:46:38.575443	Ingredients / Groceries
198	2025-09	COGS	480.00	2026-02-17 22:46:38.575443	Packaging
199	2025-09	Operating expense	620.00	2026-02-17 22:46:38.575443	Utilities
200	2025-09	Operating expense	420.00	2026-02-17 22:46:38.575443	Marketing
201	2025-09	Operating expense	1200.00	2026-02-17 22:46:38.575443	Rent Payment
202	2025-09	Operating expense	330.00	2026-02-17 22:46:38.575443	Staff meal
203	2025-09	Operating expense	400.00	2026-02-17 22:46:38.575443	Facebook Ads
204	2025-09	Operating expense	200.00	2026-02-17 22:46:38.575443	Miscellaneous
205	2025-10	COGS	2400.00	2026-02-17 22:46:46.894838	Bakery Payment
206	2025-10	COGS	1750.00	2026-02-17 22:46:46.894838	Coffee Supplier Payment
207	2025-10	COGS	880.00	2026-02-17 22:46:46.894838	Supplies
208	2025-10	COGS	690.00	2026-02-17 22:46:46.894838	Ingredients / Groceries
209	2025-10	COGS	430.00	2026-02-17 22:46:46.894838	Packaging
210	2025-10	Operating expense	610.00	2026-02-17 22:46:46.894838	Utilities
211	2025-10	Operating expense	350.00	2026-02-17 22:46:46.894838	Marketing / promotion
212	2025-10	Operating expense	1200.00	2026-02-17 22:46:46.894838	Rent Payment
213	2025-10	Operating expense	310.00	2026-02-17 22:46:46.894838	Staff meal
214	2025-10	Operating expense	420.00	2026-02-17 22:46:46.894838	Facebook Ads
215	2025-10	Operating expense	200.00	2026-02-17 22:46:46.894838	Miscellaneous
216	2025-11	COGS	2700.00	2026-02-17 22:46:55.797145	Bakery Payment
217	2025-11	COGS	1950.00	2026-02-17 22:46:55.797145	Coffee Supplier Payment
218	2025-11	COGS	990.00	2026-02-17 22:46:55.797145	Supplies
219	2025-11	COGS	760.00	2026-02-17 22:46:55.797145	Ingredients / Groceries
220	2025-11	COGS	500.00	2026-02-17 22:46:55.797145	Packaging
221	2025-11	Operating expense	650.00	2026-02-17 22:46:55.797145	Utilities
222	2025-11	Operating expense	450.00	2026-02-17 22:46:55.797145	Marketing
223	2025-11	Operating expense	1200.00	2026-02-17 22:46:55.797145	Rent Payment
224	2025-11	Operating expense	340.00	2026-02-17 22:46:55.797145	Staff meal
225	2025-11	Operating expense	260.00	2026-02-17 22:46:55.797145	Equipment purchase
226	2025-11	Operating expense	100.00	2026-02-17 22:46:55.797145	Miscellaneous
227	2025-12	COGS	2500.00	2026-02-17 22:47:14.270544	Bakery Payment
228	2025-12	COGS	1850.00	2026-02-17 22:47:14.270544	Coffee Supplier Payment
229	2025-12	COGS	900.00	2026-02-17 22:47:14.270544	Supplies
230	2025-12	COGS	720.00	2026-02-17 22:47:14.270544	Ingredients / Groceries
231	2025-12	COGS	460.00	2026-02-17 22:47:14.270544	Packaging
232	2025-12	Operating expense	600.00	2026-02-17 22:47:14.270544	Utilities
233	2025-12	Operating expense	400.00	2026-02-17 22:47:14.270544	Marketing / promotion
234	2025-12	Operating expense	1200.00	2026-02-17 22:47:14.270544	Rent Payment
235	2025-12	Operating expense	350.00	2026-02-17 22:47:14.270544	Staff meal
236	2025-12	Operating expense	320.00	2026-02-17 22:47:14.270544	Taxes / licenses / bank fees
247	2025-08	COGS	3000.00	2026-02-18 17:24:32.439934	\N
248	2025-08	Operating expense	3000.00	2026-02-18 17:24:32.439934	\N
249	2025-09	COGS	3000.00	2026-02-18 17:24:32.439934	\N
250	2025-09	Operating expense	3000.00	2026-02-18 17:24:32.439934	\N
251	2025-10	COGS	3000.00	2026-02-18 17:24:32.439934	\N
252	2025-10	Operating expense	3000.00	2026-02-18 17:24:32.439934	\N
253	2025-11	COGS	3000.00	2026-02-18 17:24:32.439934	\N
254	2025-11	Operating expense	3000.00	2026-02-18 17:24:32.439934	\N
255	2025-12	COGS	3000.00	2026-02-18 17:24:32.439934	\N
256	2025-12	Operating expense	3000.00	2026-02-18 17:24:32.439934	\N
257	2026-01	COGS	2000.00	2026-02-18 17:27:21.738583	Bakery Payment
258	2026-01	COGS	1000.00	2026-02-18 17:27:21.738583	Coffee Supplier Payment
259	2026-01	COGS	920.00	2026-02-18 17:27:21.738583	Supplies
260	2026-01	COGS	730.00	2026-02-18 17:27:21.738583	Ingredients / Groceries
261	2026-01	COGS	480.00	2026-02-18 17:27:21.738583	Packaging
262	2026-01	Operating expense	610.00	2026-02-18 17:27:21.738583	Utilities
263	2026-01	Operating expense	390.00	2026-02-18 17:27:21.738583	Marketing / promotion
264	2026-01	Operating expense	1200.00	2026-02-18 17:27:21.738583	Rent Payment
265	2026-01	Operating expense	320.00	2026-02-18 17:27:21.738583	Staff meal
266	2026-01	Operating expense	350.00	2026-02-18 17:27:21.738583	Facebook Ads
267	2026-01	Operating expense	280.00	2026-02-18 17:27:21.738583	Miscellaneous
268	2026-01	COGS	3000.00	2026-02-18 17:28:32.421319	\N
269	2026-01	Operating expense	3000.00	2026-02-18 17:28:32.421319	\N
\.


--
-- Data for Name: checking_account_main; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.checking_account_main (date, transaction_id, description, category, type, amount, balance) FROM stdin;
2025-12-26	\N	Daily Sales Deposit	Sales Revenue	\N	603	\N
2025-12-27	\N	Daily Sales Deposit	Sales Revenue	\N	688	\N
2025-12-28	\N	Daily Sales Deposit	Sales Revenue	\N	756	\N
2025-12-29	\N	Daily Sales Deposit	Sales Revenue	\N	409	\N
2025-12-30	\N	Daily Sales Deposit	Sales Revenue	\N	499	\N
2025-12-30	\N	Coffee Supplier Payment	COGS	\N	322	\N
2025-08-01	TX00041	Daily Sales Deposit	Sales Revenue	Credit	907	41885
2025-08-02	TX00042	Daily Sales Deposit	Sales Revenue	Credit	1066	42951
2025-08-03	TX00043	Daily Sales Deposit	Sales Revenue	Credit	1109	44060
2025-08-04	TX00044	Daily Sales Deposit	Sales Revenue	Credit	887	44947
2025-08-05	TX00045	Daily Sales Deposit	Sales Revenue	Credit	740	45687
2025-08-06	TX00046	Daily Sales Deposit	Sales Revenue	Credit	1000	46687
2025-08-06	TX00047	Bakery Payment	COGS	Debit	426	46261
2025-08-07	TX00048	Daily Sales Deposit	Sales Revenue	Credit	1043	47304
2025-08-08	TX00049	Daily Sales Deposit	Sales Revenue	Credit	835	48139
2025-08-08	TX00050	Utility Bill Payment	Operating Expense	Debit	238	47901
2025-08-09	TX00051	Daily Sales Deposit	Sales Revenue	Credit	780	48681
2025-08-10	TX00052	Daily Sales Deposit	Sales Revenue	Credit	1118	49799
2025-08-11	TX00053	Daily Sales Deposit	Sales Revenue	Credit	960	50759
2025-08-12	TX00054	Daily Sales Deposit	Sales Revenue	Credit	740	51499
2025-08-13	TX00055	Daily Sales Deposit	Sales Revenue	Credit	900	52399
2025-08-14	TX00056	Daily Sales Deposit	Sales Revenue	Credit	1117	53516
2025-08-14	TX00057	Maintenance Payment	Operating Expense	Debit	161	53355
2025-08-15	TX00058	Daily Sales Deposit	Sales Revenue	Credit	798	54153
2025-08-16	TX00059	Daily Sales Deposit	Sales Revenue	Credit	913	55066
2025-08-17	TX00060	Daily Sales Deposit	Sales Revenue	Credit	1148	56214
2025-08-18	TX00061	Daily Sales Deposit	Sales Revenue	Credit	1130	57344
2025-08-19	TX00062	Daily Sales Deposit	Sales Revenue	Credit	956	58300
2025-08-20	TX00063	Daily Sales Deposit	Sales Revenue	Credit	954	59254
2025-12-01	\N	Daily Sales Deposit	Sales Revenue	\N	585	\N
2025-12-02	\N	Daily Sales Deposit	Sales Revenue	\N	524	\N
2025-12-03	\N	Daily Sales Deposit	Sales Revenue	\N	457	\N
2025-12-03	\N	Coffee Supplier Payment	COGS	\N	279	\N
2025-12-04	\N	Daily Sales Deposit	Sales Revenue	\N	725	\N
2025-12-05	\N	Daily Sales Deposit	Sales Revenue	\N	500	\N
2025-12-06	\N	Daily Sales Deposit	Sales Revenue	\N	452	\N
2025-12-07	\N	Daily Sales Deposit	Sales Revenue	\N	507	\N
2025-12-08	\N	Daily Sales Deposit	Sales Revenue	\N	595	\N
2025-12-09	\N	Daily Sales Deposit	Sales Revenue	\N	771	\N
2025-12-10	\N	Daily Sales Deposit	Sales Revenue	\N	754	\N
2025-12-11	\N	Daily Sales Deposit	Sales Revenue	\N	707	\N
2025-12-12	\N	Daily Sales Deposit	Sales Revenue	\N	505	\N
2025-12-13	\N	Daily Sales Deposit	Sales Revenue	\N	544	\N
2025-12-14	\N	Daily Sales Deposit	Sales Revenue	\N	674	\N
2025-12-15	\N	Daily Sales Deposit	Sales Revenue	\N	745	\N
2025-12-15	\N	Bakery Payment	COGS	\N	216	\N
2025-12-16	\N	Daily Sales Deposit	Sales Revenue	\N	795	\N
2025-12-17	\N	Daily Sales Deposit	Sales Revenue	\N	457	\N
2025-12-18	\N	Daily Sales Deposit	Sales Revenue	\N	638	\N
2025-12-19	\N	Daily Sales Deposit	Sales Revenue	\N	525	\N
2025-12-19	\N	Maintenance Payment	Operating Expense	\N	188	\N
2025-12-20	\N	Daily Sales Deposit	Sales Revenue	\N	772	\N
2025-12-21	\N	Daily Sales Deposit	Sales Revenue	\N	588	\N
2025-12-22	\N	Daily Sales Deposit	Sales Revenue	\N	468	\N
2025-12-23	\N	Daily Sales Deposit	Sales Revenue	\N	646	\N
2025-12-23	\N	Utility Bill Payment	Operating Expense	\N	253	\N
2025-12-24	\N	Daily Sales Deposit	Sales Revenue	\N	485	\N
2025-12-24	\N	Maintenance Payment	Operating Expense	\N	319	\N
2025-12-25	\N	Daily Sales Deposit	Sales Revenue	\N	446	\N
2025-08-21	TX00064	Daily Sales Deposit	Sales Revenue	Credit	982	60236
2025-08-22	TX00065	Daily Sales Deposit	Sales Revenue	Credit	714	60950
2025-08-22	TX00066	Maintenance Payment	Operating Expense	Debit	479	60471
2025-08-23	TX00067	Daily Sales Deposit	Sales Revenue	Credit	878	61349
2025-08-23	TX00068	Bakery Payment	COGS	Debit	330	61019
2025-08-24	TX00069	Daily Sales Deposit	Sales Revenue	Credit	751	61770
2025-08-25	TX00070	Daily Sales Deposit	Sales Revenue	Credit	1087	62857
2025-08-26	TX00071	Daily Sales Deposit	Sales Revenue	Credit	1106	63963
2025-08-27	TX00072	Daily Sales Deposit	Sales Revenue	Credit	842	64805
2025-09-02	TX00075	Daily Sales Deposit	Sales Revenue	Credit	485	66751
2025-09-03	TX00076	Daily Sales Deposit	Sales Revenue	Credit	569	67320
2025-09-04	TX00077	Daily Sales Deposit	Sales Revenue	Credit	533	67853
2025-09-05	TX00078	Daily Sales Deposit	Sales Revenue	Credit	507	68360
2025-09-05	TX00079	Utility Bill Payment	Operating Expense	Debit	385	67975
2025-09-06	TX00080	Daily Sales Deposit	Sales Revenue	Credit	527	68502
2025-09-07	TX00081	Daily Sales Deposit	Sales Revenue	Credit	747	69249
2025-09-08	TX00082	Daily Sales Deposit	Sales Revenue	Credit	589	69838
2025-09-08	TX00083	Utility Bill Payment	Operating Expense	Debit	476	69362
2025-09-09	TX00084	Daily Sales Deposit	Sales Revenue	Credit	520	69882
2025-09-10	TX00085	Daily Sales Deposit	Sales Revenue	Credit	632	70514
2025-09-11	TX00086	Daily Sales Deposit	Sales Revenue	Credit	597	71111
2025-09-12	TX00087	Daily Sales Deposit	Sales Revenue	Credit	536	71647
2025-09-13	TX00088	Daily Sales Deposit	Sales Revenue	Credit	624	72271
2025-09-13	TX00089	Utility Bill Payment	Operating Expense	Debit	271	72000
2025-09-14	TX00090	Daily Sales Deposit	Sales Revenue	Credit	773	72773
2025-09-15	TX00091	Daily Sales Deposit	Sales Revenue	Credit	632	73405
2025-09-16	TX00092	Daily Sales Deposit	Sales Revenue	Credit	717	74122
2025-09-17	TX00093	Daily Sales Deposit	Sales Revenue	Credit	451	74573
2025-09-18	TX00094	Daily Sales Deposit	Sales Revenue	Credit	694	75267
2025-11-25	\N	Rent Payment	Operating Expense	\N	337	\N
2025-09-19	TX00095	Daily Sales Deposit	Sales Revenue	Credit	512	75779
2025-09-19	TX00096	Utility Bill Payment	Operating Expense	Debit	180	75599
2025-09-20	TX00097	Daily Sales Deposit	Sales Revenue	Credit	512	76111
2025-09-21	TX00098	Daily Sales Deposit	Sales Revenue	Credit	619	76730
2025-09-21	TX00099	Bakery Payment	COGS	Debit	323	76407
2025-09-22	TX00100	Daily Sales Deposit	Sales Revenue	Credit	784	77191
2025-09-25	TX00103	Daily Sales Deposit	Sales Revenue	Credit	646	78983
2025-09-26	TX00104	Daily Sales Deposit	Sales Revenue	Credit	602	79585
2025-09-27	TX00105	Daily Sales Deposit	Sales Revenue	Credit	654	80239
2025-09-28	TX00106	Daily Sales Deposit	Sales Revenue	Credit	724	80963
2025-09-29	TX00107	Daily Sales Deposit	Sales Revenue	Credit	597	81560
2025-09-30	TX00108	Daily Sales Deposit	Sales Revenue	Credit	639	82199
2025-09-30	TX00109	Daily Sales Deposit	Sales Revenue	Credit	600	82799
2025-10-01	TX00110	Daily Sales Deposit	Sales Revenue	Credit	725	83524
2025-10-02	TX00111	Daily Sales Deposit	Sales Revenue	Credit	658	84182
2025-10-03	TX00112	Daily Sales Deposit	Sales Revenue	Credit	745	84927
2025-10-04	TX00113	Daily Sales Deposit	Sales Revenue	Credit	546	85473
2025-10-05	TX00114	Daily Sales Deposit	Sales Revenue	Credit	598	86071
2025-10-05	TX00115	Coffee Supplier Payment	COGS	Debit	227	85844
2025-10-06	TX00116	Daily Sales Deposit	Sales Revenue	Credit	759	86603
2025-10-06	TX00117	Coffee Supplier Payment	COGS	Debit	250	86353
2025-10-07	TX00118	Daily Sales Deposit	Sales Revenue	Credit	498	86851
2025-10-08	TX00119	Daily Sales Deposit	Sales Revenue	Credit	543	87394
2025-10-09	TX00120	Daily Sales Deposit	Sales Revenue	Credit	459	87853
2025-10-10	TX00121	Daily Sales Deposit	Sales Revenue	Credit	784	88637
2025-10-10	TX00122	Maintenance Payment	Operating Expense	Debit	239	88398
2025-10-11	TX00123	Daily Sales Deposit	Sales Revenue	Credit	436	88834
2025-10-12	TX00124	Daily Sales Deposit	Sales Revenue	Credit	408	89242
2025-10-13	TX00125	Daily Sales Deposit	Sales Revenue	Credit	546	89788
2025-10-14	TX00126	Daily Sales Deposit	Sales Revenue	Credit	530	90318
2025-10-15	TX00127	Daily Sales Deposit	Sales Revenue	Credit	453	90771
2025-10-16	TX00128	Daily Sales Deposit	Sales Revenue	Credit	515	91286
2025-10-17	TX00130	Daily Sales Deposit	Sales Revenue	Credit	653	91736
2025-10-17	TX00131	Bakery Payment	COGS	Debit	198	91538
2025-10-18	TX00132	Daily Sales Deposit	Sales Revenue	Credit	748	92286
2025-10-19	TX00133	Daily Sales Deposit	Sales Revenue	Credit	765	93051
2025-10-20	TX00134	Daily Sales Deposit	Sales Revenue	Credit	709	93760
2025-10-21	TX00135	Daily Sales Deposit	Sales Revenue	Credit	568	94328
2025-10-21	TX00136	Bakery Payment	COGS	Debit	167	94161
2025-10-22	TX00137	Daily Sales Deposit	Sales Revenue	Credit	797	94958
2025-10-23	TX00138	Daily Sales Deposit	Sales Revenue	Credit	783	95741
2025-10-24	TX00139	Daily Sales Deposit	Sales Revenue	Credit	594	96335
2025-10-25	TX00140	Daily Sales Deposit	Sales Revenue	Credit	432	96767
2025-10-26	TX00141	Daily Sales Deposit	Sales Revenue	Credit	770	97537
2025-10-27	TX00142	Daily Sales Deposit	Sales Revenue	Credit	421	97958
2025-10-28	TX00143	Daily Sales Deposit	Sales Revenue	Credit	437	98395
2025-10-29	TX00144	Daily Sales Deposit	Sales Revenue	Credit	450	98845
2025-10-30	TX00145	Daily Sales Deposit	Sales Revenue	Credit	682	99527
2025-11-01	TX00146	Daily Sales Deposit	Sales Revenue	Credit	676	100203
2025-11-02	TX00147	Daily Sales Deposit	Sales Revenue	Credit	683	100886
2025-11-03	TX00148	Daily Sales Deposit	Sales Revenue	Credit	716	101602
2025-11-04	TX00149	Daily Sales Deposit	Sales Revenue	Credit	403	102005
2025-11-04	TX00150	Bakery Payment	COGS	Debit	148	101857
2025-11-05	TX00151	Daily Sales Deposit	Sales Revenue	Credit	571	102428
2025-11-06	TX00152	Daily Sales Deposit	Sales Revenue	Credit	445	102873
2025-11-07	TX00153	Daily Sales Deposit	Sales Revenue	Credit	498	103371
2025-11-08	TX00154	Daily Sales Deposit	Sales Revenue	Credit	436	103807
2025-09-23	TX00101	Daily Sales Deposit	Sales Revenue	Credit	529	77720
2025-09-24	TX00102	Daily Sales Deposit	Sales Revenue	Credit	617	78337
2025-08-28	TX00073	Daily Sales Deposit	Sales Revenue	Credit	735	65540
2025-09-01	TX00074	Daily Sales Deposit	Sales Revenue	Credit	726	66266
2025-11-09	TX00155	Daily Sales Deposit	Sales Revenue	Credit	701	104508
2025-11-10	TX00156	Daily Sales Deposit	Sales Revenue	Credit	498	105006
2025-11-11	TX00157	Daily Sales Deposit	Sales Revenue	Credit	515	105521
2025-11-12	TX00158	Daily Sales Deposit	Sales Revenue	Credit	560	106081
2025-11-13	TX00159	Daily Sales Deposit	Sales Revenue	Credit	527	106608
2025-11-14	TX00160	Daily Sales Deposit	Sales Revenue	Credit	622	107230
2025-11-15	TX00161	Daily Sales Deposit	Sales Revenue	Credit	722	107952
2025-11-16	TX00162	Daily Sales Deposit	Sales Revenue	Credit	679	108631
2025-11-17	TX00163	Daily Sales Deposit	Sales Revenue	Credit	741	109372
2025-11-18	TX00164	Daily Sales Deposit	Sales Revenue	Credit	526	109898
2025-11-19	TX00165	Daily Sales Deposit	Sales Revenue	Credit	785	110683
2025-11-20	TX00166	Daily Sales Deposit	Sales Revenue	Credit	503	111186
2025-11-21	TX00167	Daily Sales Deposit	Sales Revenue	Credit	698	111884
2025-11-22	TX00168	Daily Sales Deposit	Sales Revenue	Credit	438	112322
2025-11-23	TX00169	Daily Sales Deposit	Sales Revenue	Credit	646	112968
2025-11-24	TX00170	Daily Sales Deposit	Sales Revenue	Credit	705	113673
2025-11-25	TX00171	Daily Sales Deposit	Sales Revenue	Credit	412	114085
2025-11-25	TX00172	Bakery Payment	COGS	Debit	490	113595
2025-11-26	TX00173	Daily Sales Deposit	Sales Revenue	Credit	435	114030
2025-11-27	TX00174	Daily Sales Deposit	Sales Revenue	Credit	720	114750
2025-11-28	TX00176	Daily Sales Deposit	Sales Revenue	Credit	770	115021
2025-11-29	TX00177	Daily Sales Deposit	Sales Revenue	Credit	491	115512
2025-11-30	TX00178	Daily Sales Deposit	Sales Revenue	Credit	687	116199
2025-11-30	TX00179	Daily Sales Deposit	Sales Revenue	Credit	741	116940
2025-12-26	\N	Rent Payment	Operating Expense	\N	440	\N
2025-10-11	\N	Rent Payment	Operating Expense	\N	469	\N
2025-08-16	TX00129	Rent Payment	Operating Expense	Debit	203	91083
2025-09-27	TX00175	Rent Payment	Operating Expense	Debit	499	114251
2026-02-21	TX-4685A9F8	Bakery Payment	COGS	Debit	100.0	0
2026-02-21	TX-815DC02F	Bakery Payment	COGS	Debit	100.0	0
2026-02-28	TX-92F511A3	Bakery Payment	COGS	Debit	100.0	0
\.


--
-- Data for Name: checking_account_secondary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.checking_account_secondary (date, transaction_id, description, category, type, amount, balance) FROM stdin;
\.


--
-- Data for Name: company_budgets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.company_budgets (id, month, amount, created_at) FROM stdin;
1	2026-02	200.00	2026-02-03 21:22:14.346334
\.


--
-- Data for Name: credit_card_account; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.credit_card_account (date, transaction_id, vendor, category, type, amount, balance) FROM stdin;
2025-12-04	\N	Coffee Supplier	Marketing	\N	107	\N
2025-12-11	\N	Facebook Ads	Utilities	\N	457	\N
2025-12-18	\N	Utility Company	Supplies	\N	410	\N
2025-12-25	\N	Coffee Supplier	Supplies	\N	513	\N
2025-08-05	CC00008	Coffee Supplier	Marketing	Debit	179	1331
2025-08-12	CC00009	Facebook Ads	Marketing	Debit	449	1780
2025-08-19	CC00010	Utility Company	Other	Debit	363	2143
2025-08-26	CC00011	Coffee Supplier	Other	Debit	163	2306
2025-09-05	CC00012	Facebook Ads	Utilities	Debit	206	2512
2025-09-12	CC00013	Facebook Ads	Marketing	Debit	264	2776
2025-09-19	CC00014	Local Print Shop	Utilities	Debit	411	3187
2025-09-26	CC00015	Utility Company	Marketing	Debit	207	3394
2025-10-02	CC00017	Facebook Ads	Utilities	Debit	229	3090
2025-10-09	CC00019	Facebook Ads	Utilities	Debit	384	2993
2025-10-16	CC00021	Utility Company	Marketing	Debit	344	2653
2025-10-23	CC00023	Coffee Supplier	Other	Debit	111	2359
2025-10-30	CC00024	Utility Company	Utilities	Debit	315	2674
2025-11-07	CC00026	Facebook Ads	Marketing	Debit	405	2663
2025-11-14	CC00027	Utility Company	Utilities	Debit	283	2946
2025-11-21	CC00028	Coffee Supplier	Other	Debit	527	3473
2025-11-28	CC00030	Coffee Supplier	Supplies	Debit	435	3401
\.


--
-- Data for Name: monthly_balances; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.monthly_balances (id, month_year, starting_balance, ending_balance, created_at) FROM stdin;
20	2025-08-01	10000.00	32045.00	2026-02-21 13:12:49.044881
25	2025-10-01	46557.00	60476.00	2026-02-21 13:13:32.751378
26	2025-11-01	60476.00	75241.00	2026-02-21 13:13:42.161156
27	2025-12-01	75241.00	88397.00	2026-02-21 13:13:53.515671
23	2025-09-01	32045.00	46557.00	2026-02-21 13:13:20.495224
\.


--
-- Data for Name: overall_budgets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.overall_budgets (id, amount, description, month) FROM stdin;
57	100000.00	First month	2022-01
62	3244.70	Budget	2026-12
63	10000.00	August budget	2025-08
64	14000.00	September budget	2025-09
65	15000.00	October budget	2025-10
66	15000.00	November budget	2025-11
68	30000.00	December adjustment	2025-12
69	30000.00	December adjustment	2026-01
53	8080.00	\N	2026-02
\.


--
-- Data for Name: payroll_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payroll_history (employee_id, employee_name, role, pay_date, net_pay) FROM stdin;
E001	Arthur Morgan	Manager	2025-08-31	300.00
E001	Arthur Morgan	Manager	2025-09-30	300.00
E001	Arthur Morgan	Manager	2025-10-31	300.00
E001	Arthur Morgan	Manager	2025-11-30	300.00
E001	Arthur Morgan	Manager	2025-12-31	300.00
E002	Elena Fisher	Cashier	2025-08-31	180.00
E002	Elena Fisher	Cashier	2025-09-30	180.00
E002	Elena Fisher	Cashier	2025-10-31	180.00
E002	Elena Fisher	Cashier	2025-11-30	180.00
E002	Elena Fisher	Cashier	2025-12-31	180.00
E003	Victor Sullivan	Barista	2025-08-31	160.00
E003	Victor Sullivan	Barista	2025-09-30	160.00
E003	Victor Sullivan	Barista	2025-10-31	160.00
E003	Victor Sullivan	Barista	2025-11-30	160.00
E003	Victor Sullivan	Barista	2025-12-31	160.00
E004	Chloe Frazer	Barista	2025-08-31	160.00
E004	Chloe Frazer	Barista	2025-09-30	160.00
E004	Chloe Frazer	Barista	2025-10-31	160.00
E004	Chloe Frazer	Barista	2025-11-30	160.00
E004	Chloe Frazer	Barista	2025-12-31	160.00
E005	Leon Kennedy	Waiter	2025-08-31	120.00
E005	Leon Kennedy	Waiter	2025-09-30	120.00
E005	Leon Kennedy	Waiter	2025-10-31	120.00
E005	Leon Kennedy	Waiter	2025-11-30	120.00
E005	Leon Kennedy	Waiter	2025-12-31	120.00
E006	Claire Redfield	Waiter	2025-08-31	120.00
E006	Claire Redfield	Waiter	2025-09-30	120.00
E006	Claire Redfield	Waiter	2025-10-31	120.00
E006	Claire Redfield	Waiter	2025-11-30	120.00
E006	Claire Redfield	Waiter	2025-12-31	120.00
E007	Jill Valentine	Waiter	2025-08-31	120.00
E007	Jill Valentine	Waiter	2025-09-30	120.00
E007	Jill Valentine	Waiter	2025-10-31	120.00
E007	Jill Valentine	Waiter	2025-11-30	120.00
E007	Jill Valentine	Waiter	2025-12-31	120.00
\.


--
-- Name: budgets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.budgets_id_seq', 269, true);


--
-- Name: checking_account_secondary_transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.checking_account_secondary_transaction_id_seq', 1, false);


--
-- Name: company_budgets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.company_budgets_id_seq', 11, true);


--
-- Name: monthly_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.monthly_balances_id_seq', 76, true);


--
-- Name: overall_budgets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.overall_budgets_id_seq', 69, true);


--
-- Name: payroll_history_employee_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payroll_history_employee_id_seq', 1, false);


--
-- Name: budgets budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT budgets_pkey PRIMARY KEY (id);


--
-- Name: checking_account_secondary checking_account_secondary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.checking_account_secondary
    ADD CONSTRAINT checking_account_secondary_pkey PRIMARY KEY (transaction_id);


--
-- Name: company_budgets company_budgets_month_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_budgets
    ADD CONSTRAINT company_budgets_month_key UNIQUE (month);


--
-- Name: company_budgets company_budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_budgets
    ADD CONSTRAINT company_budgets_pkey PRIMARY KEY (id);


--
-- Name: monthly_balances monthly_balances_month_year_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthly_balances
    ADD CONSTRAINT monthly_balances_month_year_key UNIQUE (month_year);


--
-- Name: monthly_balances monthly_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monthly_balances
    ADD CONSTRAINT monthly_balances_pkey PRIMARY KEY (id);


--
-- Name: overall_budgets overall_budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.overall_budgets
    ADD CONSTRAINT overall_budgets_pkey PRIMARY KEY (id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: TABLE budgets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.budgets TO PUBLIC;


--
-- Name: SEQUENCE budgets_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.budgets_id_seq TO PUBLIC;


--
-- Name: TABLE checking_account_main; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.checking_account_main TO PUBLIC;


--
-- Name: TABLE checking_account_secondary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.checking_account_secondary TO PUBLIC;


--
-- Name: SEQUENCE checking_account_secondary_transaction_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.checking_account_secondary_transaction_id_seq TO PUBLIC;


--
-- Name: TABLE company_budgets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.company_budgets TO PUBLIC;


--
-- Name: SEQUENCE company_budgets_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.company_budgets_id_seq TO PUBLIC;


--
-- Name: TABLE credit_card_account; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.credit_card_account TO PUBLIC;


--
-- Name: TABLE monthly_balances; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.monthly_balances TO PUBLIC;


--
-- Name: SEQUENCE monthly_balances_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.monthly_balances_id_seq TO PUBLIC;


--
-- Name: TABLE overall_budgets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.overall_budgets TO PUBLIC;


--
-- Name: SEQUENCE overall_budgets_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.overall_budgets_id_seq TO PUBLIC;


--
-- Name: TABLE payroll_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.payroll_history TO PUBLIC;


--
-- Name: SEQUENCE payroll_history_employee_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.payroll_history_employee_id_seq TO PUBLIC;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict EpFKKZBcdDm57HjerLWwYZiPBffJgsNZmAF4Fnzeh8gbFrkLik6dfTTdG22KHdD

