[README_CAMBIOS_SICE.md](https://github.com/user-attachments/files/29822676/README_CAMBIOS_SICE.md)
# Cambios propuestos para App_SICE_EConitua

Archivo principal generado:

- `sice_google.py`
- `assets/encabezado_udg_plus.png`

## Objetivo

Convertir la app en un cargador de base maestra para Educacion Continua que pueda:

- Leer la base actual de Google Sheets.
- Cargar reportes descargados del SII.
- Cargar bases de matriculados o grupos cerrados con encabezados distintos.
- Cargar opcionalmente la cartelera 2026 para asignar fecha de inicio por programa.
- Homologar columnas al formato de la base maestra.
- Generar llaves de control por participante y curso.
- Actualizar Google Sheets sin duplicar registros ya existentes.

## Cambios principales

- Se reemplazo la llave anterior `Codigo EC + Programa + Mes` porque no identifica a una persona.
- Se agregaron llaves:
  - `Llave participante`: usa CURP, correo o nombre/telefono.
  - `Llave curso`: usa Clave Curso, Clave Grupo o Programa + Fecha. El Codigo EC se conserva como dato del SII, pero ya no se usa como si fuera la identidad del curso.
  - `Llave registro`: combina participante + curso.
- El upsert ahora compara varias pistas de identidad por persona, no solo la llave visible. Esto permite cruzar una fila del SII con CURP y correo contra una fila de matriculados que solo trae correo.
- Cuando detecta que una fila nueva corresponde a una persona ya existente, fusiona la informacion: conserva los campos ya llenos y completa solamente los campos vacios. Por ejemplo, si el SII ya tenia `Codigo EC` y Matriculados trae programa o telefono, la fila final se queda con ambos datos sin duplicar a la persona.
- Si una fila nueva podria coincidir con varias filas existentes de la misma persona, se omite para revision en lugar de unirla automaticamente al curso equivocado.
- Se agrego una vista institucional con encabezado UDG+, paleta azul institucional, metricas tipo tablero, botones y sidebar con acabado mas sobrio.
- Se agrego homologacion de columnas para archivos de matriculados:
  - `Fecha registro` -> `Fecha de Inscripción`
  - `Apellido paterno` -> `Paterno`
  - `Correo electrónico` -> `Correo`
  - `Ciudad` -> `Municipio`
  - `Último grado de estudios` -> `Grado Estudios`
  - entre otras.
- Se agrego conversion de fechas de Excel serial a `YYYY-MM-DD`.
- Se agrego limpieza de telefonos y codigos que llegan como numeros o notacion cientifica.
- Se agrego validacion visual de registros por revisar.
- Se agrego descarga CSV del archivo normalizado antes de aplicar cambios.
- Se conservan filas antiguas sin llave, pero los nuevos registros sin llave se omiten para evitar duplicados peligrosos.

## Pendiente operativo

La integracion de GitHub permitio leer el repositorio, pero no crear rama ni escribir cambios (`403 Resource not accessible by integration`). Para aplicar esto al repo, reemplaza el archivo `sice_google.py` del repositorio con el generado en esta carpeta.
