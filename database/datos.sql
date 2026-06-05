--
-- PostgreSQL database dump
--

\restrict NSPTReFw9tPyCGrwxbqLGaJfqakw2VtW42XHa3hJ9tDPaGULSZ9sAlqRdFX5KyK

-- Dumped from database version 17.10 (Debian 17.10-0+deb13u1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-0+deb13u1)

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

--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuarios (id, nombre, email, contrasena, rol, telefono, creado_en, estado, email_verificado, codigo_verificacion, mfa_secret, mfa_habilitado, mfa_verificado) FROM stdin;
92	moreno	nm0156168@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3106623089	2026-05-21 22:49:51.653844	activo	f	\N	OVXYJZ5U7UESHSJFAQSJELOPSEKZ7KIO	f	f
25	nicolas	nicolas@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	taller	3106623025	2026-05-04 23:30:33.576054	pendiente	f	\N	\N	f	f
22	Pedro Gómez	pedro@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	admin	3205556677	2026-04-21 17:46:11.369671	activo	t	\N	\N	f	f
20	Carlos Ramírez	carlos@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3001234567	2026-04-21 17:46:11.369671	activo	t	\N	\N	f	f
21	María López	maria@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3109876543	2026-04-21 17:46:11.369671	activo	t	\N	\N	f	f
23	Ana Martínez	ana@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3001112233	2026-04-21 17:46:11.369671	activo	t	\N	\N	f	f
24	Taller Central	taller@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	taller	3001234567	2026-05-04 22:50:51.73646	activo	t	\N	\N	f	f
57	moreno	gutierrezgeronimo137@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3106623225	2026-05-12 15:42:35.271903	activo	f	\N	\N	f	f
58	nicolas	nicolasmoreno8979@gmail.com	03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4	usuario	3106623085	2026-05-12 15:50:29.784901	activo	t	\N	\N	f	f
62	nicol	sofialeonf12@gmail.com	ca6f60a75d1113334e9b5911116df4be0d440fa7a5071dab14762271980b076d	usuario	3132207672	2026-05-15 15:16:16.917544	activo	f	\N	\N	f	f
63	didier	perillabarajas.didier9@gmail.com	1c8f50a9fc13e2a890bac09ef7e71e1633f5dbb1f72e57125db16e4c3587e2fc	usuario	3106623085	2026-05-15 15:19:33.03081	activo	f	\N	\N	f	f
\.


--
-- Data for Name: talleres; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.talleres (id, nombre, direccion, telefono, admin_id, creado_en) FROM stdin;
10	Taller TurboTurn	Calle 80 #45-12, Bogotá	6012345678	22	2026-04-21 17:47:04.891211
11	Taller Central	Por definir	3001234567	24	2026-05-04 23:19:35.44707
12	tallerdenicolas	carrera80#64-23	3106623025	25	2026-05-04 23:30:33.576054
\.


--
-- Data for Name: vehiculos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.vehiculos (id, usuario_id, tipo_vehiculo, marca, anio, placa, color, cilindraje, tipo_carroceria) FROM stdin;
3	20	moto	Honda	2020	ABC123	Rojo	150	\N
4	21	carro	Toyota	2019	XYZ789	Blanco	\N	Sedán
5	23	moto	Yamaha	2021	DEF456	Negro	200	\N
6	20	carro	Mazda	2018	GHI321	Gris	\N	Camioneta
\.


--
-- Data for Name: citas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.citas (id, usuario_id, vehiculo_id, taller_id, fecha_hora, estado, notas) FROM stdin;
3	20	3	10	2026-04-20 09:00:00	completada	Cambio de aceite urgente
4	21	4	10	2026-04-21 14:00:00	confirmada	Revisión general
5	23	5	10	2026-04-22 10:00:00	pendiente	Sincronización de carburador
6	20	6	10	2026-04-23 11:00:00	pendiente	Revisión de frenos
\.


--
-- Data for Name: codigos_verificacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.codigos_verificacion (id, email, codigo, creado_en, expira_en, usado, datos_registro) FROM stdin;
1	nm0156168@gmail.com	516323	2026-05-21 22:47:18.862991	2026-05-21 23:02:18.862991	f	{"rol": "usuario", "email": "nm0156168@gmail.com", "nombre": "nicolas", "telefono": "3106623025", "contrasena": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", "nombre_taller": null, "direccion_taller": null}
2	nm0156168@gmail.com	742265	2026-05-21 22:48:33.304482	2026-05-21 23:03:33.304482	t	{"rol": "usuario", "email": "nm0156168@gmail.com", "nombre": "moreno", "telefono": "3106623089", "contrasena": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", "nombre_taller": null, "direccion_taller": null}
\.


--
-- Data for Name: servicios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.servicios (id, taller_id, nombre, descripcion, precio) FROM stdin;
5	10	Cambio de aceite moto	Cambio de aceite y filtro para motos	45000.00
6	10	Sincronización de carburador	Ajuste y sincronización del carburador	60000.00
7	10	Cambio de aceite carro	Cambio de aceite y filtro para carros	80000.00
8	10	Revisión de frenos	Revisión y ajuste del sistema de frenos	55000.00
9	10	Cambio de llantas	Desmonte y montaje de llantas	90000.00
\.


--
-- Data for Name: historial_servicios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.historial_servicios (id, cita_id, servicio_id, observaciones, costo_final, fecha) FROM stdin;
3	3	5	Se cambió aceite 10W-40, filtro en buen estado	45000.00	2026-04-21 17:51:40.354851
4	4	7	Aceite sintético 5W-30, se recomendó cambio de filtro	80000.00	2026-04-21 17:51:40.354851
\.


--
-- Name: citas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.citas_id_seq', 6, true);


--
-- Name: codigos_verificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.codigos_verificacion_id_seq', 2, true);


--
-- Name: historial_servicios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.historial_servicios_id_seq', 4, true);


--
-- Name: servicios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.servicios_id_seq', 9, true);


--
-- Name: talleres_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.talleres_id_seq', 43, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usuarios_id_seq', 92, true);


--
-- Name: vehiculos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehiculos_id_seq', 6, true);


--
-- PostgreSQL database dump complete
--

\unrestrict NSPTReFw9tPyCGrwxbqLGaJfqakw2VtW42XHa3hJ9tDPaGULSZ9sAlqRdFX5KyK

