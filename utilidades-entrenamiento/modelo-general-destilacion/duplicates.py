"""Detección y resolución de imágenes casi duplicadas (hash perceptual dHash)."""
import sqlite3
from pathlib import Path

from PIL import Image

HASH_BITS = 64
DEFAULT_THRESHOLD = 2
CHUNKS = 8  # con distancia <= 7 al menos un fragmento de 8 bits coincide
GROUP_PAGE_SIZE = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS imagen_huella (
    id_imagen INTEGER PRIMARY KEY REFERENCES prenda_imagen(id_imagen) ON DELETE CASCADE,
    dhash TEXT NOT NULL,
    ancho INTEGER NOT NULL,
    alto INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS grupo_duplicado (
    id_grupo INTEGER PRIMARY KEY AUTOINCREMENT,
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'resuelto', 'descartado')),
    id_prenda_conservada INTEGER REFERENCES prenda(id_prenda),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS grupo_duplicado_miembro (
    id_grupo INTEGER NOT NULL REFERENCES grupo_duplicado(id_grupo) ON DELETE CASCADE,
    id_prenda INTEGER NOT NULL REFERENCES prenda(id_prenda),
    PRIMARY KEY (id_grupo, id_prenda)
);
CREATE INDEX IF NOT EXISTS idx_miembro_prenda ON grupo_duplicado_miembro(id_prenda);
"""


def dhash(path: Path) -> tuple[int, int, int]:
    with Image.open(path) as image:
        width, height = image.size
        pixels = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            value = (value << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return value, width, height


def find_groups(hashes: dict[int, int], threshold: int) -> list[list[int]]:
    """Agrupa claves cuyos hashes están a distancia de Hamming <= threshold."""
    parent: dict[int, int] = {key: key for key in hashes}

    def find(key: int) -> int:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    buckets: dict[tuple[int, int], list[int]] = {}
    for key, value in hashes.items():
        for chunk in range(CHUNKS):
            buckets.setdefault((chunk, (value >> (chunk * 8)) & 0xFF), []).append(key)
    for members in buckets.values():
        for index, first in enumerate(members):
            for second in members[index + 1:]:
                if find(first) != find(second) and bin(hashes[first] ^ hashes[second]).count("1") <= threshold:
                    parent[find(second)] = find(first)
    groups: dict[int, list[int]] = {}
    for key in hashes:
        groups.setdefault(find(key), []).append(key)
    return [sorted(group) for group in groups.values() if len(group) > 1]


def command_find_duplicates(database: Path, dataset_root: Path, threshold: int = DEFAULT_THRESHOLD) -> int:
    with sqlite3.connect(database, timeout=60) as connection:
        connection.executescript(SCHEMA)
        images = connection.execute(
            "SELECT i.id_imagen, i.id_prenda, i.ruta_relativa FROM prenda_imagen i "
            "JOIN prenda p ON p.id_prenda = i.id_prenda WHERE p.estado_revision != 'rechazado'"
        ).fetchall()
        known = {row[0] for row in connection.execute("SELECT id_imagen FROM imagen_huella")}
        computed = 0
        for image_id, _, relative in images:
            if image_id in known:
                continue
            try:
                value, width, height = dhash(dataset_root / relative)
            except (OSError, ValueError):
                continue
            connection.execute(
                "INSERT INTO imagen_huella (id_imagen, dhash, ancho, alto) VALUES (?, ?, ?, ?)",
                (image_id, f"{value:016x}", width, height),
            )
            computed += 1
        connection.commit()
        garment_by_image = {row[0]: row[1] for row in images}
        hashes = {
            garment_by_image[image_id]: int(value, 16)
            for image_id, value in connection.execute("SELECT id_imagen, dhash FROM imagen_huella")
            if image_id in garment_by_image
        }
        resolved = {
            row[0]
            for row in connection.execute(
                "SELECT m.id_prenda FROM grupo_duplicado_miembro m "
                "JOIN grupo_duplicado g ON g.id_grupo = m.id_grupo WHERE g.estado != 'pendiente'"
            )
        }
        connection.execute("DELETE FROM grupo_duplicado WHERE estado = 'pendiente'")
        groups = find_groups({k: v for k, v in hashes.items() if k not in resolved}, threshold)
        for members in groups:
            group_id = connection.execute("INSERT INTO grupo_duplicado DEFAULT VALUES").lastrowid
            connection.executemany(
                "INSERT INTO grupo_duplicado_miembro (id_grupo, id_prenda) VALUES (?, ?)",
                [(group_id, member) for member in members],
            )
        connection.commit()
    extra = sum(len(group) - 1 for group in groups)
    print(f"Huellas nuevas: {computed}. Grupos: {len(groups)}. Imágenes sobrantes: {extra} (umbral {threshold}).")
    return 0


def _recommended(members: list[dict]) -> int:
    return max(members, key=lambda item: (item["ancho"] * item["alto"], -item["id"]))["id"]


def list_groups(connection: sqlite3.Connection, page: int, state: str = "pendiente") -> dict:
    connection.executescript(SCHEMA)
    totals = {
        row[0]: row[1] for row in connection.execute("SELECT estado, COUNT(*) FROM grupo_duplicado GROUP BY estado")
    }
    total = totals.get(state, 0)
    pages = max(1, -(-total // GROUP_PAGE_SIZE))
    page = min(max(page, 1), pages)
    group_rows = connection.execute(
        "SELECT id_grupo, id_prenda_conservada FROM grupo_duplicado WHERE estado = ? "
        "ORDER BY id_grupo LIMIT ? OFFSET ?",
        (state, GROUP_PAGE_SIZE, (page - 1) * GROUP_PAGE_SIZE),
    ).fetchall()
    groups = []
    for group_id, kept in group_rows:
        members = [
            {
                "id": row[0], "codigo": row[1], "categoria": row[2], "split": row[3],
                "estado": row[4], "ancho": row[5] or 0, "alto": row[6] or 0,
                "imagen_url": f"/api/image/{row[0]}",
            }
            for row in connection.execute(
                """
                SELECT p.id_prenda, p.codigo, p.ruta_categoria, p.split, p.estado_revision,
                       h.ancho, h.alto
                FROM grupo_duplicado_miembro m
                JOIN prenda p ON p.id_prenda = m.id_prenda
                LEFT JOIN prenda_imagen i ON i.id_prenda = p.id_prenda
                LEFT JOIN imagen_huella h ON h.id_imagen = i.id_imagen
                WHERE m.id_grupo = ? GROUP BY p.id_prenda ORDER BY p.id_prenda
                """,
                (group_id,),
            )
        ]
        groups.append({"id": group_id, "recomendada": kept or _recommended(members), "miembros": members})
    return {
        "page": page, "pages": pages, "total": total, "estado": state,
        "pendientes": totals.get("pendiente", 0), "resueltos": totals.get("resuelto", 0),
        "descartados": totals.get("descartado", 0),
        "sobrantes": connection.execute(
            "SELECT COUNT(*) - COUNT(DISTINCT m.id_grupo) FROM grupo_duplicado_miembro m "
            "JOIN grupo_duplicado g ON g.id_grupo = m.id_grupo WHERE g.estado = 'pendiente'"
        ).fetchone()[0],
        "grupos": groups,
    }


def resolve_group(connection: sqlite3.Connection, group_id: int, keep: int | None) -> int:
    """Conserva una prenda y rechaza el resto; devuelve cuántas se rechazaron."""
    state = connection.execute("SELECT estado FROM grupo_duplicado WHERE id_grupo = ?", (group_id,)).fetchone()
    if state is None or state[0] != "pendiente":
        raise ValueError(f"El grupo {group_id} no está pendiente.")
    members = [
        row[0] for row in connection.execute(
            "SELECT id_prenda FROM grupo_duplicado_miembro WHERE id_grupo = ?", (group_id,)
        )
    ]
    if keep not in members:
        raise ValueError("La prenda a conservar no pertenece al grupo.")
    others = [member for member in members if member != keep]
    connection.executemany(
        "UPDATE prenda SET estado_revision = 'rechazado', apta_para_entrenamiento = 0 WHERE id_prenda = ?",
        [(member,) for member in others],
    )
    connection.execute(
        "UPDATE grupo_duplicado SET estado = 'resuelto', id_prenda_conservada = ? WHERE id_grupo = ?",
        (keep, group_id),
    )
    return len(others)


def ensure_purge_column(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(grupo_duplicado)")}
    if "archivos_eliminados" not in columns:
        connection.execute("ALTER TABLE grupo_duplicado ADD COLUMN archivos_eliminados INTEGER NOT NULL DEFAULT 0")


def purge_large_groups(database: Path, dataset_root: Path, min_size: int) -> tuple[int, int, int]:
    """Resuelve grupos con >= min_size miembros y borra los archivos de las imágenes sobrantes.

    Las filas de prenda_imagen se conservan (prenda rechazada) para que su SHA siga
    bloqueando futuras importaciones; solo se eliminan los archivos.
    """
    groups = rejected = files = 0
    with sqlite3.connect(database, timeout=60) as connection:
        connection.executescript(SCHEMA)
        ensure_purge_column(connection)
        pending = connection.execute(
            "SELECT g.id_grupo FROM grupo_duplicado g JOIN grupo_duplicado_miembro m USING (id_grupo) "
            "WHERE g.estado = 'pendiente' GROUP BY g.id_grupo HAVING COUNT(*) >= ?",
            (min_size,),
        ).fetchall()
        for (group_id,) in pending:
            members = list_groups_members(connection, group_id)
            keep = _recommended(members)
            rejected += resolve_group(connection, group_id, keep)
            for member in members:
                if member["id"] == keep:
                    continue
                for (relative,) in connection.execute(
                    "SELECT ruta_relativa FROM prenda_imagen WHERE id_prenda = ?", (member["id"],)
                ):
                    target = dataset_root / relative
                    if target.is_file():
                        target.unlink()
                        files += 1
                        try:
                            target.parent.rmdir()
                        except OSError:
                            pass
            connection.execute("UPDATE grupo_duplicado SET archivos_eliminados = 1 WHERE id_grupo = ?", (group_id,))
            groups += 1
        connection.commit()
    return groups, rejected, files


def list_groups_members(connection: sqlite3.Connection, group_id: int) -> list[dict]:
    return [
        {"id": row[0], "ancho": row[1] or 0, "alto": row[2] or 0}
        for row in connection.execute(
            """
            SELECT p.id_prenda, h.ancho, h.alto FROM grupo_duplicado_miembro m
            JOIN prenda p ON p.id_prenda = m.id_prenda
            LEFT JOIN prenda_imagen i ON i.id_prenda = p.id_prenda
            LEFT JOIN imagen_huella h ON h.id_imagen = i.id_imagen
            WHERE m.id_grupo = ? GROUP BY p.id_prenda ORDER BY p.id_prenda
            """,
            (group_id,),
        )
    ]


def dismiss_group(connection: sqlite3.Connection, group_id: int) -> None:
    """Marca el grupo como falso positivo: no son duplicadas."""
    updated = connection.execute(
        "UPDATE grupo_duplicado SET estado = 'descartado' WHERE id_grupo = ? AND estado = 'pendiente'",
        (group_id,),
    ).rowcount
    if not updated:
        raise ValueError(f"El grupo {group_id} no está pendiente.")


def undo_group(connection: sqlite3.Connection, group_id: int) -> None:
    """Deshace una resolución o un descarte y devuelve el grupo a pendiente."""
    ensure_purge_column(connection)
    row = connection.execute(
        "SELECT estado, id_prenda_conservada, archivos_eliminados FROM grupo_duplicado WHERE id_grupo = ?",
        (group_id,),
    ).fetchone()
    if row is not None and row[2]:
        raise ValueError("Los archivos de este grupo se eliminaron; restaura desde respaldos/.")
    if row is None or row[0] == "pendiente":
        raise ValueError(f"El grupo {group_id} no se puede deshacer.")
    if row[0] == "resuelto":
        connection.execute(
            "UPDATE prenda SET estado_revision = 'pendiente' WHERE estado_revision = 'rechazado' "
            "AND id_prenda IN (SELECT id_prenda FROM grupo_duplicado_miembro WHERE id_grupo = ? AND id_prenda != ?)",
            (group_id, row[1]),
        )
    connection.execute(
        "UPDATE grupo_duplicado SET estado = 'pendiente', id_prenda_conservada = NULL WHERE id_grupo = ?",
        (group_id,),
    )
