"""Traza en JSONL: una línea por evento, legible por máquinas y por personas."""

import json
import time
from pathlib import Path


class Traza:
    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text("", encoding="utf-8")

    def evento(self, tipo: str, **datos) -> None:
        linea = {"t": round(time.time(), 3), "tipo": tipo, **datos}
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
