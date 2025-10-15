# 🤖 GitHub Actions - Automatización de Docker

## 🎯 Cómo Funciona

El repositorio ahora tiene CI/CD automático que construye y publica imágenes Docker automáticamente:

### Push a `main`:
```bash
git push origin main
```
→ Construye y sube: `alvaromolrui/musicalo:main`

### Crear Tag (Release):
```bash
git tag v1.1.0-alpha
git push origin v1.1.0-alpha
```
→ Construye y sube:
- `alvaromolrui/musicalo:1.1.0-alpha` (versión específica)
- `alvaromolrui/musicalo:latest` (última release)

---

## ⚙️ Configuración Inicial (Solo Primera Vez)

### 1. Crear Token de Docker Hub

1. Ve a https://hub.docker.com
2. Click en tu usuario → **Account Settings**
3. **Security** → **New Access Token**
4. Nombre: `github-actions-musicalo`
5. Permisos: **Read, Write, Delete**
6. **Generate** y copia el token

### 2. Añadir Secret en GitHub

1. Ve a tu repositorio: https://github.com/alvaromolrui/musicalo
2. **Settings** → **Secrets and variables** → **Actions**
3. Click en **New repository secret**
4. Name: `DOCKER_PASSWORD`
5. Secret: Pega el token de Docker Hub
6. **Add secret**

### 3. ¡Listo!

Ya no necesitas construir imágenes manualmente. GitHub lo hará automáticamente.

---

## 🚀 Flujo de Trabajo

### Desarrollo Normal:

```bash
# 1. Hacer cambios en tu código
git add .
git commit -m "feat: nueva funcionalidad"

# 2. Push a main
git push origin main

# 3. GitHub Actions automáticamente:
#    - Construye la imagen
#    - La sube como alvaromolrui/musicalo:main
```

### Publicar Release:

```bash
# 1. Actualizar VERSION
echo "1.2.0-alpha" > VERSION

# 2. Actualizar CHANGELOG.md
# Añadir entrada para v1.2.0-alpha

# 3. Commit de versión
git add VERSION CHANGELOG.md
git commit -m "chore: Release v1.2.0-alpha"
git push origin main

# 4. Crear tag
git tag -a v1.2.0-alpha -m "Release v1.2.0-alpha"
git push origin v1.2.0-alpha

# 5. GitHub Actions automáticamente:
#    - Construye la imagen
#    - La sube como alvaromolrui/musicalo:1.2.0-alpha
#    - Actualiza alvaromolrui/musicalo:latest
```

---

## 🏷️ Tags Disponibles en Docker Hub

Después de configurar, tendrás:

```
alvaromolrui/musicalo:latest        → Última release (v1.1.0-alpha)
alvaromolrui/musicalo:1.1.0-alpha   → Release específica
alvaromolrui/musicalo:1.0.0         → Release anterior (cuando exista)
alvaromolrui/musicalo:main          → Última versión de main (desarrollo)
```

---

## 📊 Ventajas

✅ **Automático**: No construyes manualmente  
✅ **Multiplataforma**: AMD64 + ARM64  
✅ **Cache optimizado**: Builds más rápidos  
✅ **Versionado claro**: Tag por release  
✅ **Separación**: `latest` (producción) vs `main` (desarrollo)  

---

## 🔍 Ver Estado de Builds

1. Ve a tu repositorio en GitHub
2. Click en **Actions**
3. Verás todos los builds con su estado

---

## 🛑 Desactivar (si es necesario)

Si no quieres usar GitHub Actions temporalmente:

1. Renombra el archivo:
```bash
mv .github/workflows/docker-publish.yml .github/workflows/docker-publish.yml.disabled
```

2. O elimina la carpeta:
```bash
rm -rf .github/
```

---

## 🆘 Troubleshooting

### Error: "Invalid credentials"

- Verifica que `DOCKER_PASSWORD` esté configurado en GitHub Secrets
- Regenera el token en Docker Hub si es necesario

### Build falla

- Revisa los logs en GitHub Actions (pestaña Actions)
- Verifica que Dockerfile sea válido

### No se actualiza `latest`

- Solo se actualiza con tags, no con push a main
- Asegúrate de crear el tag con `git tag v1.x.x`

---

## 📝 Recomendación de Versionado

Para futuras releases:

```
v1.1.0-alpha  → Primera alpha de 1.1
v1.1.0-beta   → Beta de 1.1
v1.1.0        → Release estable 1.1
v1.2.0-alpha  → Siguiente versión alpha
```

Cada tag creará automáticamente su imagen en Docker Hub.

