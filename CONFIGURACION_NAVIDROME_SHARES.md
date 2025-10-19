# Configuración de Shares en Navidrome

## Configuración correcta

Para que los shares permitan descargar archivos, necesitas estas configuraciones:

## 1. Habilitar la función de Shares

En tu archivo de configuración de Navidrome (o variables de entorno):

```ini
# Archivo navidrome.toml
EnableSharing = true
DefaultDownloadableShare = true
```

O como variables de entorno:
```bash
ND_ENABLESHARING=true
ND_DEFAULTDOWNLOADABLESHARE=true
```

**⚠️ IMPORTANTE:** 
- `EnableSharing`: Habilita la función de shares (por defecto **DESHABILITADA**)
- `DefaultDownloadableShare`: Permite descargas en shares por defecto (recomendado: **true**)

### Docker Compose ejemplo:
```yaml
services:
  navidrome:
    environment:
      - ND_ENABLESHARING=true
      - ND_DEFAULTDOWNLOADABLESHARE=true
```

## 2. Configurar URL pública (si usas proxy inverso)

Si Navidrome está detrás de un proxy inverso:

```ini
# Archivo navidrome.toml
ShareURL = "https://tu-dominio-publico.com"
```

O como variable de entorno:
```bash
ND_SHAREURL=https://tu-dominio-publico.com
```

## 3. Verificar que el proxy permita /share

Si usas nginx, Caddy, etc., asegúrate de permitir el tráfico a `/share/*`:

### Ejemplo nginx:
```nginx
location /share/ {
    proxy_pass http://navidrome:4533/share/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Ejemplo Caddy:
```caddy
reverse_proxy /share/* navidrome:4533
```

## 4. Configurar expiración de shares (opcional)

Por defecto, los shares expiran después de 1 año:

```ini
DefaultShareExpiration = "8760h"  # 1 año
```

Puedes cambiar a:
```ini
DefaultShareExpiration = "720h"   # 30 días
DefaultShareExpiration = "168h"   # 7 días
DefaultShareExpiration = "24h"    # 1 día
```

## Cómo funciona

Una vez configurado correctamente:

1. El comando `/share` crea un share en Navidrome
2. Navidrome genera una URL del tipo: `https://tu-servidor.com/share/XXXXXXXXXX`
3. Cualquiera que abra esa URL verá una interfaz web con:
   - ▶️ Botón de reproducir
   - 📥 Botón de descargar
   - Lista de canciones

## Verificación

Para verificar que está funcionando:

1. Abre tu instancia de Navidrome en el navegador
2. Ve a cualquier álbum
3. Haz clic en el botón "Share" (si aparece)
4. Si NO aparece el botón → EnableSharing está deshabilitado
5. Si aparece → copia el enlace y ábrelo en modo incógnito
6. Deberías ver los botones de reproducir y descargar

## Troubleshooting

### No aparece el botón "Share" en la interfaz
- ✅ Verifica que `EnableSharing = true`
- ✅ Reinicia Navidrome después de cambiar la configuración

### El enlace no funciona (404)
- ✅ Verifica la configuración de `ShareURL`
- ✅ Si usas proxy inverso, verifica que permita `/share/*`

### El enlace funciona pero no puedo descargar
- ✅ Esto es muy raro - por defecto Navidrome permite descargar
- ✅ Verifica que no haya restricciones en tu navegador
- ✅ Prueba en modo incógnito

## Documentación oficial

https://www.navidrome.org/docs/usage/sharing/

## Comando del bot

El comando `/share` del bot ya funciona correctamente. Si las descargas no funcionan, 
es un problema de configuración de Navidrome, no del bot.

