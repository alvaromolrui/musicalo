# 🚀 Inicio Rápido - Testing

## Paso 1: Construir y Subir Imagen (Local o Servidor)

Donde tengas Docker disponible:

```bash
# Asegúrate de estar en la rama correcta
git checkout feature/ai-natural-language-interaction

# Construir y subir imagen de testing
./build-testing.sh
```

O manualmente:

```bash
docker build -t alvaromolrui/musicalo:testing .
docker login
docker push alvaromolrui/musicalo:testing
```

## Paso 2: Probar en el Servidor (Método Simple)

**Opción A - Editando docker-compose.yml (Recomendado)**

```bash
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# Cambiar latest por testing en docker-compose.yml
nano docker-compose.yml
# Busca: image: alvaromolrui/musicalo:latest
# Cambia a: image: alvaromolrui/musicalo:testing

# Actualizar y reiniciar
docker-compose pull
docker-compose down
docker-compose up -d

# Ver logs
docker-compose logs -f
```

**Opción B - Comando rápido (sin editar archivo)**

```bash
ssh tu-usuario@tu-servidor
cd /ruta/a/musicalo

# Detener producción temporalmente
docker-compose down

# Correr imagen de testing
docker run -d --name musicalo-testing \
  --env-file .env \
  -p 8000:8000 \
  alvaromolrui/musicalo:testing

# Ver logs
docker logs -f musicalo-testing

# Para volver a producción:
docker stop musicalo-testing
docker rm musicalo-testing
docker-compose up -d
```

## ✨ Probar la Nueva Funcionalidad

En Telegram, escribe directamente (sin comandos):

- "Recomiéndame música rock"
- "Busca Queen"
- "Muéstrame mis estadísticas"
- "¿Qué es el jazz?"

El bot interpretará tu mensaje y ejecutará la acción apropiada. 🎵

## 📖 Documentación Completa

Ver `TESTING.md` para instrucciones detalladas.

