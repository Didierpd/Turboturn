-- Campos para que el mecánico registre el resultado de la revisión inicial.
ALTER TABLE public.citas
ADD COLUMN IF NOT EXISTS tiempo_estimado_revision VARCHAR(100);

ALTER TABLE public.citas
ADD COLUMN IF NOT EXISTS trabajo_requerido TEXT;

ALTER TABLE public.citas
ADD COLUMN IF NOT EXISTS costo_estimado_revision NUMERIC(10,2);
