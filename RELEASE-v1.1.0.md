# 🚀 Release v1.1.0-alpha - Instrucciones de Despliegue

## ✅ Estado Actual

- ✅ Merge a main completado
- ✅ Tag v1.1.0-alpha creado
- ✅ Código pusheado a GitHub
- ✅ Versión actualizada en archivos

## 📦 Siguiente Paso: Construir Imagen de Producción

### Opción 1: Desde tu Máquina Local (si tienes Docker Desktop)

```bash
# 1. Asegúrate de estar en main
git checkout main
git pull

# 2. Inicia Docker Desktop

# 3. Construir y subir imagen
./build-and-push.sh 1.1.0

# Esto creará:
# - alvaromolrui/musicalo:1.1.0
# - alvaromolrui/musicalo:latest
```

### Opción 2: Desde el Servidor (Recomendado)

```bash
# 1. Conectar al servidor
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# 2. Actualizar a main
git checkout main
git pull

# 3. Construir imagen
docker build -t alvaromolrui/musicalo:1.1.0 .
docker tag alvaromolrui/musicalo:1.1.0 alvaromolrui/musicalo:latest

# 4. Login y subir
docker login
docker push alvaromolrui/musicalo:1.1.0
docker push alvaromolrui/musicalo:latest

# 5. Actualizar en producción
# Asegúrate de que docker-compose.yml tenga:
#   image: alvaromolrui/musicalo:latest

docker-compose pull
docker-compose down
docker-compose up -d

# 6. Ver logs
docker-compose logs -f
```

### Opción 3: Sin Construir (Usar Imagen Testing)

Si la imagen testing funcionó bien, puedes etiquetarla como latest:

```bash
# En el servidor
docker pull alvaromolrui/musicalo:testing
docker tag alvaromolrui/musicalo:testing alvaromolrui/musicalo:1.1.0
docker tag alvaromolrui/musicalo:testing alvaromolrui/musicalo:latest

docker login
docker push alvaromolrui/musicalo:1.1.0
docker push alvaromolrui/musicalo:latest

# Actualizar producción
docker-compose pull
docker-compose down
docker-compose up -d
```

## ✨ Verificación Post-Despliegue

### 1. Verificar que está corriendo

```bash
docker ps | grep musicalo
```

Deberías ver:
```
CONTAINER ID   IMAGE                         STATUS
xxx            alvaromolrui/musicalo:latest  Up X minutes
```

### 2. Ver versión en logs

```bash
docker-compose logs | head -20
```

### 3. Probar en Telegram

Abre tu bot y prueba:

```
✅ /start (deberías ver mensaje actualizado sobre lenguaje natural)
✅ "recomiéndame un disco de Pink Floyd" (sin comando)
✅ "¿cuál fue mi última canción?" (sin comando)
✅ /recommend (comando tradicional debe funcionar también)
```

## 📋 Checklist Final

- [ ] Imagen latest construida y en Docker Hub
- [ ] Producción actualizada con imagen latest
- [ ] Bot responde con /start mostrando nueva funcionalidad
- [ ] Lenguaje natural funciona correctamente
- [ ] Comandos tradicionales siguen funcionando
- [ ] Sin errores en logs

## 🎉 Cuando Todo Esté OK

- Anunciar release v1.1.0 en GitHub
- Compartir con usuarios la nueva funcionalidad
- Disfrutar del bot conversacional! 🎵🤖

## 🔗 Enlaces

- **GitHub Release**: https://github.com/alvaromolrui/musicalo/releases/tag/v1.1.0
- **Docker Hub**: https://hub.docker.com/r/alvaromolrui/musicalo
- **Rama main**: https://github.com/alvaromolrui/musicalo/tree/main

