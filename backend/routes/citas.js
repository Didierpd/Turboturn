const express = require("express");
const router = express.Router();
const db = require("../db");

router.get("/:usuario_id", async (req, res) => {
  const { usuario_id } = req.params;

  const result = await db.query(`
    SELECT c.*, v.marca, v.placa
    FROM citas c
    JOIN vehiculos v ON c.vehiculo_id = v.id
    WHERE c.usuario_id = $1
  `, [usuario_id]);

  res.json(result.rows);
});

router.post("/", async (req, res) => {
  const { usuario_id, vehiculo_id, fecha_hora, notas } = req.body;

  const result = await db.query(
    `INSERT INTO citas 
    (usuario_id,vehiculo_id,taller_id,fecha_hora,notas)
    VALUES ($1,$2,1,$3,$4) RETURNING *`,
    [usuario_id, vehiculo_id, fecha_hora, notas]
  );

  res.json(result.rows[0]);
});

module.exports = router;