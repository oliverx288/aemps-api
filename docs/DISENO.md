# Diseño UX/UI - Problemas de suministro de medicamentos (AEMPS)

Este documento define **cómo se ve y cómo se comporta** la web antes de programarla. Cada decisión lleva una línea de justificación ("Por qué") para que se entienda el criterio y se pueda aplicar a casos nuevos.

Los valores concretos (colores, tamaños, espacios) están en `frontend/tokens.css`. Este documento explica el porqué; el CSS tiene el valor.

---

## 1. Principios

| Principio | Por qué |
|---|---|
| Accesibilidad primero (WCAG 2.1 AA como mínimo) | La usará gente con poca experiencia digital, mayores y personas con baja visión; si funciona para ellas, funciona para todos. |
| Una tarea por pantalla | Menos elementos = menos dudas. |
| Lenguaje llano, sin jerga técnica | Se escribe "Problema de suministro", no "incidencia de desabastecimiento" ni "NRegistro" sin explicar. |
| Nunca comunicar algo solo con color | Hay personas con daltonismo; el estado siempre lleva texto e icono además de color. |
| Que sea evidente que los datos vienen de la AEMPS | Es información sanitaria: la gente debe saber la fuente y la fecha de actualización. |
| HTML semántico antes que "adornos" | Un `<button>` o `<a>` real ya trae teclado y lector de pantalla gratis. |

---

## 2. Mapa de pantallas y flujo

```
 [Inicio / Buscador] --buscar--> [Listado de resultados] --elegir--> [Detalle]
        |                              ^                                |
        |                              |------ "Volver al listado" -----|
        +--(fase posterior)--> [Asistente (chatbot)]
```

- **Inicio y listado comparten página**: el buscador está arriba y los resultados debajo. Por qué: menos saltos entre pantallas y la persona ve de inmediato que su búsqueda ha funcionado.
- **Detalle** es una vista propia con su propia dirección (por ejemplo `#/problema/12345`). Por qué: así se puede compartir el enlace y el botón "Atrás" del navegador funciona como espera la gente.
- **Asistente** se pospone, pero se reserva su hueco en la navegación (apartado 8.3).

Flujo principal ("quiero saber si falta mi medicamento"):

1. Entra y ve un campo grande: "Escribe el nombre del medicamento".
2. Escribe y pulsa **Buscar** (o Intro).
3. Ve la lista con el estado de cada problema (Activo / Resuelto) y fechas.
4. Pulsa una tarjeta y ve el detalle: qué pasa, desde cuándo, hasta cuándo, observaciones.
5. Pulsa **Volver al listado** y conserva su búsqueda.

---

## 3. Estructura común de página

```
+----------------------------------------------------------+
| [Saltar al contenido]  (invisible hasta recibir foco)    |
+----------------------------------------------------------+
| CABECERA                                                 |
|  Problemas de suministro de medicamentos                 |
|  Datos de la AEMPS | [Buscador] [Asistente]              |
+----------------------------------------------------------+
| <main id="contenido">                                    |
|   ... contenido de la vista ...                          |
+----------------------------------------------------------+
| PIE                                                      |
|  Fuente: Agencia Española de Medicamentos y Productos    |
|  Sanitarios (AEMPS). Datos actualizados el 12/11/2026.   |
|  Esta web es informativa y no sustituye a su médico o    |
|  farmacéutico.                                           |
+----------------------------------------------------------+
```

Decisiones:
- **Enlace "Saltar al contenido"**: permite a quien navega con teclado evitar repetir la cabecera en cada página.
- **Landmarks** `<header>`, `<nav aria-label="Principal">`, `<main>`, `<footer>`: los lectores de pantalla permiten saltar entre ellos.
- **Aviso en el pie "no sustituye a su médico o farmacéutico"**: es información de salud y hay que evitar que se use como consejo médico.
- **Fecha de actualización visible**: la confianza en un dato sanitario depende de saber cuán reciente es.
- **Ancho máximo del contenido 960 px** (`--ancho-contenido`): líneas muy largas se leen mal en pantallas grandes.

---

## 4. Paleta de color

Todos los pares se han medido con la fórmula de contraste de WCAG. Mínimos exigidos: **4,5:1** para texto normal, **3:1** para texto grande (24 px o 19 px en negrita) y para bordes e iconos de controles.

### 4.1 Tema claro

| Token | Valor | Uso | Contraste | Por qué |
|---|---|---|---|---|
| `--color-fondo` | `#FFFFFF` | Fondo de página | - | Máximo contraste y aspecto limpio. |
| `--color-superficie` | `#F3F6FA` | Tarjetas, cabecera | - | Gris azulado muy suave: separa zonas sin bordes pesados. |
| `--color-texto` | `#1A2332` | Texto principal | 15,8:1 | Casi negro pero no puro: cansa menos que `#000` sobre blanco. |
| `--color-texto-suave` | `#4A5568` | Fechas, ayudas | 7,5:1 | Pasa AAA (7:1); un gris más claro sería tentador pero ilegible. |
| `--color-borde` | `#6B7A8C` | Borde de campos y botones | 4,4:1 | Los controles necesitan 3:1 mínimo para distinguirse del fondo. |
| `--color-primario` | `#0B5CAD` | Enlaces, botón principal | 6,7:1 | Azul: se asocia a "pulsable" y a lo sanitario/institucional. |
| `--color-primario-hover` | `#084A8C` | Hover | 8,9:1 | Más oscuro = respuesta visible al acercar el ratón. |

### 4.2 Estados (siempre fondo + texto + icono)

| Estado | Fondo | Texto | Contraste | Icono y texto visible |
|---|---|---|---|---|
| Activo (hay problema ahora) | `#FDECEC` | `#9B1C1C` | 7,1:1 | "! Activo" |
| Resuelto | `#E6F4E7` | `#1B5E20` | 6,9:1 | "✓ Resuelto" |
| Aviso | `#FFF3D6` | `#7A4A00` | 6,8:1 | "Aviso:" |
| Información | `#E5F0FB` | `#0B4F8A` | 7,3:1 | "Información:" |
| Error | `#FDECEC` | `#9B1C1C` | 7,1:1 | "Error:" |

Por qué rojo/verde **y además** palabra e icono: rojo y verde son justo los colores que se confunden con el daltonismo más común; la palabra y el símbolo garantizan que el significado llega siempre. Por qué rojo oscuro y no rojo "chillón": el rojo brillante sobre fondo claro no llega a 4,5:1.

### 4.3 Tema oscuro

Se activa solo con la preferencia del sistema (`prefers-color-scheme: dark`). Todos los pares siguen superando AA (ver comentarios en `tokens.css`: entre 5,3:1 y 15,3:1).
Por qué solo automático y sin botón: menos controles, menos código, y respeta lo que la persona ya eligió en su móvil u ordenador. Por qué incluirlo: lo necesita quien tiene sensibilidad a la luz y es muy barato con variables CSS.
Detalle: en oscuro el botón primario usa texto oscuro sobre azul claro (`#7DB8F5`), no texto blanco, para mantener 8,6:1.

---

## 5. Tipografía

| Decisión | Valor | Por qué |
|---|---|---|
| Familia | Fuentes del sistema (`system-ui`...) | Cero descargas, carga instantánea, y son las fuentes a las que cada persona ya está acostumbrada. Sin dependencia de servidores externos (privacidad). |
| Tamaño base | **18 px** (`1.125rem`) | Mayor que los 16 px habituales: mejora la lectura para gente mayor o con baja visión. |
| Unidades | `rem`, nunca `px` en texto | Si la persona agranda la letra en su navegador, la web respeta su elección. |
| Escala | 14 / 16 / 18 / 20 / 24 / 32 px | Pocos tamaños bien diferenciados; evita decisiones arbitrarias. |
| Texto mínimo | 14 px, solo etiquetas cortas | Nada de lectura larga por debajo de 16 px. |
| Interlineado | 1,6 en texto, 1,25 en títulos | Espacio entre líneas que facilita no perderse al leer. |
| Ancho de línea | máx. 65 caracteres (`--ancho-lectura`) | Es el rango donde la lectura es más cómoda. |
| Pesos | 400 normal, 600 semi, 700 negrita | Jerarquía con peso además de tamaño. |
| Códigos (CN) | Fuente monoespaciada | Se distinguen bien los dígitos. |
| Alineación | A la izquierda; nunca justificado | El texto justificado crea espacios irregulares que dificultan la lectura. |

Jerarquía de títulos: un único `<h1>` por vista (32 px), `<h2>` para secciones (24 px), `<h3>` para tarjetas (20 px). No saltar niveles. Por qué: es cómo los lectores de pantalla construyen el "índice" de la página.

---

## 6. Espaciado y forma

- **Escala de 4 px** (4, 8, 12, 16, 24, 32, 48, 64 = `--espacio-1` a `--espacio-8`). Por qué: pocos valores repetidos dan un aspecto ordenado y evitan el "porque sí 13 px".
- **Objetivo táctil mínimo 44 x 44 px** (`--objetivo-minimo`). Por qué: dedos grandes o temblor de pulso necesitan blancos amplios (WCAG recomienda 44).
- **Separación entre tarjetas 16 px**, entre secciones 32-48 px. Por qué: agrupar visualmente lo que va junto (ley de proximidad).
- **Radios**: 8 px en campos y botones, 12 px en tarjetas, píldora en etiquetas de estado. Por qué: esquinas suaves se perciben amables; mantener pocos radios da coherencia.
- **Bordes de 2 px** en controles. Por qué: 1 px desaparece con baja visión.
- **Sombras muy suaves**: solo las tarjetas. Por qué: la jerarquía no debe depender de sombras (se pierden en modo de alto contraste); el borde ya delimita.

---

## 7. Componentes

### 7.1 Botón

- **Primario** ("Buscar", "Reintentar"): fondo `--color-primario`, texto `--color-sobre-primario`, alto mínimo 44 px, texto 18 px en semi-negrita.
- **Secundario** ("Volver al listado", "Limpiar"): fondo transparente, borde 2 px `--color-primario`, texto `--color-primario`.
- Estados: normal, hover (más oscuro), foco (ver 10.2), activo (`translateY(1px)`), deshabilitado (borde y texto grises con `aria-disabled`).
- Por qué: un único primario por vista deja claro "qué hago ahora"; las etiquetas son verbos ("Buscar"), no "Aceptar" ni "OK".
- Se usa siempre el elemento `<button>` (acción) o `<a>` (navegación), nunca un `<div>` clicable.

### 7.2 Campo de búsqueda

```
Buscar un medicamento              <- <label> visible, 18 px, negrita
Escriba el nombre o parte del nombre. Ejemplo: amoxicilina   <- ayuda, 16 px, gris
[______________________________] [ Buscar ]
```

- `<label for>` **visible** siempre (no solo "placeholder"). Por qué: el placeholder desaparece al escribir y suele tener bajo contraste.
- Texto de ayuda enlazado con `aria-describedby`.
- `type="search"`, `autocomplete="off"`, `name` descriptivo.
- Alto mínimo 48 px, borde 2 px `--color-borde`.
- Se envía con Intro (usar `<form>`). Por qué: es lo que hace instintivamente la gente.
- Filtro opcional bajo el campo: grupo de botones de opción (`<fieldset>` + `<legend>"Estado"`) con "Todos / Activos / Resueltos". Por qué: radio buttons nativos son accesibles sin esfuerzo y se entienden mejor que un desplegable.

### 7.3 Etiqueta de estado (badge)

`[! Activo]` rojo oscuro sobre rojo muy claro; `[✓ Resuelto]` verde oscuro sobre verde muy claro. Forma de píldora, 16 px, semi-negrita. El icono es decorativo (`aria-hidden="true"`) porque la palabra ya dice el estado. Por qué: ver 4.2.

### 7.4 Tarjeta de resultado

```
+--------------------------------------------------------+
| AMOXICILINA CINFA 500 MG CAPSULAS        [! Activo]    |  <- h3 + enlace al detalle
| Código nacional: 123456                                |
| Desde: 03/09/2026     Hasta: sin fecha prevista        |
| Observaciones: Problema de fabricación...  (recortado) |
|                                  Ver detalle >          |
+--------------------------------------------------------+
```

- Toda la tarjeta es clicable **pero** el enlace real es el título (`<a>` dentro del `<h3>`) y se extiende con CSS. Por qué: un solo punto de foco por tarjeta (menos tabulaciones) y el lector de pantalla lee el nombre del medicamento como enlace.
- Fechas en formato **dd/mm/aaaa** y con etiqueta ("Desde", "Hasta"). Por qué: es el formato en España; sin etiqueta una fecha suelta no se entiende.
- Si no hay fecha de fin: **"Sin fecha prevista"**. Por qué: un campo vacío parece un fallo.
- Observaciones recortadas a 2 líneas; el texto completo está en el detalle.

### 7.5 Lista de resultados

`<ul>` de tarjetas con un contador encima: **"12 problemas encontrados para «amoxicilina»"**, con `aria-live="polite"` (el lector lo anuncia al buscar). Ordenadas por defecto: activos primero, luego más reciente. Por qué: lo urgente va arriba.
Paginación (si hay muchos): botones "Anterior" y "Siguiente" con "Página 2 de 5". Por qué: más claro que números sueltos y más fácil de pulsar.

### 7.6 Mensajes (aviso, error, información)

Caja con borde izquierdo grueso, icono, texto y, si procede, un botón. Rol `role="alert"` para errores (se anuncia ya), `role="status"` para informativos.

### 7.7 Indicador de carga

Círculo girando **más** el texto "Cargando resultados..." y `aria-busy="true"` sobre la zona. Con `prefers-reduced-motion` se sustituye el giro por texto fijo. Por qué: una animación sola no dice qué pasa y puede marear.

### 7.8 Enlace "Volver"

`<a>` con flecha y texto: "< Volver al listado". Por qué: complementa el botón "Atrás" del navegador, que algunas personas ni saben que existe.

---

## 8. Vistas

### 8.1 Inicio y buscador (con listado)

```
CABECERA
-------------------------------------------------
h1  ¿Falta algún medicamento?
p   Consulte los problemas de suministro
    comunicados por la AEMPS.

[Buscar un medicamento             ]
[ ejemplo: amoxicilina  ] [ Buscar ]
Estado:  (o) Todos  ( ) Activos  ( ) Resueltos
-------------------------------------------------
h2  Resultados
p   12 problemas encontrados para «amoxicilina»
[tarjeta]
[tarjeta]
[tarjeta]
[ Anterior ]  Página 1 de 2  [ Siguiente ]
-------------------------------------------------
PIE
```

Por qué un título en forma de pregunta: es la duda real de la persona y le dice enseguida para qué sirve la web.

### 8.2 Detalle de un problema

```
< Volver al listado

h1  AMOXICILINA CINFA 500 MG CAPSULAS
    [! Activo]

h2  Qué ocurre
p   Texto de observaciones completo...

h2  Fechas
dl  Inicio del problema      03/09/2026
    Fin previsto             Sin fecha prevista
    Última actualización     12/11/2026

h2  Datos del medicamento
dl  Código nacional          123456
    Presentación             ...

Aviso: Consulte a su farmacéutico por alternativas.
Fuente: AEMPS  [ Ver en la web de la AEMPS ]  (se abre en pestaña nueva, indicado en el texto)
```

- **Lista de definiciones (`<dl>`)** para pares etiqueta-valor: es la semántica correcta y los lectores la anuncian bien.
- Estado en el encabezado: es lo primero que se quiere saber.
- Enlace externo con texto "(se abre en una pestaña nueva)" visible o `aria-label` equivalente. Por qué: no sorprender.

### 8.3 Asistente (chatbot) - fase posterior, solo reservado

```
h1  Asistente
p   Respondo solo con datos de esta base de datos de
    problemas de suministro. No doy consejo médico.

[ historial de mensajes  (role="log", aria-live="polite") ]
   Usted:      ¿Hay problemas con el ibuprofeno?
   Asistente:  Sí, he encontrado 2 problemas...

Escriba su pregunta
[______________________________] [ Enviar ]
Ejemplos: "¿Está activo el problema de X?"
```

Reglas ya decididas: mensajes del usuario y del asistente distinguidos por **nombre en texto** (no solo por color o lado); aviso fijo de límites; sugerencias de ejemplo para quien no sabe qué preguntar; estado "Escribiendo..." textual; el asistente responde "No tengo datos sobre eso" cuando no hay información.

---

## 9. Estados (todas las vistas de datos)

Toda zona que carga datos debe tener estos cinco estados diseñados; nunca una pantalla en blanco.

| Estado | Qué se muestra | Texto exacto | Por qué |
|---|---|---|---|
| **Inicial / vacío** (aún no ha buscado) | Mensaje informativo con ejemplos | "Escriba el nombre de un medicamento para empezar. Por ejemplo: amoxicilina, ibuprofeno." | Evita el vacío intimidante y enseña qué escribir. |
| **Cargando** | Indicador + texto, `aria-busy` | "Cargando resultados..." | Confirma que la acción se registró. |
| **Sin resultados** | Mensaje informativo con consejos y botón "Ver todos los problemas" | "No hemos encontrado problemas de suministro para «xyz». Compruebe que está bien escrito o pruebe con una parte del nombre. Que no aparezca no garantiza que no haya problemas: consulte a su farmacéutico." | No es un error: es un resultado válido. Y evita falsa tranquilidad en un tema de salud. |
| **Error de red / servidor** | Mensaje de error con botón "Intentar de nuevo" | "No hemos podido obtener los datos. Compruebe su conexión a internet e inténtelo de nuevo en unos minutos." | Dice qué pasó, qué hacer y ofrece la acción en el mismo sitio. Sin códigos técnicos (el detalle va a la consola). |
| **Error de entrada** (campo vacío) | Mensaje junto al campo, foco al campo | "Escriba al menos 3 letras del nombre del medicamento." | Explica cómo corregirlo, no solo que está mal. |
| **No encontrado** (detalle inexistente) | Mensaje + enlace "Volver al listado" | "No encontramos este problema de suministro. Puede que haya sido retirado." | Salida clara, no callejón sin salida. |
| **Datos desactualizados** (opcional) | Aviso amarillo | "Los datos pueden no estar actualizados. Última actualización: 12/11/2026." | Transparencia en información sanitaria. |

Normas de estilo de los mensajes:
- Se habla de **usted** y en frases cortas. Por qué: tono respetuoso para público amplio.
- Sin tecnicismos ("error 500", "timeout", "JSON").
- Los errores nunca culpan a la persona.
- Al mostrar error o resultados nuevos, no se mueve el foco de forma inesperada, salvo el error de entrada (foco al campo).

---

## 10. Accesibilidad (checklist obligatoria)

### 10.1 Contraste
- Texto normal >= 4,5:1; texto grande y componentes UI >= 3:1. Todos los tokens ya cumplen (apartado 4).
- Prohibido usar el color como único indicador (estado, error, enlace). Los enlaces dentro de texto van **subrayados**.

### 10.2 Foco visible
- Contorno de 3 px (`--foco-grosor`) en `--color-foco` con separación de 2 px, más halo exterior del color de fondo para verse sobre cualquier superficie.
- Se usa `:focus-visible`: se ve con teclado y no molesta con ratón.
- **Nunca** `outline: none` sin sustituto.
- Por qué: quien navega con teclado necesita saber siempre dónde está.

### 10.3 Teclado
- Todo se puede hacer con teclado: Tab/Mayús+Tab navegan, Intro activa enlaces y botones, Espacio activa botones.
- El orden de tabulación sigue el orden visual (no usar `tabindex` positivo).
- Al cambiar de vista (listado a detalle), el foco se mueve al `<h1>` de la nueva vista (con `tabindex="-1"`). Por qué: sin esto, el lector de pantalla no sabe que la página cambió.
- Sin trampas de teclado; no hay menús que se abran solo con hover.

### 10.4 Etiquetas y semántica
- Todo campo con `<label>` visible; botones con texto (si solo hay icono, `aria-label`).
- Un `<h1>` por vista; títulos sin saltos de nivel.
- `lang="es"` en `<html>`; `<title>` distinto por vista ("Detalle: AMOXICILINA - Problemas de suministro").
- Zonas dinámicas con `aria-live`/`role="status"`/`role="alert"` según urgencia.
- Iconos decorativos con `aria-hidden="true"`.
- Texto de enlace descriptivo: "Ver detalle de AMOXICILINA", no "Pulse aquí". (Se puede conseguir con texto visualmente oculto.)

### 10.5 Tamaño y zoom
- Todo en `rem`; la página debe funcionar con zoom del 200 % sin perder contenido ni scroll horizontal (WCAG 1.4.4 / 1.4.10).
- Meta viewport sin bloquear el zoom (nunca `user-scalable=no`).

### 10.6 Movimiento y preferencias
- `prefers-reduced-motion`: sin animaciones (token `--transicion: 0ms`).
- `prefers-color-scheme`: tema oscuro automático.
- No hay contenido que parpadee ni se mueva solo.

### 10.7 Comprobación antes de dar una vista por terminada
1. Recorrerla solo con teclado.
2. Zoom al 200 %.
3. Revisar con Lighthouse (pestaña Accessibility) o la extensión axe DevTools.
4. Probar con un lector de pantalla (VoiceOver en Mac: Cmd+F5) al menos una vez.

---

## 11. Responsive (diseño adaptable)

Enfoque **mobile-first**: se escribe el CSS para móvil y se añaden `@media (min-width: ...)` para pantallas mayores. Por qué: gran parte de la gente consultará desde el móvil, y es más fácil "ampliar" que "recortar".

| Ancho | Nombre | Comportamiento |
|---|---|---|
| < 640 px | Móvil | Una columna. Margen lateral 16 px. Buscador: campo a todo el ancho y botón **debajo**, también a todo el ancho. Filtro de estado en vertical. Tarjetas a todo el ancho. Navegación de la cabecera en línea, sin menú hamburguesa (solo 2 enlaces). |
| 640 - 1023 px | Tableta | Campo y botón **en la misma fila**. Margen 24 px. Tarjetas en una columna (más fácil de escanear con las fechas). |
| >= 1024 px | Escritorio | Contenido centrado, máx. 960 px. Margen 32 px. Detalle en dos columnas ("Qué ocurre" / "Datos del medicamento") solo si cabe sin apretar. |

Notas:
- Sin menú hamburguesa: esconder la navegación obliga a un clic extra y mucha gente mayor no reconoce el icono.
- Los puntos de corte van en `rem` (40 rem y 64 rem) para que también respondan si la persona agranda la letra. Las variables CSS no funcionan dentro de `@media`, por eso `tokens.css` solo los documenta.
- Las tarjetas apilan el estado debajo del título en móvil y a su derecha en pantallas anchas.
- Sin tablas para el listado; si en el futuro hay tabla, se convierte en tarjetas en móvil.

---

## 12. Textos clave en español (catálogo)

| Lugar | Texto |
|---|---|
| Título de la web | Problemas de suministro de medicamentos |
| Subtítulo | Información oficial de la Agencia Española de Medicamentos y Productos Sanitarios (AEMPS) |
| Etiqueta del buscador | Buscar un medicamento |
| Ayuda | Escriba el nombre o parte del nombre. Ejemplo: amoxicilina |
| Botón | Buscar |
| Filtro | Estado: Todos / Activos / Resueltos |
| Badge | Activo / Resuelto |
| Contador | 12 problemas encontrados / 1 problema encontrado |
| Fecha inicio / fin | Desde / Hasta (en detalle: "Inicio del problema" / "Fin previsto") |
| Sin fecha de fin | Sin fecha prevista |
| Enlace al detalle | Ver detalle |
| Volver | Volver al listado |
| Reintentar | Intentar de nuevo |
| Pie | Fuente: AEMPS. Esta web es informativa y no sustituye el consejo de su médico o farmacéutico. |

Por qué un catálogo: reutilizar siempre la misma palabra para lo mismo (nunca "Buscar" y a veces "Consultar") reduce la confusión.

---

## 13. Qué NO hacer (resumen)

- No usar colores nuevos fuera de `tokens.css`.
- No usar `placeholder` como etiqueta.
- No quitar el contorno de foco.
- No usar texto menor de 16 px en lectura.
- No comunicar el estado solo con color.
- No usar carruseles, ventanas emergentes ni desplegables personalizados: los nativos de HTML ya son accesibles.
- No mostrar mensajes técnicos al usuario.

---

## 14. Entrega para la fase de frontend

- `frontend/tokens.css` se carga **antes** que cualquier otro CSS.
- Siguiente paso (otra fase, no incluida aquí): `frontend/index.html`, `css/estilos.css` y JavaScript siguiendo este documento.
- Contrato esperado de datos: el listado necesita al menos nombre del medicamento, código nacional, estado (activo/resuelto), fecha de inicio, fecha de fin (opcional) y observaciones. Si la API no los ofrece así, se ajusta con el agente de backend, no inventando datos en la interfaz.
