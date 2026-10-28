"""Génère les icônes de l'application (PNG) sans dépendance externe : python outils/generer_icones.py"""

import struct
import zlib
from pathlib import Path

FOND = (62, 38, 25)      # brun foncé
CABOSSE = (199, 125, 26)  # orange cacao
STRIE = (139, 90, 60)


def pixel(x, y, n):
    # Cabosse : ellipse inclinée au centre, avec des stries verticales.
    cx, cy = n / 2, n / 2
    dx, dy = (x - cx) / (n * 0.24), (y - cy) / (n * 0.36)
    if dx * dx + dy * dy <= 1:
        return STRIE if int((x - cx + n) / (n * 0.07)) % 2 == 0 and abs(dx) < 0.85 else CABOSSE
    return FOND


def png(n, chemin):
    lignes = b"".join(b"\x00" + bytes(c for x in range(n) for c in pixel(x, y, n)) for y in range(n))

    def bloc(type_, donnees):
        return struct.pack(">I", len(donnees)) + type_ + donnees + struct.pack(">I", zlib.crc32(type_ + donnees))

    contenu = (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
               + bloc(b"IDAT", zlib.compress(lignes, 9)) + bloc(b"IEND", b""))
    Path(chemin).write_bytes(contenu)


if __name__ == "__main__":
    dossier = Path(__file__).resolve().parent.parent / "static" / "icones"
    for taille in (192, 512):
        png(taille, dossier / f"icone-{taille}.png")
