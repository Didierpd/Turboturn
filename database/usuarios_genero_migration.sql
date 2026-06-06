ALTER TABLE public.usuarios
ADD COLUMN IF NOT EXISTS genero VARCHAR(20);

ALTER TABLE public.usuarios
DROP CONSTRAINT IF EXISTS usuarios_genero_check;

ALTER TABLE public.usuarios
ADD CONSTRAINT usuarios_genero_check
CHECK (
  genero IS NULL OR genero IN ('masculino', 'femenino', 'otro', 'prefiero_no_decir')
);
