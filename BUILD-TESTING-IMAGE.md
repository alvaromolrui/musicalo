# 🐳 Construir Imagen de Testing para Docker Hub

## Opción 1: Desde tu Máquina Local (Recomendado)

```bash
# 1. Asegúrate de estar en la rama correcta
git checkout feature/ai-natural-language-interaction

# 2. Asegúrate de que Docker está corriendo
docker ps

# 3. Construir la imagen con tag testing
docker build -t alvaromolrui/musicalo:testing .

# 4. Login en Docker Hub (si no lo has hecho)
docker login

# 5. Subir la imagen
docker push alvaromolrui/musicalo:testing
```

## Opción 2: Usando el Script (más cómodo)

```bash
git checkout feature/ai-natural-language-interaction
./build-testing.sh
```

El script te preguntará si quieres subir a Docker Hub después de construir.

## Opción 3: Desde el Servidor

Si prefieres construir directamente en el servidor:

```bash
# En el servidor
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# Actualizar código
git fetch
git checkout feature/ai-natural-language-interaction
git pull

# Construir
docker build -t alvaromolrui/musicalo:testing .

# Login (si no lo has hecho)
docker login

# Subir
docker push alvaromolrui/musicalo:testing
```

## 🚀 Desplegar en el Servidor

Una vez la imagen está en Docker Hub:

```bash
# En el servidor
cd /ruta/a/musicalo

# Editar docker-compose.yml y cambiar:
# image: alvaromolrui/musicalo:latest
# por:
# image: alvaromolrui/musicalo:testing

# O simplemente:
sed -i 's/musicalo:latest/musicalo:testing/' docker-compose.yml

# Descargar la nueva imagen
docker-compose pull

# Reiniciar con la nueva imagen
docker-compose down
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## 🔄 Volver a Producción

```bash
# Cambiar de nuevo a latest
sed -i 's/musicalo:testing/musicalo:latest/' docker-compose.yml

# O editar manualmente docker-compose.yml

docker-compose pull
docker-compose down
docker-compose up -d
```

## ⚡ Alternativa Rápida (Sin Editar Archivo)

También puedes especificar la imagen directamente:

```bash
# Probar testing
docker-compose stop
docker run -d --name musicalo-testing \
  --env-file .env \
  -p 8000:8000 \
  alvaromolrui/musicalo:testing

# Ver logs
docker logs -f musicalo-testing

# Detener y volver a producción
docker stop musicalo-testing
docker rm musicalo-testing
docker-compose up -d
```

## ✅ Verificar que Funciona

1. Abre tu bot en Telegram
2. Envía `/start` - deberías ver el nuevo mensaje sobre lenguaje natural
3. Prueba escribir: **"Recomiéndame música rock"** (sin comandos)
4. El bot debería analizar tu mensaje y darte recomendaciones

## 🏷️ Tags Disponibles

- `alvaromolrui/musicalo:latest` - Versión estable de producción
- `alvaromolrui/musicalo:testing` - Versión de pruebas con IA natural language

## 🆘 Troubleshooting

### Error: Cannot connect to Docker daemon

```bash
# Verifica que Docker está corriendo
docker ps

# Si no está corriendo, inícialo:
# Windows: Abre Docker Desktop
# Linux: sudo systemctl start docker
```

### Error: authentication required

```bash
docker login
# Ingresa tus credenciales de Docker Hub
```

### La imagen no se actualiza

```bash
# Forzar descarga de la nueva imagen
docker-compose pull
docker-compose down
docker-compose up -d --force-recreate
```

