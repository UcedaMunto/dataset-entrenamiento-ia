PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prenda (
    id_prenda INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    ruta_categoria TEXT NOT NULL,
    split TEXT CHECK (split IN ('train', 'val', 'test') OR split IS NULL),
    estado_revision TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado_revision IN ('pendiente', 'aprobado', 'rechazado')),
    apta_para_entrenamiento INTEGER NOT NULL DEFAULT 0
        CHECK (apta_para_entrenamiento IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prenda_imagen (
    id_imagen INTEGER PRIMARY KEY,
    id_prenda INTEGER NOT NULL,
    ruta_relativa TEXT NOT NULL UNIQUE,
    vista TEXT,
    es_fotografia_real INTEGER NOT NULL DEFAULT 1
        CHECK (es_fotografia_real IN (0, 1)),
    fuente TEXT NOT NULL,
    permiso_uso TEXT NOT NULL,
    sha256 TEXT,
    FOREIGN KEY (id_prenda) REFERENCES prenda(id_prenda) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS catalogo_propiedad (
    id_propiedad INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    tipo_propiedad TEXT NOT NULL
        CHECK (tipo_propiedad IN ('tipo_prenda', 'color', 'estilo', 'atributo')),
    valores_permitidos TEXT,
    tipo_valor TEXT NOT NULL DEFAULT 'texto'
        CHECK (tipo_valor IN ('texto', 'numero', 'booleano')),
    permite_varios INTEGER NOT NULL DEFAULT 0
        CHECK (permite_varios IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1
        CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS valor_propiedad_prenda (
    id_valor INTEGER PRIMARY KEY,
    id_prenda INTEGER NOT NULL,
    id_propiedad INTEGER NOT NULL,
    valor TEXT NOT NULL,
    FOREIGN KEY (id_prenda) REFERENCES prenda(id_prenda) ON DELETE CASCADE,
    FOREIGN KEY (id_propiedad) REFERENCES catalogo_propiedad(id_propiedad),
    UNIQUE (id_prenda, id_propiedad, valor)
);

CREATE INDEX IF NOT EXISTS idx_prenda_split_revision
    ON prenda(split, estado_revision, apta_para_entrenamiento);

CREATE INDEX IF NOT EXISTS idx_prenda_imagen_prenda
    ON prenda_imagen(id_prenda);

CREATE INDEX IF NOT EXISTS idx_valor_prenda
    ON valor_propiedad_prenda(id_prenda);

CREATE INDEX IF NOT EXISTS idx_valor_propiedad
    ON valor_propiedad_prenda(id_propiedad);

INSERT OR IGNORE INTO catalogo_propiedad
    (codigo, nombre, tipo_propiedad, valores_permitidos, tipo_valor, permite_varios)
VALUES
    ('tipo_prenda', 'Tipo de prenda', 'tipo_prenda',
     '["abrigo","blusa","camisa","chaqueta","falda","pantalon","short","sueter","vestido"]',
     'texto', 0),
    ('color', 'Color', 'color',
     '["amarillo","azul","beige","blanco","cafe","gris","morado","multicolor","naranja","negro","rojo","rosa","verde","unknown"]',
     'texto', 1),
    ('estilo', 'Estilo', 'estilo',
     '["casual","deportivo","elegante","fiesta","formal","verano","unknown"]',
     'texto', 1),
    ('largo', 'Largo', 'atributo', NULL, 'texto', 0),
    ('corte', 'Corte', 'atributo', NULL, 'texto', 0),
    ('patron', 'Patrón', 'atributo', NULL, 'texto', 0);

UPDATE catalogo_propiedad
SET valores_permitidos =
    '["abrigo","blusa","camisa","chaqueta","falda","pantalon","short","sueter","vestido"]'
WHERE codigo = 'tipo_prenda';
