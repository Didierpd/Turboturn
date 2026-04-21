-- =============================================
-- BASE DE DATOS: TurboTurn
-- Proyecto: Gestión de turnos para talleres
-- Autores: Paula Pinilla, Didier Perilla, Nicolás Moreno
-- =============================================

-- Tabla de usuarios
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('cliente', 'mecanico', 'admin')),
    telefono VARCHAR(20),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de talleres
CREATE TABLE talleres (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    telefono VARCHAR(20),
    admin_id INT REFERENCES usuarios(id),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de vehiculos
CREATE TABLE vehiculos (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id),
    tipo_vehiculo VARCHAR(10) NOT NULL CHECK (tipo_vehiculo IN ('moto', 'carro')),
    marca VARCHAR(50) NOT NULL,
    anio INT NOT NULL,
    placa VARCHAR(10) UNIQUE NOT NULL,
    color VARCHAR(30),
    cilindraje INT,
    tipo_carroceria VARCHAR(30)
);

-- Tabla de servicios
CREATE TABLE servicios (
    id SERIAL PRIMARY KEY,
    taller_id INT REFERENCES talleres(id),
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL
);

-- Tabla de citas
CREATE TABLE citas (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id),
    vehiculo_id INT REFERENCES vehiculos(id),
    taller_id INT REFERENCES talleres(id),
    fecha_hora TIMESTAMP NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'confirmada', 'completada', 'cancelada')),
    notas TEXT
);

-- Tabla de historial de servicios
CREATE TABLE historial_servicios (
    id SERIAL PRIMARY KEY,
    cita_id INT REFERENCES citas(id),
    servicio_id INT REFERENCES servicios(id),
    observaciones TEXT,
    costo_final DECIMAL(10,2),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- DATOS DE PRUEBA
-- =============================================

-- Usuarios
INSERT INTO usuarios (nombre, email, contrasena, rol, telefono) VALUES
('Carlos Ramírez', 'carlos@gmail.com', '1234', 'cliente', '3001234567'),
('María López', 'maria@gmail.com', '1234', 'cliente', '3109876543'),
('Pedro Gómez', 'pedro@gmail.com', '1234', 'admin', '3205556677'),
('Ana Martínez', 'ana@gmail.com', '1234', 'cliente', '3001112233');

-- Taller
INSERT INTO talleres (nombre, direccion, telefono, admin_id) VALUES
('Taller TurboTurn', 'Calle 80 #45-12, Bogotá', '6012345678', 3);

-- Vehiculos
INSERT INTO vehiculos (usuario_id, tipo_vehiculo, marca, anio, placa, color, cilindraje, tipo_carroceria) VALUES
(1, 'moto', 'Honda', 2020, 'ABC123', 'Rojo', 150, NULL),
(2, 'carro', 'Toyota', 2019, 'XYZ789', 'Blanco', NULL, 'Sedán'),
(4, 'moto', 'Yamaha', 2021, 'DEF456', 'Negro', 200, NULL),
(1, 'carro', 'Mazda', 2018, 'GHI321', 'Gris', NULL, 'Camioneta');

-- Servicios
INSERT INTO servicios (taller_id, nombre, descripcion, precio) VALUES
(1, 'Cambio de aceite moto', 'Cambio de aceite y filtro para motos', 45000),
(1, 'Sincronización de carburador', 'Ajuste y sincronización del carburador', 60000),
(1, 'Cambio de aceite carro', 'Cambio de aceite y filtro para carros', 80000),
(1, 'Revisión de frenos', 'Revisión y ajuste del sistema de frenos', 55000),
(1, 'Cambio de llantas', 'Desmonte y montaje de llantas', 90000);

-- Citas
INSERT INTO citas (usuario_id, vehiculo_id, taller_id, fecha_hora, estado, notas) VALUES
(1, 1, 1, '2026-04-20 09:00:00', 'completada', 'Cambio de aceite urgente'),
(2, 2, 1, '2026-04-21 14:00:00', 'confirmada', 'Revisión general'),
(4, 3, 1, '2026-04-22 10:00:00', 'pendiente', 'Sincronización de carburador'),
(1, 4, 1, '2026-04-23 11:00:00', 'pendiente', 'Revisión de frenos');

-- Historial
INSERT INTO historial_servicios (cita_id, servicio_id, observaciones, costo_final) VALUES
(1, 1, 'Se cambió aceite 10W-40, filtro en buen estado', 45000),
(2, 3, 'Aceite sintético 5W-30, se recomendó cambio de filtro', 80000);
