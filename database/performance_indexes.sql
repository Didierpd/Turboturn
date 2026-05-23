CREATE INDEX IF NOT EXISTS idx_citas_usuario_fecha
ON public.citas (usuario_id, fecha_hora DESC);

CREATE INDEX IF NOT EXISTS idx_citas_taller_fecha
ON public.citas (taller_id, fecha_hora DESC);

CREATE INDEX IF NOT EXISTS idx_citas_vehiculo_id
ON public.citas (vehiculo_id);

CREATE INDEX IF NOT EXISTS idx_historial_servicios_cita_id
ON public.historial_servicios (cita_id);

CREATE INDEX IF NOT EXISTS idx_historial_servicios_servicio_id
ON public.historial_servicios (servicio_id);

CREATE INDEX IF NOT EXISTS idx_historial_servicios_fecha
ON public.historial_servicios (fecha DESC);

CREATE INDEX IF NOT EXISTS idx_servicios_taller_id
ON public.servicios (taller_id);

CREATE INDEX IF NOT EXISTS idx_vehiculos_usuario_id
ON public.vehiculos (usuario_id);

CREATE INDEX IF NOT EXISTS idx_talleres_admin_id
ON public.talleres (admin_id);

CREATE INDEX IF NOT EXISTS idx_mecanicos_taller_activo
ON public.mecanicos (taller_id, activo);

CREATE INDEX IF NOT EXISTS idx_citas_mecanico_id
ON public.citas (mecanico_id);

CREATE INDEX IF NOT EXISTS idx_mecanicos_email
ON public.mecanicos (LOWER(email));
