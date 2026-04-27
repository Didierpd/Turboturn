const express = require("express");
const router = express.Router();
const db = require("../db");

router.post("/login", async (req, res) => {
  try {
    const { email, contrasena } = req.body;

    const result = await db.query(
      "SELECT * FROM usuarios WHERE email=$1 AND contrasena=$2",
      [email, contrasena]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ mensaje: "Credenciales incorrectas" });
    }

    res.json(result.rows[0]);

  } catch (error) {
    res.status(500).json(error);
  }
});

module.exports = router;