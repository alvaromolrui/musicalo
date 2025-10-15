# 🧪 Guía de Testing - Musicalo v1.1.0

## ✨ Nueva Funcionalidad: Lenguaje Natural con IA

Esta versión añade **conversación natural** al bot de Telegram usando Gemini AI.

### Características
- 🤖 **Sin comandos**: Habla directamente con el bot
- 🎯 **Inteligente**: Entiende intención y contexto
- 📊 **Datos reales**: Usa tu historial de Last.fm/ListenBrainz
- 🎵 **Preciso**: Detecta referencias, cantidad y preferencias
- 🔄 **Variado**: Diferentes recomendaciones cada vez

### Ejemplos
```
✅ "recomiéndame un disco de algún grupo similar a Pink Floyd"
✅ "¿cuál fue mi última canción?"
✅ "dame 3 artistas parecidos a Queen"
✅ "¿qué he escuchado hoy?"
✅ "busca algo de rock en mi biblioteca"
```

---

## 🚀 Despliegue Rápido

### Paso 1: Construir Imagen (local o servidor con Docker)

```bash
# Cambiar a rama de testing
git checkout feature/ai-natural-language-interaction
git pull

# Construir imagen
docker build -t alvaromolrui/musicalo:testing .

# Subir a Docker Hub (opcional pero recomendado)
docker login
docker push alvaromolrui/musicalo:testing
```

### Paso 2: Probar en el Servidor

```bash
# Conectar al servidor
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# Editar docker-compose.yml
nano docker-compose.yml
```

Cambiar esta línea:
```yaml
image: alvaromolrui/musicalo:latest
```

Por:
```yaml
image: alvaromolrui/musicalo:testing
```

Guardar (Ctrl+O) y salir (Ctrl+X)

```bash
# Actualizar y reiniciar
docker-compose pull
docker-compose down
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### Para Volver a Producción

```bash
# Editar docker-compose.yml y cambiar de nuevo a:
  image: alvaromolrui/musicalo:latest

# Reiniciar
docker-compose down
docker-compose up -d
```

---

## ✅ Verificación

### 1. Verificar que está corriendo

```bash
docker ps | grep musicalo
```

Deberías ver el contenedor corriendo.

### 2. Probar la Nueva Funcionalidad

Abre tu bot en Telegram y prueba escribir **sin comandos**:

```
"recomiéndame un disco de Pink Floyd"
"¿cuál es mi canción favorita?"
"dame música rock"
"¿qué he escuchado hoy?"
```

El bot debería responder inteligentemente usando IA.

### 3. Ver Logs

```bash
# Logs en tiempo real
docker-compose logs -f

# Últimas 100 líneas
docker-compose logs --tail=100
```

En los logs verás:
```
🤖 Usuario escribió: recomiéndame un disco de Pink Floyd
🤖 Respuesta de IA: {"action": "recommend", "params": {...}}
🤖 Acción detectada: recommend con params: {...}
```

---

## 🛠️ Scripts Útiles

### build-testing.sh
Construye y sube la imagen de testing a Docker Hub.

```bash
./build-testing.sh
```

### docker-testing-*.sh
Scripts para gestionar el contenedor de testing cuando uses `docker-compose.testing.yml` (configuración avanzada).

```bash
./docker-testing-start.sh    # Iniciar
./docker-testing-stop.sh     # Detener  
./docker-testing-restart.sh  # Reiniciar
./docker-testing-logs.sh     # Ver logs
```

---

## 🐛 Troubleshooting

### El bot no responde a lenguaje natural

Verifica que la imagen sea `testing`:
```bash
docker ps | grep musicalo
# Debe mostrar: alvaromolrui/musicalo:testing
```

### Error de Gemini AI

Verifica la API key:
```bash
docker exec -it musicalo env | grep GEMINI_API_KEY
```

### Logs muestran errores

```bash
docker-compose logs --tail=200
```

Busca errores con "ERROR" o "Traceback".

---

## 📦 Configuración Avanzada (Opcional)

Si prefieres correr testing en **paralelo** con producción (puerto diferente):

1. Usa `docker-compose.testing.yml` (puerto 8001)
2. Crea un bot de Telegram separado
3. Usa `.env.testing` con token diferente

Ver archivo `docker-compose.testing.yml` para detalles.

---

## 🎯 Pasar a Producción

Cuando estés satisfecho con la versión de testing:

```bash
# 1. Hacer merge a main
git checkout main
git merge feature/ai-natural-language-interaction

# 2. Actualizar versión (se hará en próximo paso)

# 3. Construir imagen de producción
docker build -t alvaromolrui/musicalo:latest .
docker push alvaromolrui/musicalo:latest

# 4. Actualizar en servidor
# Cambiar docker-compose.yml de nuevo a:
  image: alvaromolrui/musicalo:latest

docker-compose pull
docker-compose down
docker-compose up -d
```

---

## 📚 Más Información

- **Código fuente**: https://github.com/alvaromolrui/musicalo
- **Rama testing**: `feature/ai-natural-language-interaction`
- **Documentación principal**: Ver `README.md`
