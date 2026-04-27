const express = require("express");
const router = express.Router();
const db = require("../db");

router.get("/:usuario_id", async (req, res) => {
  const { usuario_id } = req.params;

  const result = await db.query(
    "SELECT * FROM vehiculos WHERE usuario_id=$1",
    [usuario_id]
  );

  res.json(result.rows);
});

router.post("/", async (req, res) => {
  const { usuario_id, marca, anio, placa, color } = req.body;

  const result = await db.query(
    `INSERT INTO vehiculos 
     (usuario_id,tipo_vehiculo,marca,anio,placa,color)
     VALUES ($1,'carro',$2,$3,$4,$5) RETURNING *`,
    [usuario_id, marca, anio, placa, color]
  );

  res.json(result.rows[0]);
});

module.exports = router;