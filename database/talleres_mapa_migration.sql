-- Coordenadas usadas por el mapa de talleres con Leaflet.
ALTER TABLE public.talleres
ADD COLUMN IF NOT EXISTS latitud NUMERIC(10,7);

ALTER TABLE public.talleres
ADD COLUMN IF NOT EXISTS longitud NUMERIC(10,7);

-- Ubicación inicial aproximada en Bogotá para talleres existentes sin coordenadas.
-- Después se puede reemplazar por coordenadas reales de cada dirección.
WITH talleres_sin_coordenadas AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS posicion
    FROM public.talleres
    WHERE latitud IS NULL OR longitud IS NULL
)
UPDATE public.talleres t
SET latitud = 4.6500 + ((tsc.posicion - 1) * 0.012),
    longitud = -74.0900 + ((tsc.posicion - 1) * 0.014)
FROM talleres_sin_coordenadas tsc
WHERE t.id = tsc.id;
