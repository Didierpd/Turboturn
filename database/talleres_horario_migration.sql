ALTER TABLE public.talleres
ADD COLUMN IF NOT EXISTS horario_apertura TIME NOT NULL DEFAULT '08:00',
ADD COLUMN IF NOT EXISTS horario_cierre TIME NOT NULL DEFAULT '18:00';

ALTER TABLE public.talleres
DROP CONSTRAINT IF EXISTS talleres_horario_check;

ALTER TABLE public.talleres
ADD CONSTRAINT talleres_horario_check
CHECK (horario_apertura < horario_cierre);
