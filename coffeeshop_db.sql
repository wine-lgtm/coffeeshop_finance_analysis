--
-- PostgreSQL database dump
--

\restrict HoANtjMOgtrffpF2SkIIupde5acdbTuhm5hDhWkeh2eH6todWHp0ZxpjlGeW3ei

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
    date date,
    transaction_id text,
    description text,
    category text,
    type text,
    amount numeric,
    balance numeric
);


ALTER TABLE public.checking_account_secondary OWNER TO postgres;

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
-- Name: employee_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee_profiles (
    id integer NOT NULL,
    name text,
    role text,
    hourly_rate numeric,
    is_active boolean DEFAULT true,
    is_seasonal boolean DEFAULT false
);


ALTER TABLE public.employee_profiles OWNER TO postgres;

--
-- Name: payroll_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payroll_history (
    employee_id integer,
    employee_name text,
    role text,
    pay_date date,
    gross_pay numeric,
    federal_tax numeric,
    provincial_tax numeric,
    cpp numeric,
    ei numeric,
    other_deductions numeric,
    net_pay numeric,
    employer_cpp numeric,
    employer_ei numeric,
    tips numeric,
    travel_reimbursement numeric,
    total_business_cost numeric
);


ALTER TABLE public.payroll_history OWNER TO postgres;

--
-- Name: payroll_ledger; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.payroll_ledger AS
 SELECT p.pay_date,
    e.name,
    e.role,
    p.gross_pay,
    p.net_pay,
    p.total_business_cost,
    p.tips,
    p.federal_tax,
    p.provincial_tax,
    p.cpp,
    p.employer_cpp,
    p.ei,
    p.employer_ei
   FROM (public.payroll_history p
     JOIN public.employee_profiles e ON ((p.employee_id = e.id)));


ALTER VIEW public.payroll_ledger OWNER TO postgres;

--
-- Name: payroll_system_ledger; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.payroll_system_ledger AS
 SELECT employee_name AS name,
    role,
    count(*) AS total_paychecks_issued,
    sum(gross_pay) AS total_gross_life,
    sum(((((gross_pay + employer_cpp) + employer_ei) + tips) + travel_reimbursement)) AS total_cash_spent_by_business,
    sum(tips) AS total_tips_distributed
   FROM public.payroll_history
  GROUP BY employee_name, role;


ALTER VIEW public.payroll_system_ledger OWNER TO postgres;

--
-- Data for Name: checking_account_main; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.checking_account_main (date, transaction_id, description, category, type, amount, balance) FROM stdin;
2022-01-01	TX00001	Daily Sales Deposit	Sales Revenue	Credit	802	15802
2022-01-02	TX00002	Daily Sales Deposit	Sales Revenue	Credit	970	16772
2022-01-03	TX00003	Daily Sales Deposit	Sales Revenue	Credit	888	17660
2022-01-04	TX00004	Daily Sales Deposit	Sales Revenue	Credit	821	18481
2022-01-04	TX00005	Utility Bill Payment	Operating Expense	Debit	430	18051
2022-01-05	TX00006	Daily Sales Deposit	Sales Revenue	Credit	787	18838
2022-01-06	TX00007	Daily Sales Deposit	Sales Revenue	Credit	1059	19897
2022-01-07	TX00008	Daily Sales Deposit	Sales Revenue	Credit	849	20746
2022-01-07	TX00009	Rent Payment	Operating Expense	Debit	443	20303
2022-01-08	TX00010	Daily Sales Deposit	Sales Revenue	Credit	1113	21416
2022-01-09	TX00011	Daily Sales Deposit	Sales Revenue	Credit	891	22307
2022-01-10	TX00012	Daily Sales Deposit	Sales Revenue	Credit	860	23167
2022-01-11	TX00013	Daily Sales Deposit	Sales Revenue	Credit	721	23888
2022-01-11	TX00014	Bakery Payment	COGS	Debit	444	23444
2022-01-12	TX00015	Daily Sales Deposit	Sales Revenue	Credit	1174	24618
2022-01-13	TX00016	Daily Sales Deposit	Sales Revenue	Credit	869	25487
2022-01-13	TX00017	Utility Bill Payment	Operating Expense	Debit	287	25200
2022-01-14	TX00018	Daily Sales Deposit	Sales Revenue	Credit	1063	26263
2022-01-15	TX00019	Daily Sales Deposit	Sales Revenue	Credit	1019	27282
2022-01-16	TX00020	Daily Sales Deposit	Sales Revenue	Credit	1184	28466
2022-01-17	TX00021	Daily Sales Deposit	Sales Revenue	Credit	720	29186
2022-01-18	TX00022	Daily Sales Deposit	Sales Revenue	Credit	973	30159
2022-01-19	TX00023	Daily Sales Deposit	Sales Revenue	Credit	1015	31174
2022-01-20	TX00024	Daily Sales Deposit	Sales Revenue	Credit	964	32138
2022-01-20	TX00025	Rent Payment	Operating Expense	Debit	485	31653
2022-01-21	TX00026	Daily Sales Deposit	Sales Revenue	Credit	791	32444
2022-01-22	TX00027	Daily Sales Deposit	Sales Revenue	Credit	1154	33598
2022-01-23	TX00028	Daily Sales Deposit	Sales Revenue	Credit	963	34561
2022-01-23	TX00029	Bakery Payment	COGS	Debit	305	34256
2022-01-24	TX00030	Daily Sales Deposit	Sales Revenue	Credit	1119	35375
2022-01-24	TX00031	Coffee Supplier Payment	COGS	Debit	487	34888
2022-01-25	TX00032	Daily Sales Deposit	Sales Revenue	Credit	1089	35977
2022-01-26	TX00033	Daily Sales Deposit	Sales Revenue	Credit	959	36936
2022-01-26	TX00034	Coffee Supplier Payment	COGS	Debit	290	36646
2022-01-27	TX00035	Daily Sales Deposit	Sales Revenue	Credit	917	37563
2022-01-28	TX00036	Daily Sales Deposit	Sales Revenue	Credit	901	38464
2022-01-29	TX00037	Daily Sales Deposit	Sales Revenue	Credit	969	39433
2022-01-30	TX00038	Daily Sales Deposit	Sales Revenue	Credit	970	40403
2022-01-30	TX00039	Rent Payment	Operating Expense	Debit	314	40089
2022-01-31	TX00040	Daily Sales Deposit	Sales Revenue	Credit	889	40978
2022-02-01	TX00041	Daily Sales Deposit	Sales Revenue	Credit	907	41885
2022-02-02	TX00042	Daily Sales Deposit	Sales Revenue	Credit	1066	42951
2022-02-03	TX00043	Daily Sales Deposit	Sales Revenue	Credit	1109	44060
2022-02-04	TX00044	Daily Sales Deposit	Sales Revenue	Credit	887	44947
2022-02-05	TX00045	Daily Sales Deposit	Sales Revenue	Credit	740	45687
2022-02-06	TX00046	Daily Sales Deposit	Sales Revenue	Credit	1000	46687
2022-02-06	TX00047	Bakery Payment	COGS	Debit	426	46261
2022-02-07	TX00048	Daily Sales Deposit	Sales Revenue	Credit	1043	47304
2022-02-08	TX00049	Daily Sales Deposit	Sales Revenue	Credit	835	48139
2022-02-08	TX00050	Utility Bill Payment	Operating Expense	Debit	238	47901
2022-02-09	TX00051	Daily Sales Deposit	Sales Revenue	Credit	780	48681
2022-02-10	TX00052	Daily Sales Deposit	Sales Revenue	Credit	1118	49799
2022-02-11	TX00053	Daily Sales Deposit	Sales Revenue	Credit	960	50759
2022-02-12	TX00054	Daily Sales Deposit	Sales Revenue	Credit	740	51499
2022-02-13	TX00055	Daily Sales Deposit	Sales Revenue	Credit	900	52399
2022-02-14	TX00056	Daily Sales Deposit	Sales Revenue	Credit	1117	53516
2022-02-14	TX00057	Maintenance Payment	Operating Expense	Debit	161	53355
2022-02-15	TX00058	Daily Sales Deposit	Sales Revenue	Credit	798	54153
2022-02-16	TX00059	Daily Sales Deposit	Sales Revenue	Credit	913	55066
2022-02-17	TX00060	Daily Sales Deposit	Sales Revenue	Credit	1148	56214
2022-02-18	TX00061	Daily Sales Deposit	Sales Revenue	Credit	1130	57344
2022-02-19	TX00062	Daily Sales Deposit	Sales Revenue	Credit	956	58300
2022-02-20	TX00063	Daily Sales Deposit	Sales Revenue	Credit	954	59254
2022-02-21	TX00064	Daily Sales Deposit	Sales Revenue	Credit	982	60236
2022-02-22	TX00065	Daily Sales Deposit	Sales Revenue	Credit	714	60950
2022-02-22	TX00066	Maintenance Payment	Operating Expense	Debit	479	60471
2022-02-23	TX00067	Daily Sales Deposit	Sales Revenue	Credit	878	61349
2022-02-23	TX00068	Bakery Payment	COGS	Debit	330	61019
2022-02-24	TX00069	Daily Sales Deposit	Sales Revenue	Credit	751	61770
2022-02-25	TX00070	Daily Sales Deposit	Sales Revenue	Credit	1087	62857
2022-02-26	TX00071	Daily Sales Deposit	Sales Revenue	Credit	1106	63963
2022-02-27	TX00072	Daily Sales Deposit	Sales Revenue	Credit	842	64805
2022-02-28	TX00073	Daily Sales Deposit	Sales Revenue	Credit	735	65540
2022-03-01	TX00074	Daily Sales Deposit	Sales Revenue	Credit	726	66266
2022-03-02	TX00075	Daily Sales Deposit	Sales Revenue	Credit	485	66751
2022-03-03	TX00076	Daily Sales Deposit	Sales Revenue	Credit	569	67320
2022-03-04	TX00077	Daily Sales Deposit	Sales Revenue	Credit	533	67853
2022-03-05	TX00078	Daily Sales Deposit	Sales Revenue	Credit	507	68360
2022-03-05	TX00079	Utility Bill Payment	Operating Expense	Debit	385	67975
2022-03-06	TX00080	Daily Sales Deposit	Sales Revenue	Credit	527	68502
2022-03-07	TX00081	Daily Sales Deposit	Sales Revenue	Credit	747	69249
2022-03-08	TX00082	Daily Sales Deposit	Sales Revenue	Credit	589	69838
2022-03-08	TX00083	Utility Bill Payment	Operating Expense	Debit	476	69362
2022-03-09	TX00084	Daily Sales Deposit	Sales Revenue	Credit	520	69882
2022-03-10	TX00085	Daily Sales Deposit	Sales Revenue	Credit	632	70514
2022-03-11	TX00086	Daily Sales Deposit	Sales Revenue	Credit	597	71111
2022-03-12	TX00087	Daily Sales Deposit	Sales Revenue	Credit	536	71647
2022-03-13	TX00088	Daily Sales Deposit	Sales Revenue	Credit	624	72271
2022-03-13	TX00089	Utility Bill Payment	Operating Expense	Debit	271	72000
2022-03-14	TX00090	Daily Sales Deposit	Sales Revenue	Credit	773	72773
2022-03-15	TX00091	Daily Sales Deposit	Sales Revenue	Credit	632	73405
2022-03-16	TX00092	Daily Sales Deposit	Sales Revenue	Credit	717	74122
2022-03-17	TX00093	Daily Sales Deposit	Sales Revenue	Credit	451	74573
2022-03-18	TX00094	Daily Sales Deposit	Sales Revenue	Credit	694	75267
2022-03-19	TX00095	Daily Sales Deposit	Sales Revenue	Credit	512	75779
2022-03-19	TX00096	Utility Bill Payment	Operating Expense	Debit	180	75599
2022-03-20	TX00097	Daily Sales Deposit	Sales Revenue	Credit	512	76111
2022-03-21	TX00098	Daily Sales Deposit	Sales Revenue	Credit	619	76730
2022-03-21	TX00099	Bakery Payment	COGS	Debit	323	76407
2022-03-22	TX00100	Daily Sales Deposit	Sales Revenue	Credit	784	77191
2022-03-23	TX00101	Daily Sales Deposit	Sales Revenue	Credit	529	77720
2022-03-24	TX00102	Daily Sales Deposit	Sales Revenue	Credit	617	78337
2022-03-25	TX00103	Daily Sales Deposit	Sales Revenue	Credit	646	78983
2022-03-26	TX00104	Daily Sales Deposit	Sales Revenue	Credit	602	79585
2022-03-27	TX00105	Daily Sales Deposit	Sales Revenue	Credit	654	80239
2022-03-28	TX00106	Daily Sales Deposit	Sales Revenue	Credit	724	80963
2022-03-29	TX00107	Daily Sales Deposit	Sales Revenue	Credit	597	81560
2022-03-30	TX00108	Daily Sales Deposit	Sales Revenue	Credit	639	82199
2022-03-31	TX00109	Daily Sales Deposit	Sales Revenue	Credit	600	82799
2022-04-01	TX00110	Daily Sales Deposit	Sales Revenue	Credit	725	83524
2022-04-02	TX00111	Daily Sales Deposit	Sales Revenue	Credit	658	84182
2022-04-03	TX00112	Daily Sales Deposit	Sales Revenue	Credit	745	84927
2022-04-04	TX00113	Daily Sales Deposit	Sales Revenue	Credit	546	85473
2022-04-05	TX00114	Daily Sales Deposit	Sales Revenue	Credit	598	86071
2022-04-05	TX00115	Coffee Supplier Payment	COGS	Debit	227	85844
2022-04-06	TX00116	Daily Sales Deposit	Sales Revenue	Credit	759	86603
2022-04-06	TX00117	Coffee Supplier Payment	COGS	Debit	250	86353
2022-04-07	TX00118	Daily Sales Deposit	Sales Revenue	Credit	498	86851
2022-04-08	TX00119	Daily Sales Deposit	Sales Revenue	Credit	543	87394
2022-04-09	TX00120	Daily Sales Deposit	Sales Revenue	Credit	459	87853
2022-04-10	TX00121	Daily Sales Deposit	Sales Revenue	Credit	784	88637
2022-04-10	TX00122	Maintenance Payment	Operating Expense	Debit	239	88398
2022-04-11	TX00123	Daily Sales Deposit	Sales Revenue	Credit	436	88834
2022-04-12	TX00124	Daily Sales Deposit	Sales Revenue	Credit	408	89242
2022-04-13	TX00125	Daily Sales Deposit	Sales Revenue	Credit	546	89788
2022-04-14	TX00126	Daily Sales Deposit	Sales Revenue	Credit	530	90318
2022-04-15	TX00127	Daily Sales Deposit	Sales Revenue	Credit	453	90771
2022-04-16	TX00128	Daily Sales Deposit	Sales Revenue	Credit	515	91286
2022-04-16	TX00129	Rent Payment	Operating Expense	Debit	203	91083
2022-04-17	TX00130	Daily Sales Deposit	Sales Revenue	Credit	653	91736
2022-04-17	TX00131	Bakery Payment	COGS	Debit	198	91538
2022-04-18	TX00132	Daily Sales Deposit	Sales Revenue	Credit	748	92286
2022-04-19	TX00133	Daily Sales Deposit	Sales Revenue	Credit	765	93051
2022-04-20	TX00134	Daily Sales Deposit	Sales Revenue	Credit	709	93760
2022-04-21	TX00135	Daily Sales Deposit	Sales Revenue	Credit	568	94328
2022-04-21	TX00136	Bakery Payment	COGS	Debit	167	94161
2022-04-22	TX00137	Daily Sales Deposit	Sales Revenue	Credit	797	94958
2022-04-23	TX00138	Daily Sales Deposit	Sales Revenue	Credit	783	95741
2022-04-24	TX00139	Daily Sales Deposit	Sales Revenue	Credit	594	96335
2022-04-25	TX00140	Daily Sales Deposit	Sales Revenue	Credit	432	96767
2022-04-26	TX00141	Daily Sales Deposit	Sales Revenue	Credit	770	97537
2022-04-27	TX00142	Daily Sales Deposit	Sales Revenue	Credit	421	97958
2022-04-28	TX00143	Daily Sales Deposit	Sales Revenue	Credit	437	98395
2022-04-29	TX00144	Daily Sales Deposit	Sales Revenue	Credit	450	98845
2022-04-30	TX00145	Daily Sales Deposit	Sales Revenue	Credit	682	99527
2022-05-01	TX00146	Daily Sales Deposit	Sales Revenue	Credit	676	100203
2022-05-02	TX00147	Daily Sales Deposit	Sales Revenue	Credit	683	100886
2022-05-03	TX00148	Daily Sales Deposit	Sales Revenue	Credit	716	101602
2022-05-04	TX00149	Daily Sales Deposit	Sales Revenue	Credit	403	102005
2022-05-04	TX00150	Bakery Payment	COGS	Debit	148	101857
2022-05-05	TX00151	Daily Sales Deposit	Sales Revenue	Credit	571	102428
2022-05-06	TX00152	Daily Sales Deposit	Sales Revenue	Credit	445	102873
2022-05-07	TX00153	Daily Sales Deposit	Sales Revenue	Credit	498	103371
2022-05-08	TX00154	Daily Sales Deposit	Sales Revenue	Credit	436	103807
2022-05-09	TX00155	Daily Sales Deposit	Sales Revenue	Credit	701	104508
2022-05-10	TX00156	Daily Sales Deposit	Sales Revenue	Credit	498	105006
2022-05-11	TX00157	Daily Sales Deposit	Sales Revenue	Credit	515	105521
2022-05-12	TX00158	Daily Sales Deposit	Sales Revenue	Credit	560	106081
2022-05-13	TX00159	Daily Sales Deposit	Sales Revenue	Credit	527	106608
2022-05-14	TX00160	Daily Sales Deposit	Sales Revenue	Credit	622	107230
2022-05-15	TX00161	Daily Sales Deposit	Sales Revenue	Credit	722	107952
2022-05-16	TX00162	Daily Sales Deposit	Sales Revenue	Credit	679	108631
2022-05-17	TX00163	Daily Sales Deposit	Sales Revenue	Credit	741	109372
2022-05-18	TX00164	Daily Sales Deposit	Sales Revenue	Credit	526	109898
2022-05-19	TX00165	Daily Sales Deposit	Sales Revenue	Credit	785	110683
2022-05-20	TX00166	Daily Sales Deposit	Sales Revenue	Credit	503	111186
2022-05-21	TX00167	Daily Sales Deposit	Sales Revenue	Credit	698	111884
2022-05-22	TX00168	Daily Sales Deposit	Sales Revenue	Credit	438	112322
2022-05-23	TX00169	Daily Sales Deposit	Sales Revenue	Credit	646	112968
2022-05-24	TX00170	Daily Sales Deposit	Sales Revenue	Credit	705	113673
2022-05-25	TX00171	Daily Sales Deposit	Sales Revenue	Credit	412	114085
2022-05-25	TX00172	Bakery Payment	COGS	Debit	490	113595
2022-05-26	TX00173	Daily Sales Deposit	Sales Revenue	Credit	435	114030
2022-05-27	TX00174	Daily Sales Deposit	Sales Revenue	Credit	720	114750
2022-05-27	TX00175	Rent Payment	Operating Expense	Debit	499	114251
2022-05-28	TX00176	Daily Sales Deposit	Sales Revenue	Credit	770	115021
2022-05-29	TX00177	Daily Sales Deposit	Sales Revenue	Credit	491	115512
2022-05-30	TX00178	Daily Sales Deposit	Sales Revenue	Credit	687	116199
2022-05-31	TX00179	Daily Sales Deposit	Sales Revenue	Credit	741	116940
2022-06-01	\N	June Test Revenue	Sales Revenue	\N	5000.00	\N
2022-06-02	\N	June Test Supplies	COGS	\N	1500.00	\N
\.


--
-- Data for Name: checking_account_secondary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.checking_account_secondary (date, transaction_id, description, category, type, amount, balance) FROM stdin;
2022-01-01	SC00001	Transfer from Main	Transfer	Credit	3403	5403
2022-01-15	SC00002	Payroll Funding	Payroll	Debit	2688	2715
2022-02-01	SC00003	Transfer from Main	Transfer	Credit	5779	8494
2022-02-15	SC00004	Payroll Funding	Payroll	Debit	5216	3278
2022-03-01	SC00005	Transfer from Main	Transfer	Credit	5579	8857
2022-03-15	SC00006	Payroll Funding	Payroll	Debit	5228	3629
2022-04-01	SC00007	Transfer from Main	Transfer	Credit	4712	8341
2022-04-15	SC00008	Payroll Funding	Payroll	Debit	4093	4248
2022-05-01	SC00009	Transfer from Main	Transfer	Credit	4273	8521
2022-05-15	SC00010	Payroll Funding	Payroll	Debit	3957	4564
\.


--
-- Data for Name: credit_card_account; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.credit_card_account (date, transaction_id, vendor, category, type, amount, balance) FROM stdin;
2022-01-01	CC00001	Utility Company	Supplies	Debit	229	229
2022-01-08	CC00002	Facebook Ads	Other	Debit	444	673
2022-01-10	CC00003	Payment to CC	Payment	Credit	428	245
2022-01-15	CC00004	Utility Company	Marketing	Debit	360	605
2022-01-22	CC00005	Local Print Shop	Marketing	Debit	539	1144
2022-01-24	CC00006	Payment to CC	Payment	Credit	486	658
2022-01-29	CC00007	Coffee Supplier	Utilities	Debit	494	1152
2022-02-05	CC00008	Coffee Supplier	Marketing	Debit	179	1331
2022-02-12	CC00009	Facebook Ads	Marketing	Debit	449	1780
2022-02-19	CC00010	Utility Company	Other	Debit	363	2143
2022-02-26	CC00011	Coffee Supplier	Other	Debit	163	2306
2022-03-05	CC00012	Facebook Ads	Utilities	Debit	206	2512
2022-03-12	CC00013	Facebook Ads	Marketing	Debit	264	2776
2022-03-19	CC00014	Local Print Shop	Utilities	Debit	411	3187
2022-03-26	CC00015	Utility Company	Marketing	Debit	207	3394
2022-03-28	CC00016	Payment to CC	Payment	Credit	533	2861
2022-04-02	CC00017	Facebook Ads	Utilities	Debit	229	3090
2022-04-04	CC00018	Payment to CC	Payment	Credit	481	2609
2022-04-09	CC00019	Facebook Ads	Utilities	Debit	384	2993
2022-04-11	CC00020	Payment to CC	Payment	Credit	684	2309
2022-04-16	CC00021	Utility Company	Marketing	Debit	344	2653
2022-04-18	CC00022	Payment to CC	Payment	Credit	405	2248
2022-04-23	CC00023	Coffee Supplier	Other	Debit	111	2359
2022-04-30	CC00024	Utility Company	Utilities	Debit	315	2674
2022-05-02	CC00025	Payment to CC	Payment	Credit	416	2258
2022-05-07	CC00026	Facebook Ads	Marketing	Debit	405	2663
2022-05-14	CC00027	Utility Company	Utilities	Debit	283	2946
2022-05-21	CC00028	Coffee Supplier	Other	Debit	527	3473
2022-05-23	CC00029	Payment to CC	Payment	Credit	507	2966
2022-05-28	CC00030	Coffee Supplier	Supplies	Debit	435	3401
\.


--
-- Data for Name: employee_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employee_profiles (id, name, role, hourly_rate, is_active, is_seasonal) FROM stdin;
1	Alice Johnson	Owner	25.00	t	f
2	Brian Smith	Barista	16.50	t	f
3	Chloe Davis	Barista	16.00	t	f
4	Daniel Lee	Manager	18.75	t	f
5	Eva Thompson	Independent Contractor	17.50	t	f
6	Frank White	Seasonal Barista	15.00	t	t
\.


--
-- Data for Name: payroll_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payroll_history (employee_id, employee_name, role, pay_date, gross_pay, federal_tax, provincial_tax, cpp, ei, other_deductions, net_pay, employer_cpp, employer_ei, tips, travel_reimbursement, total_business_cost) FROM stdin;
\N	\N	\N	2022-06-03	1800.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
1	Alice Johnson	Owner	2022-01-07	2002.24	240.27	100.11	119.13	32.64	0	1510.09	119.13	45.69	0	0	2167.06
1	Alice Johnson	Owner	2022-01-21	1985.98	238.32	99.3	118.17	32.37	0	1497.82	118.17	45.32	0	0	2149.47
1	Alice Johnson	Owner	2022-02-04	2081.15	249.74	104.06	123.83	33.92	0	1569.6	123.83	47.49	0	0	2252.47
1	Alice Johnson	Owner	2022-02-18	1941.95	233.03	97.1	115.55	31.65	0	1464.62	115.55	44.32	0	0	2101.82
1	Alice Johnson	Owner	2022-03-04	1989.04	238.69	99.45	118.35	32.42	0	1500.14	118.35	45.39	0	0	2152.78
1	Alice Johnson	Owner	2022-03-18	1993.08	239.17	99.65	118.59	32.49	0	1503.18	118.59	45.48	0	0	2157.15
1	Alice Johnson	Owner	2022-04-01	1979.78	237.57	98.99	117.8	32.27	0	1493.15	117.8	45.18	0	0	2142.76
1	Alice Johnson	Owner	2022-04-15	2074.6	248.95	103.73	123.44	33.82	0	1564.66	123.44	47.34	0	0	2245.38
1	Alice Johnson	Owner	2022-04-29	2014.92	241.79	100.75	119.89	32.84	0	1519.65	119.89	45.98	0	0	2180.79
1	Alice Johnson	Owner	2022-05-13	1949.87	233.98	97.49	116.02	31.78	0	1470.59	116.02	44.5	0	0	2110.39
1	Alice Johnson	Owner	2022-05-27	1970.8	236.5	98.54	117.26	32.12	0	1486.37	117.26	44.97	0	0	2133.03
2	Brian Smith	Barista	2022-01-07	1301.43	156.17	65.07	77.44	21.21	0	981.54	77.44	29.7	190.21	0	1598.78
2	Brian Smith	Barista	2022-01-21	1383.1	165.97	69.16	82.29	22.54	0	1043.14	82.29	31.56	211.66	0	1708.61
2	Brian Smith	Barista	2022-02-04	1291.57	154.99	64.58	76.85	21.05	0	974.1	76.85	29.47	221.29	0	1619.18
2	Brian Smith	Barista	2022-02-18	1311.85	157.42	65.59	78.05	21.38	0	989.39	78.05	29.94	197.41	0	1617.25
2	Brian Smith	Barista	2022-03-04	1241.02	148.92	62.05	73.84	20.23	0	935.98	73.84	28.32	185.24	0	1528.42
2	Brian Smith	Barista	2022-03-18	1307.07	156.85	65.35	77.77	21.31	0	985.79	77.77	29.83	190.81	0	1605.48
2	Brian Smith	Barista	2022-04-01	1382.18	165.86	69.11	82.24	22.53	0	1042.44	82.24	31.54	252.44	0	1748.40
2	Brian Smith	Barista	2022-04-15	1306.37	156.76	65.32	77.73	21.29	0	985.26	77.73	29.81	209.3	0	1623.21
2	Brian Smith	Barista	2022-04-29	1277.42	153.29	63.87	76.01	20.82	0	963.43	76.01	29.15	193.59	0	1576.17
2	Brian Smith	Barista	2022-05-13	1301.72	156.21	65.09	77.45	21.22	0	981.76	77.45	29.71	217.58	0	1626.46
2	Brian Smith	Barista	2022-05-27	1283.7	154.04	64.18	76.38	20.92	0	968.16	76.38	29.29	193.05	0	1582.42
3	Chloe Davis	Barista	2022-01-07	1243.07	149.17	62.15	73.96	20.26	0	937.53	73.96	28.37	144.12	0	1489.52
3	Chloe Davis	Barista	2022-01-21	1241.67	149	62.08	73.88	20.24	0	936.47	73.88	28.33	202.91	0	1546.79
3	Chloe Davis	Barista	2022-02-04	1294.04	155.28	64.7	77	21.09	0	975.96	77	29.53	141.74	0	1542.31
3	Chloe Davis	Barista	2022-02-18	1168.22	140.19	58.41	69.51	19.04	0	881.07	69.51	26.66	191.95	0	1456.34
3	Chloe Davis	Barista	2022-03-04	1299.76	155.97	64.99	77.34	21.19	0	980.28	77.34	29.66	223.38	0	1630.14
3	Chloe Davis	Barista	2022-03-18	1245.47	149.46	62.27	74.11	20.3	0	939.33	74.11	28.42	138.11	0	1486.11
3	Chloe Davis	Barista	2022-04-01	1251.77	150.21	62.59	74.48	20.4	0	944.09	74.48	28.57	188.12	0	1542.94
3	Chloe Davis	Barista	2022-04-15	1284.41	154.13	64.22	76.42	20.94	0	968.7	76.42	29.31	191.34	0	1581.48
3	Chloe Davis	Barista	2022-04-29	1284.5	154.14	64.22	76.43	20.94	0	968.77	76.43	29.31	218.22	0	1608.46
3	Chloe Davis	Barista	2022-05-13	1277.53	153.3	63.88	76.01	20.82	0	963.51	76.01	29.15	211.51	0	1594.20
3	Chloe Davis	Barista	2022-05-27	1203.63	144.44	60.18	71.62	19.62	0	907.78	71.62	27.47	152.94	0	1455.66
4	Daniel Lee	Manager	2022-01-07	1489.39	178.73	74.47	88.62	24.28	0	1123.3	88.62	33.99	0	75	1687.00
4	Daniel Lee	Manager	2022-01-21	1543	185.16	77.15	91.81	25.15	0	1163.73	91.81	35.21	0	75	1745.02
4	Daniel Lee	Manager	2022-02-04	1562.69	187.52	78.13	92.98	25.47	0	1178.58	92.98	35.66	0	75	1766.33
4	Daniel Lee	Manager	2022-02-18	1422.41	170.69	71.12	84.63	23.19	0	1072.78	84.63	32.46	0	75	1614.50
4	Daniel Lee	Manager	2022-03-04	1518.55	182.23	75.93	90.35	24.75	0	1145.29	90.35	34.65	0	75	1718.55
4	Daniel Lee	Manager	2022-03-18	1566.89	188.03	78.34	93.23	25.54	0	1181.75	93.23	35.76	0	75	1770.88
4	Daniel Lee	Manager	2022-04-01	1418.76	170.25	70.94	84.42	23.13	0	1070.03	84.42	32.38	0	75	1610.56
4	Daniel Lee	Manager	2022-04-15	1502.12	180.25	75.11	89.38	24.48	0	1132.9	89.38	34.28	0	75	1700.78
4	Daniel Lee	Manager	2022-04-29	1545.15	185.42	77.26	91.94	25.19	0	1165.36	91.94	35.26	0	75	1747.35
4	Daniel Lee	Manager	2022-05-13	1602.91	192.35	80.15	95.37	26.13	0	1208.91	95.37	36.58	0	75	1809.86
4	Daniel Lee	Manager	2022-05-27	1437.43	172.49	71.87	85.53	23.43	0	1084.11	85.53	32.8	0	75	1630.76
5	Eva Thompson	Independent Contractor	2022-01-07	1365.38	136.54	54.62	0	0	0	1174.23	0	0	0	0	1365.38
5	Eva Thompson	Independent Contractor	2022-01-21	1447.06	144.71	57.88	0	0	0	1244.47	0	0	0	0	1447.06
5	Eva Thompson	Independent Contractor	2022-02-04	1399.9	139.99	56	0	0	0	1203.91	0	0	0	0	1399.9
5	Eva Thompson	Independent Contractor	2022-02-18	1369.62	136.96	54.78	0	0	0	1177.87	0	0	0	0	1369.62
5	Eva Thompson	Independent Contractor	2022-03-04	1441.57	144.16	57.66	0	0	0	1239.75	0	0	0	0	1441.57
5	Eva Thompson	Independent Contractor	2022-03-18	1416.04	141.6	56.64	0	0	0	1217.79	0	0	0	0	1416.04
5	Eva Thompson	Independent Contractor	2022-04-01	1369.41	136.94	54.78	0	0	0	1177.69	0	0	0	0	1369.41
5	Eva Thompson	Independent Contractor	2022-04-15	1367.41	136.74	54.7	0	0	0	1175.98	0	0	0	0	1367.41
5	Eva Thompson	Independent Contractor	2022-04-29	1396.86	139.69	55.87	0	0	0	1201.3	0	0	0	0	1396.86
5	Eva Thompson	Independent Contractor	2022-05-13	1312.27	131.23	52.49	0	0	0	1128.55	0	0	0	0	1312.27
5	Eva Thompson	Independent Contractor	2022-05-27	1533.25	153.33	61.33	0	0	0	1318.6	0	0	0	0	1533.25
\.


--
-- Name: employee_profiles employee_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_profiles
    ADD CONSTRAINT employee_profiles_pkey PRIMARY KEY (id);


--
-- Name: payroll_history fk_employee_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_history
    ADD CONSTRAINT fk_employee_id FOREIGN KEY (employee_id) REFERENCES public.employee_profiles(id);


--
-- PostgreSQL database dump complete
--

\unrestrict HoANtjMOgtrffpF2SkIIupde5acdbTuhm5hDhWkeh2eH6todWHp0ZxpjlGeW3ei

