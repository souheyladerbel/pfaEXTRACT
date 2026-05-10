"""Affiche le schéma et un aperçu de data/history/extractions.db (sans tout le JSON)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    ROOT / "data" / "history" / "extractions.db",
    ROOT / "Data" / "history" / "extractions.db",
]


def main() -> None:
    db = next((p for p in CANDIDATES if p.is_file()), None)
    if db is None:
        print("Aucun fichier extractions.db trouvé sous data/history/ ni Data/history/.")
        sys.exit(1)
    print("Fichier:", db.resolve(), "\n")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    for row in con.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        if row[0]:
            print(row[0], "\n")
    n = con.execute("SELECT COUNT(*) FROM extraction_history").fetchone()[0]
    print("Nombre d'enregistrements:", n, "\n")
    q = """
    SELECT id, kind, source_filename, saved_at,
           LENGTH(payload_json) AS payload_octets,
           relative_path
    FROM extraction_history
    ORDER BY datetime(saved_at) DESC, id DESC
    LIMIT 15
    """
    print("Dernières lignes (payload tronqué dans cette vue) :\n")
    for r in con.execute(q):
        d = dict(r)
        print(d)
    con.close()
    print(
        "\nPour ouvrir le JSON d'une ligne : Python / sqlite3 / "
        "DB Browser for SQLite (https://sqlitebrowser.org/)."
    )


if __name__ == "__main__":
    main()
