# 🚀 DESPLIEGUE A PRODUCCIÓN - v1.1.0-alpha

## ✅ TODO LISTO EN GITHUB

```
✅ Rama: main
✅ Versión: 1.1.0-alpha
✅ Tag: v1.1.0-alpha
✅ Código optimizado y limpio
✅ Documentación completa
```

---

## 🐳 CONSTRUIR IMAGEN `latest` PARA PRODUCCIÓN

### En el Servidor (Método Recomendado):

```bash
# 1. Conectar y actualizar
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# 2. Cambiar a main y actualizar
git checkout main
git pull

# 3. Construir imagen
docker build -t alvaromolrui/musicalo:1.1.0-alpha .

# 4. Etiquetar como latest
docker tag alvaromolrui/musicalo:1.1.0-alpha alvaromolrui/musicalo:latest

# 5. Login en Docker Hub
docker login

# 6. Subir a Docker Hub
docker push alvaromolrui/musicalo:1.1.0-alpha
docker push alvaromolrui/musicalo:latest

# 7. Verificar que docker-compose.yml tiene:
cat docker-compose.yml | grep image
# Debe mostrar: image: alvaromolrui/musicalo:latest

# 8. Actualizar producción
docker-compose pull
docker-compose down
docker-compose up -d

# 9. Verificar logs
docker-compose logs -f
```

### Desde Local (cuando tengas Docker Desktop):

```bash
# 1. Inicia Docker Desktop

# 2. Actualizar código
git checkout main
git pull

# 3. Usar el script
./build-and-push.sh 1.1.0-alpha

# Esto sube automáticamente:
# - alvaromolrui/musicalo:1.1.0-alpha
# - alvaromolrui/musicalo:latest
```

---

## ✨ VERIFICACIÓN EN PRODUCCIÓN

### 1. Verificar Imagen

```bash
docker ps | grep musicalo
```

Debe mostrar:
```
CONTAINER ID   IMAGE                         STATUS
xxx            alvaromolrui/musicalo:latest  Up X minutes
```

### 2. Ver Logs

```bash
docker-compose logs --tail=50
```

Debe mostrar:
```
✅ Usando Last.fm para datos de escucha
INFO - Iniciando bot en modo polling...
INFO - Application started
```

### 3. Probar en Telegram

**Lenguaje Natural (NUEVO):**
```
"recomiéndame un disco de Pink Floyd"
"¿cuál fue mi última canción?"
"dame 3 artistas parecidos a Queen"
```

**Comandos Tradicionales:**
```
/start
/recommend
/stats
```

Ambos métodos deben funcionar correctamente.

---

## 🎯 IMÁGENES DISPONIBLES EN DOCKER HUB

Después del despliegue tendrás:

```
alvaromolrui/musicalo:latest        → Producción (v1.1.0-alpha)
alvaromolrui/musicalo:1.1.0-alpha   → Versión específica
alvaromolrui/musicalo:testing       → Testing (mismo código)
```

---

## 📊 CHANGELOG v1.1.0-alpha

### Nuevas Características
- 🤖 Conversación natural sin comandos
- 🎯 Interpretación inteligente con IA
- 📊 Respuestas contextuales con datos reales
- 🔄 Variedad en recomendaciones
- 💬 Sistema conversacional completo

### Mejoras
- Parseo robusto de argumentos
- Detección de referencias específicas
- Respeto de cantidad solicitada (singular vs plural)
- Variedad garantizada (randomización)
- Código optimizado (-1221 líneas redundantes)

### Eliminado
- Watchtower (simplificación)
- 9 archivos redundantes de testing
- Imports duplicados

Ver `CHANGELOG.md` para detalles completos.

---

## 🆘 TROUBLESHOOTING

### Error al construir imagen
```bash
# Verificar Docker
docker --version
docker ps
```

### Error al subir a Docker Hub
```bash
# Login de nuevo
docker login
```

### Bot no responde en producción
```bash
# Ver logs completos
docker-compose logs --tail=200

# Verificar variables de entorno
docker exec -it musicalo env | grep -E "TELEGRAM|GEMINI|LASTFM"
```

---

## 🎉 ¡Listo!

Una vez completados los pasos, **Musicalo v1.1.0-alpha** estará en producción con todas las nuevas características de IA conversacional.

**¡Disfruta de tu bot inteligente!** 🎵🤖✨

