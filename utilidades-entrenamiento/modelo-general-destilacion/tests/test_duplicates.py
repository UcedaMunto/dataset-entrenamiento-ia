import sqlite3
import tempfile
import unittest
from pathlib import Path

import duplicates


class DuplicatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection = sqlite3.connect(Path(self.temp.name) / "m.sqlite")
        self.connection.executescript(Path("/app/schema.sql").read_text(encoding="utf-8"))
        for index in range(1, 4):
            self.connection.execute(
                "INSERT INTO prenda (codigo, ruta_categoria, split) VALUES (?, 'superior/camisas', 'train')",
                (f"C-{index}",),
            )
        self.connection.executescript(duplicates.SCHEMA)
        self.connection.execute("INSERT INTO grupo_duplicado DEFAULT VALUES")
        self.connection.executemany(
            "INSERT INTO grupo_duplicado_miembro VALUES (1, ?)", [(1,), (2,), (3,)]
        )

    def test_find_groups_uses_hamming_distance(self):
        groups = duplicates.find_groups({1: 0b0, 2: 0b11, 3: 0b111 << 40, 4: 0b111 << 40 | 1}, 2)
        self.assertEqual(sorted(groups), [[1, 2], [3, 4]])
        self.assertEqual(duplicates.find_groups({1: 0, 2: (1 << 64) - 1}, 2), [])

    def test_resolve_rejects_others_and_undo_restores(self):
        self.assertEqual(duplicates.resolve_group(self.connection, 1, 2), 2)
        states = dict(self.connection.execute("SELECT id_prenda, estado_revision FROM prenda"))
        self.assertEqual(states, {1: "rechazado", 2: "pendiente", 3: "rechazado"})
        with self.assertRaises(ValueError):
            duplicates.resolve_group(self.connection, 1, 2)
        duplicates.undo_group(self.connection, 1)
        states = dict(self.connection.execute("SELECT id_prenda, estado_revision FROM prenda"))
        self.assertEqual(set(states.values()), {"pendiente"})

    def test_keep_must_belong_to_group_and_dismiss_changes_nothing(self):
        with self.assertRaises(ValueError):
            duplicates.resolve_group(self.connection, 1, 99)
        duplicates.dismiss_group(self.connection, 1)
        listing = duplicates.list_groups(self.connection, 1, "descartado")
        self.assertEqual(listing["total"], 1)
        self.assertEqual(len(listing["grupos"][0]["miembros"]), 3)

    def test_purge_deletes_files_but_keeps_rows_blocking_reimport(self):
        root = Path(self.temp.name)
        for index in range(1, 4):
            folder = root / f"C-{index}"
            folder.mkdir()
            (folder / "i.png").write_bytes(b"x")
            self.connection.execute(
                "INSERT INTO prenda_imagen (id_prenda, ruta_relativa, fuente, permiso_uso, sha256) "
                "VALUES (?, ?, 'aig', 't', ?)",
                (index, f"C-{index}/i.png", f"sha{index}"),
            )
            self.connection.execute(
                "INSERT INTO imagen_huella (id_imagen, dhash, ancho, alto) VALUES (?, '0', ?, 10)",
                (index, index * 10),
            )
        self.connection.commit()
        database = root / "m.sqlite"
        self.assertEqual(duplicates.purge_large_groups(database, root, 4), (0, 0, 0))
        self.assertEqual(duplicates.purge_large_groups(database, root, 3), (1, 2, 2))
        self.assertTrue((root / "C-3" / "i.png").is_file())
        self.assertFalse((root / "C-1").exists())
        with sqlite3.connect(database) as check:
            self.assertEqual(check.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 3)
            with self.assertRaises(ValueError):
                duplicates.undo_group(check, 1)
