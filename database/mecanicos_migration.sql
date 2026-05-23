CREATE TABLE IF NOT EXISTS public.mecanicos (
    id SERIAL PRIMARY KEY,
    taller_id INTEGER NOT NULL REFERENCES public.talleres(id),
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120),
    telefono VARCHAR(30),
    especialidad VARCHAR(100),
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.citas
ADD COLUMN IF NOT EXISTS mecanico_id INTEGER;

ALTER TABLE public.mecanicos
ADD COLUMN IF NOT EXISTS contrasena TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'citas_mecanico_id_fkey'
    ) THEN
        ALTER TABLE public.citas
        ADD CONSTRAINT citas_mecanico_id_fkey
        FOREIGN KEY (mecanico_id) REFERENCES public.mecanicos(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_mecanicos_taller_activo
ON public.mecanicos (taller_id, activo);

CREATE INDEX IF NOT EXISTS idx_citas_mecanico_id
ON public.citas (mecanico_id);

CREATE INDEX IF NOT EXISTS idx_mecanicos_email
ON public.mecanicos (LOWER(email));
