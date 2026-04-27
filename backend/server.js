const express = require("express");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/usuarios", require("./routes/usuarios"));
app.use("/api/vehiculos", require("./routes/vehiculo"));
app.use("/api/citas", require("./routes/citas"));
app.use("/api/servicios", require("./routes/servicios"));

app.listen(3000, () => {
  console.log("Servidor corriendo en puerto 3000");
});