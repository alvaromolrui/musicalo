# Flujo de trabajo

Qué fichero tocar según lo que encuentres en sesión, y el ciclo real de publicación del repo. Las reglas de confirmación antes de acciones destructivas/irreversibles ya viven en las instrucciones del harness — aquí solo el mapa de dónde documentar cada cosa.

## Principio general

El código es la fuente de verdad del comportamiento; estos seis ficheros son la fuente de verdad de todo lo que el código *no* explica por sí solo (el porqué, las convenciones, los términos, los errores ya vistos). Si en una sesión descubres o cambias algo de eso, refléjalo aquí en el mismo commit — no lo dejes solo en la conversación.

## Qué fichero tocar según lo que encuentres

| Encuentras... | Documéntalo en |
|---|---|
| Un componente, servicio o flujo de datos nuevo, o un cambio de cómo se comunican dos partes del sistema | [arquitectura.md](arquitectura.md) |
| Un patrón de nombrado, formato de commit, o convención de código que se repite y no estaba escrita | [convenciones.md](convenciones.md) |
| Una decisión de diseño importante (cambio de stack, sustitución de un componente, migración) con contexto/opciones/consecuencias | [decisiones/README.md](decisiones/README.md), nueva entrada en la tabla + documento propio si el contexto lo justifica |
| Un bug real ya diagnosticado y corregido, o un falso positivo que ya se investigó | [errores-conocidos.md](errores-conocidos.md) — usa el hash del commit del fix como referencia, no dupliques el detalle |
| Un término, nombre propio o sigla interna que no se explica por sí sola | [glosario.md](glosario.md) |
| Un hallazgo que no encaja en ninguno de los anteriores pero es relevante para el usuario final | [README.md](README.md) (funcionalidades, instalación, configuración) |

No son excluyentes: un mismo commit de fix suele tocar dos sitios (el código + una fila en `errores-conocidos.md`); un cambio de arquitectura grande suele tocar `arquitectura.md` y una entrada nueva en `decisiones/`.

## Ciclo real de publicación

1. Commit en `main` (no hay evidencia de flujo de PR/review en el historial — ver [convenciones.md](convenciones.md#ramas); las dos ramas `feature/*` remotas no parecen estar activas, confírmalo antes de asumir lo contrario).
2. [.github/workflows/docker-publish.yml](.github/workflows/docker-publish.yml) reconstruye automáticamente la imagen Docker cuyo directorio cambió (`backend/`+ficheros raíz relevantes, o `frontend/`) y la publica en Docker Hub con el tag `:main`.
3. Un tag `vX.Y.Z` (coincidiendo con el contenido de [VERSION](VERSION)) publica además el tag `:latest` de ambas imágenes — es el paso de "release" real, no un merge a `main` cualquiera.
4. No hay pipeline de tests automatizado en CI — [test_playlist_creation.py](test_playlist_creation.py) existe como script suelto, ejecútalo manualmente si tocas el flujo de creación de playlists antes de dar un cambio por verificado.

## Al diagnosticar un bug en producción

Patrón ya consolidado en varios commits recientes (ver [errores-conocidos.md](errores-conocidos.md)):

1. Reproduce o al menos describe el síntoma real observado (no una suposición de causa) — el propio mensaje de commit lo recoge como "Encontrado en producción: ...".
2. Encuentra la causa raíz antes de tocar código — varios fixes de este repo distinguían explícitamente entre una hipótesis inicial descartada y la causa real confirmada.
3. Si el fix no cierra el problema del todo (una parte queda sin garantía estructural), dilo explícitamente en el propio commit en vez de dar a entender que quedó resuelto.
4. Añade la fila correspondiente en [errores-conocidos.md](errores-conocidos.md) en el mismo commit.

## Al cerrar un proyecto de decisión

Cuando una entrada de [decisiones/](decisiones/README.md) llega a un estado final:

1. Márcala como completada en su propio documento (si tiene uno propio) o directamente en la tabla del índice.
2. Si dejó un patrón de bug reutilizable, añade también una fila en [errores-conocidos.md](errores-conocidos.md).
3. No la sigas editando como si fuera documentación viva del estado actual — eso va en [arquitectura.md](arquitectura.md); la entrada de `decisiones/` se congela como registro histórico del *por qué*.
