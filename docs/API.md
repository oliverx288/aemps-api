# Contrato de la API de problemas de suministro (AEMPS)

Este documento es la **fuente de verdad** para el frontend y el backend. Si algo
cambia en la API, se cambia primero aquí y se avisa.

- Versión del contrato: **1.1** (aprobado por la usuaria; ver registro de cambios en la sección 7)
- Base de la API: `http://localhost:8000` (desarrollo). Todas las rutas empiezan por `/api`.
- Formato: JSON en UTF-8. Los nombres de los campos están en español y en `snake_case`.
- La API **solo lee de nuestra base de datos SQLite** (`backend/aemps.db`). Nunca llama a CIMA
  mientras atiende una petición; eso lo hace un script de importación aparte.

---

## 1. De dónde vienen los datos (lo que hemos observado)

La fuente es `https://cima.aemps.es/cima/rest/psuministro` (pública, sin clave).
Está paginada: `?pagina=1`, `?pagina=2`, ... con 200 resultados por página.
También existe `.../psuministro/{cn}` para un solo medicamento.

Respuesta real (recortada):

```json
{
  "totalFilas": 922,
  "pagina": 1,
  "tamanioPagina": 200,
  "resultados": [
    {
      "cn": "677012",
      "nombre": "EXEMESTANO STADA 25 mg COMPRIMIDOS RECUBIERTOS CON PELICULA EFG , 30 comprimidos",
      "tipoProblemaSuministro": 5,
      "fini": 1794438000000,
      "ffin": 1795647600000,
      "activo": true,
      "observ": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración."
    }
  ]
}
```

Datos que comprobamos al revisar las 5 páginas (922 registros, 13-nov-2026):

| Hecho observado | Consecuencia para nuestro diseño |
|---|---|
| `cn` es único (922 registros, 922 `cn` distintos) y es un texto de 6 dígitos | Es la clave primaria. Se guarda como **TEXT**, no como número (para no perder ceros a la izquierda si los hubiera). |
| `fini` y `ffin` son **milisegundos desde 1970 (epoch)**, y corresponden a la medianoche hora de Madrid (p. ej. `1794438000000` = 2026-11-12 00:00 en Madrid) | Los convertimos a fecha `YYYY-MM-DD` en zona `Europe/Madrid`. Ver sección 4. |
| `ffin` **falta** en 268 de 922 registros | Es opcional: significa "fecha de fin todavía no conocida". Se guarda como `NULL`. |
| `activo` vale `true` en los 922 registros | Hoy la fuente solo lista problemas vigentes y un problema resuelto simplemente desaparece de la lista. Aun así **guardamos `activo` tal cual** (columna propia) y el estado se deriva de él y de `en_origen`; ver sección 5. |
| `tipoProblemaSuministro` es un número (valores vistos: 1 a 7 y 9 a 12) | CIMA no publica aquí el significado de cada código. Lo guardamos tal cual como número (INTEGER) y **no inventamos nombres** para los tipos. El texto explicativo viene en `observ`. |
| `observ` está siempre presente (máx. 345 caracteres) | Texto libre para mostrar al usuario. |
| `nombre` mezcla marca, forma farmacéutica y formato en un único texto | Lo guardamos entero. No intentamos separarlo. |

---

## 2. Esquema de la base de datos (SQLite)

Archivo: `backend/aemps.db`. Una sola tabla.

```sql
CREATE TABLE IF NOT EXISTS problemas_suministro (
    cn                 TEXT    PRIMARY KEY,          -- código nacional (clave: evita duplicados)
    nombre             TEXT    NOT NULL,             -- nombre completo del medicamento
    nombre_busqueda    TEXT    NOT NULL,             -- nombre en minúsculas y sin tildes, para buscar
    tipo_problema      INTEGER NOT NULL,             -- código numérico de CIMA (tipoProblemaSuministro)
    fecha_inicio       TEXT    NOT NULL,             -- 'YYYY-MM-DD' (fini convertido, hora de Madrid)
    fecha_fin          TEXT,                         -- 'YYYY-MM-DD' o NULL si no se conoce (ffin)
    observaciones      TEXT    NOT NULL DEFAULT '',  -- texto libre (observ)
    activo             INTEGER NOT NULL DEFAULT 1,   -- campo 'activo' de la AEMPS tal cual: 1 = true, 0 = false
    en_origen          INTEGER NOT NULL DEFAULT 1,   -- 1 = aparecía en CIMA en la última importación, 0 = ya no
    actualizado_en     TEXT    NOT NULL              -- fecha/hora UTC de la última importación que lo tocó (ISO 8601)
);

CREATE INDEX IF NOT EXISTS idx_problemas_fecha_inicio ON problemas_suministro (fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_problemas_fecha_fin    ON problemas_suministro (fecha_fin);
CREATE INDEX IF NOT EXISTS idx_problemas_tipo         ON problemas_suministro (tipo_problema);
CREATE INDEX IF NOT EXISTS idx_problemas_en_origen    ON problemas_suministro (en_origen);
```

### Por qué así

- **`cn` como PRIMARY KEY**: SQLite no deja insertar dos filas con el mismo `cn`. Al reimportar usamos
  `INSERT ... ON CONFLICT(cn) DO UPDATE SET ...`: si el `cn` ya existe se actualiza la fila, y si no, se crea.
  Así podemos importar cuantas veces queramos sin duplicar.
- **Fechas como TEXT `YYYY-MM-DD`**: SQLite no tiene tipo fecha. Guardadas así se ordenan y comparan
  correctamente con `<`, `>`, `ORDER BY`, y se leen a simple vista.
- **`nombre_busqueda`**: el `LIKE` de SQLite ignora mayúsculas solo en letras sin tilde, así que buscar
  `"paracetamol"` no encontraría `"PARACETAMOL"` con tildes en otras palabras de forma fiable. Guardamos una copia
  normalizada (minúsculas, sin tildes) y la API normaliza igual lo que escribe la usuaria. Con unos ~1000 registros
  una búsqueda `LIKE '%texto%'` es instantánea; no hace falta nada más sofisticado (FTS).
- **`en_origen`**: es lo que nos permite detectar problemas resueltos. En cada importación se ponen todas las filas
  a `en_origen = 0` y luego las que vienen de CIMA vuelven a `1` (por el upsert). Las que sigan en `0` ya no
  están en CIMA: se han resuelto. **No se borran**, así se conserva el histórico.
- **Índices**: sobre las columnas por las que se filtra u ordena (`fecha_inicio`, `fecha_fin`, `tipo_problema`,
  `en_origen`). No hay índice útil para `LIKE '%x%'`, pero con este volumen no importa.
- **`activo`**: copia fiel del campo `activo` de la AEMPS (1 o 0). Si CIMA no lo enviara, se guarda 1.
- **El estado no se guarda**: se deriva al consultar de `activo` y `en_origen` (sección 5). `vencido` tampoco se
  guarda: depende de la fecha de hoy, así que se calcula en cada consulta.

---

## 3. Convenciones generales

### Fechas

- Fechas (sin hora): texto `"YYYY-MM-DD"`, por ejemplo `"2026-11-12"`. Son días de calendario en hora de Madrid.
- Fecha y hora (solo `actualizado_en`): ISO 8601 en UTC, por ejemplo `"2026-11-13T09:30:00Z"`.
- La API **nunca** devuelve milisegundos epoch. El frontend solo tiene que formatear el texto para mostrarlo
  (p. ej. `12/11/2026`).
- `fecha_fin: null` significa "fin no conocido"; el frontend debe mostrar algo como "Sin fecha de fin prevista".

### CORS

El frontend será HTML/JS estático servido desde otro origen (p. ej. `http://localhost:5500` con Live Server),
y el navegador bloquea por defecto las peticiones entre orígenes distintos. Por eso FastAPI llevará `CORSMiddleware`:

- Orígenes permitidos: los de la variable de entorno `CORS_ORIGINS` en `backend/.env`
  (lista separada por comas). Valor por defecto en desarrollo:
  `http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080`.
- Métodos permitidos: `GET`, `POST`, `OPTIONS`. Cabeceras: `Content-Type`.
- No se usan cookies ni credenciales. No hay autenticación (los datos son públicos).
- No usamos `*` para que quede claro qué orígenes se aceptan; si el frontend se sirve desde otro puerto, se
  añade a `CORS_ORIGINS`.

### Errores

Todos los errores devuelven el código HTTP correspondiente y un JSON con la clave `detail`:

| Código | Cuándo | Cuerpo |
|---|---|---|
| `200` | Todo correcto | Datos |
| `404` | El `cn` pedido no existe en la base | `{"detail": "No existe ningún problema de suministro con cn 000000"}` |
| `422` | Parámetro inválido (p. ej. `pagina=0`, `estado=otro`) | `{"detail": [{"loc": ["query","pagina"], "msg": "...", "type": "..."}]}` (formato estándar de FastAPI) |
| `501` | Endpoint reservado, aún no implementado (chatbot) | `{"detail": "El chatbot todavía no está disponible"}` |
| `500` | Error inesperado del servidor | `{"detail": "Error interno del servidor"}` |
| `503` | La base de datos no existe o no se puede abrir (no se ha ejecutado la importación) | `{"detail": "Base de datos no disponible. Ejecuta primero la importación."}` |

Nota: en `404`, `501`, `500` y `503` el `detail` es un texto; en `422` es una lista. El frontend debe
comprobar si es texto o lista antes de mostrarlo.

---

## 4. Endpoints

### 4.1 `GET /api/salud`

Comprobación rápida de que la API funciona y de cuándo se importaron los datos por última vez.

Respuesta `200`:

```json
{
  "estado": "ok",
  "total_registros": 922,
  "ultima_importacion": "2026-11-13T09:30:00Z"
}
```

`ultima_importacion` es `null` si la tabla está vacía.

---

### 4.2 `GET /api/problemas`  (listado con búsqueda, filtros y paginación)

Parámetros de query (todos opcionales):

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `q` | texto | (vacío) | Busca en el nombre del medicamento **y** en el `cn`. Sin distinguir mayúsculas ni tildes. Mínimo 2 caracteres si se envía. Ej.: `q=ibuprofeno`, `q=677012`. |
| `estado` | `activo` \| `resuelto` \| `todos` | `activo` | Filtra por estado (sección 5). |
| `ocultar_vencidos` | booleano (`true` / `false`) | `false` | Si es `true`, oculta los registros con `vencido = true` (su `fecha_fin` ya pasó, hoy en `Europe/Madrid`). Por defecto no se oculta nada. Los registros sin `fecha_fin` nunca se ocultan. |
| `tipo` | entero | (todos) | Filtra por `tipo_problema`. |
| `orden` | `fecha_inicio_desc` \| `fecha_inicio_asc` \| `nombre` | `fecha_inicio_desc` | Orden de los resultados. Si hay empate se ordena por `cn` para que la paginación sea estable. |
| `pagina` | entero >= 1 | `1` | Número de página (empieza en 1). |
| `tamanio` | entero 1-100 | `20` | Resultados por página. |

Respuesta `200`:

```json
{
  "total": 633,
  "pagina": 1,
  "tamanio": 20,
  "total_paginas": 32,
  "resultados": [
    {
      "cn": "677012",
      "nombre": "EXEMESTANO STADA 25 mg COMPRIMIDOS RECUBIERTOS CON PELICULA EFG , 30 comprimidos",
      "tipo_problema": 5,
      "fecha_inicio": "2026-11-12",
      "fecha_fin": "2026-11-26",
      "estado": "activo",
      "vencido": false,
      "observaciones": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración."
    },
    {
      "cn": "667105",
      "nombre": "BEGLAN 25 microgramos/inhalación, suspensión para inhalación en envase a presión , 1 inhalador de 120 dosis",
      "tipo_problema": 5,
      "fecha_inicio": "2026-11-11",
      "fecha_fin": null,
      "estado": "activo",
      "vencido": false,
      "observaciones": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración."
    }
  ]
}
```

Notas:

- `total` es el número de filas que cumplen los filtros (no solo las de la página), para poder pintar el paginador.
- Si no hay coincidencias: `200` con `"total": 0`, `"total_paginas": 0` y `"resultados": []` (no es un error).
- Si `pagina` supera `total_paginas`, devuelve `200` con `resultados: []`.
- El listado devuelve los mismos campos que el detalle excepto `actualizado_en`.
- `estado` y `vencido` son campos independientes: un registro puede ser `"activo"` y a la vez `vencido: true`
  (la AEMPS aún lo marca activo pero su fecha de fin ya pasó). Con `ocultar_vencidos=true` esos desaparecen del listado.

Ejemplos de petición:

```
GET /api/problemas
GET /api/problemas?q=ibuprofeno&estado=todos
GET /api/problemas?ocultar_vencidos=true
GET /api/problemas?tipo=5&orden=nombre&pagina=2&tamanio=50
```

Ejemplo de error `422`: `GET /api/problemas?pagina=0`.

---

### 4.3 `GET /api/problemas/{cn}`  (detalle)

Parámetro de ruta: `cn` (texto, código nacional).

Ejemplo: `GET /api/problemas/677012`

Respuesta `200`:

```json
{
  "cn": "677012",
  "nombre": "EXEMESTANO STADA 25 mg COMPRIMIDOS RECUBIERTOS CON PELICULA EFG , 30 comprimidos",
  "tipo_problema": 5,
  "fecha_inicio": "2026-11-12",
  "fecha_fin": "2026-11-26",
  "estado": "activo",
  "vencido": false,
  "observaciones": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración.",
  "actualizado_en": "2026-11-13T09:30:00Z"
}
```

Errores: `404` si el `cn` no existe (ver sección 3). Este endpoint devuelve el problema **sea cual sea su estado**
(también los resueltos).

---

### 4.4 `GET /api/resumen`

Contadores para cabeceras y tarjetas del frontend, sin tener que paginar todo.

Respuesta `200`:

```json
{
  "total": 922,
  "activos": 922,
  "resueltos": 0,
  "por_tipo": [
    {"tipo_problema": 5, "total": 633},
    {"tipo_problema": 6, "total": 69}
  ],
  "ultima_importacion": "2026-11-13T09:30:00Z"
}
```

- `por_tipo` cuenta solo los problemas **activos** (por `estado`, sin tener en cuenta `vencido`), ordenados de mayor
  a menor `total`.
- `total = activos + resueltos`.
- `activos` y `resueltos` siguen la regla de `estado` (sección 5); no se descuentan los vencidos.

---

### 4.5 `POST /api/chat`  (RESERVADO, fase posterior)

Se reserva la ruta y la forma de la petición para que el frontend pueda preparar su pantalla, pero **por ahora
responde `501`**.

Petición (prevista):

```json
{ "mensaje": "¿Hay problemas de suministro con el ibuprofeno?" }
```

Respuesta `501` (actual):

```json
{ "detail": "El chatbot todavía no está disponible" }
```

Respuesta `200` (prevista, puede ampliarse cuando se implemente, avisando antes):

```json
{
  "respuesta": "Sí, hay 3 problemas activos con ibuprofeno...",
  "cn_relacionados": ["650123", "650124"]
}
```

---

## 5. Cómo se derivan `estado` y `vencido`

Ninguno de los dos está guardado en la base de datos: se calculan al consultar. El frontend debe usar los campos
tal cual y **no recalcularlos** con las fechas.

### `estado` (solo `"activo"` o `"resuelto"`)

Respeta el campo `activo` de la AEMPS:

```
estado = "activo"     si  activo = 1  y  en_origen = 1
estado = "resuelto"   en cualquier otro caso (activo = 0, o en_origen = 0)
```

- `activo = true` en la AEMPS -> `"activo"`; `activo = false` -> `"resuelto"`.
- Un registro que **desaparece de CIMA** (`en_origen = 0`) sigue contando como `"resuelto"`.
- La fecha de fin **ya no influye** en `estado`.

### `vencido` (booleano)

```
vencido = true    si  fecha_fin no es null  y  fecha_fin < hoy   (hoy = fecha en Europe/Madrid)
vencido = false   en cualquier otro caso (incluida fecha_fin = null)
```

- Es informativo: sirve para que el frontend avise de que "la fecha de fin prevista ya pasó" aunque la AEMPS
  siga marcando el problema como activo. Se calcula solo con las fechas, sea cual sea el `estado`.
- Se compara con `<` estricto: el último día del problema todavía no está vencido.
- Se puede ocultar con `GET /api/problemas?ocultar_vencidos=true` (por defecto no se oculta nada).
- Se calcula con la fecha de hoy que da Python en `Europe/Madrid` (no con `date('now')` de SQLite, que usa UTC y
  fallaría una hora alrededor de medianoche).

---

## 6. Resumen de la importación (para el backend, no es un endpoint)

Aunque no forma parte de la API, define lo que la API espera encontrar en la tabla:

| Campo de CIMA | Columna | Transformación |
|---|---|---|
| `cn` | `cn` | Texto, tal cual |
| `nombre` | `nombre` | Tal cual |
| `nombre` | `nombre_busqueda` | Minúsculas y sin tildes |
| `tipoProblemaSuministro` | `tipo_problema` | Entero, tal cual (sin nombres inventados) |
| `fini` | `fecha_inicio` | ms epoch a `YYYY-MM-DD` en `Europe/Madrid` |
| `ffin` | `fecha_fin` | Igual; `NULL` si no viene (nunca cadena vacía) |
| `observ` | `observaciones` | Tal cual (`''` si no viene) |
| `activo` | `activo` | `1` si `true`, `0` si `false`, tal cual viene (`1` si no viene) |
| (importación) | `en_origen`, `actualizado_en` | `1` y la hora UTC actual en cada fila importada |

Pasos: leer todas las páginas (`totalFilas` / `tamanioPagina`), poner `en_origen = 0` en toda la tabla y hacer el
upsert (`INSERT ... ON CONFLICT(cn) DO UPDATE`) de cada registro, todo dentro de una transacción para que, si algo
falla a mitad, la base no quede a medias.

---

## 7. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-11-13 | Primer contrato: tabla, `/api/salud`, `/api/problemas`, `/api/problemas/{cn}`, `/api/resumen`, `/api/chat` (reservado). |
| 1.1 | 2026-11-13 | Decisiones de la usuaria: nueva columna `activo` (copia de la AEMPS); `estado` se deriva de `activo` y `en_origen` (ya no de `fecha_fin`); nuevo campo `vencido` en listado y detalle; nuevo filtro `ocultar_vencidos` en `GET /api/problemas`; `fecha_fin` es `NULL` si no existe; `tipo_problema` entero tal cual. |
