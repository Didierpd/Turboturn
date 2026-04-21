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