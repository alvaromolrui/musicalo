# Seguridad del Bot de Telegram 🔒

Este documento describe las características de seguridad del Music Agent Bot y cómo configurarlas correctamente.

## 🔐 Control de Acceso

Por defecto, cualquier usuario de Telegram que encuentre tu bot puede interactuar con él. Esto puede ser un problema de seguridad y privacidad, ya que:

- El bot tiene acceso a tu biblioteca musical personal
- Puede mostrar tus estadísticas de escucha
- Utiliza tu API key de Gemini (con límites de uso)
- Accede a tus cuentas de Last.fm/ListenBrainz

**Recomendación:** Configura el bot en modo privado para restricción de acceso.

## 🛡️ Configurar Bot Privado

### Paso 1: Obtener tu ID de Usuario de Telegram

Tu ID de usuario es un número único que te identifica en Telegram. Para obtenerlo:

1. **Abre Telegram** en tu dispositivo (móvil o escritorio)
2. **Busca el bot** [@userinfobot](https://t.me/userinfobot)
3. **Inicia una conversación** con el bot
4. El bot te responderá con tu información:
   ```
   👤 User Info
   
   Id: 123456789
   First Name: Tu Nombre
   Username: @tu_usuario
   Language: es
   ```
5. **Copia el número de ID** (en este ejemplo: `123456789`)

### Paso 2: Configurar Variable de Entorno

Edita tu archivo `.env` (o `docker-compose.override.yml` si usas Docker) y agrega/modifica la siguiente línea:

#### Opción 1: Solo tú
```env
TELEGRAM_ALLOWED_USER_IDS=123456789
```

#### Opción 2: Múltiples usuarios
Si quieres permitir acceso a varias personas (familia, amigos), separa los IDs con comas:

```env
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321,555444333
```

**⚠️ Importante:** NO pongas espacios entre los IDs, solo comas.

### Paso 3: Reiniciar el Bot

#### Si usas Docker:
```bash
./docker-restart.sh
```

#### Si lo ejecutas manualmente:
```bash
# Detener el bot (Ctrl+C si está en ejecución)
# Luego volver a iniciarlo:
python start-bot.py
```

## ✅ Verificar que está Funcionando

### 1. Revisar los Logs

Cuando el bot inicia, deberías ver uno de estos mensajes:

**✅ Modo Privado (Correcto):**
```
🔒 Bot configurado en modo privado para 1 usuario(s)
```

**⚠️ Modo Público (No Seguro):**
```
⚠️ Bot en modo público - cualquier usuario puede usarlo
💡 Para hacerlo privado, configura TELEGRAM_ALLOWED_USER_IDS en .env
```

### 2. Probar con Otro Usuario (Opcional)

Pide a alguien que no esté en la lista que intente usar tu bot. Debería recibir:

```
🚫 Acceso Denegado

Este bot es privado y solo puede ser usado por usuarios autorizados.

Tu ID de usuario es: 999888777

Si crees que deberías tener acceso, contacta con el administrador 
del bot y proporciona tu ID de usuario.
```

## 🔓 Agregar Nuevos Usuarios

Si quieres dar acceso a alguien nuevo:

1. **Pídele su ID de usuario** (que lo obtenga con @userinfobot)
2. **Edita tu `.env`** y agrega su ID a la lista:
   ```env
   TELEGRAM_ALLOWED_USER_IDS=123456789,999888777
   ```
3. **Reinicia el bot**

## ⚠️ Modo Público

Para volver el bot público (NO RECOMENDADO):

1. Edita tu `.env`
2. Deja la variable vacía o coméntala:
   ```env
   # TELEGRAM_ALLOWED_USER_IDS=
   ```
   o
   ```env
   TELEGRAM_ALLOWED_USER_IDS=
   ```
3. Reinicia el bot

## 🔍 Solución de Problemas

### "El bot no me responde y tengo ID configurado"

**Causa:** El ID está mal escrito o hay espacios.

**Solución:**
- Verifica que el ID esté correcto (sin espacios)
- Revisa los logs del bot para ver si detecta el modo privado
- Asegúrate de haber reiniciado el bot después de modificar `.env`

### "Agregué a alguien pero no puede acceder"

**Causa:** No reiniciaste el bot o hay un error de sintaxis.

**Solución:**
- Reinicia el bot con `./docker-restart.sh` o Ctrl+C + `python start-bot.py`
- Verifica que no haya espacios en la lista de IDs
- Revisa que los IDs estén separados solo por comas

### "Los logs no muestran el mensaje de modo privado"

**Causa:** La variable no está cargándose correctamente.

**Solución:**
- Verifica que el archivo `.env` esté en la raíz del proyecto
- Si usas Docker, verifica que `docker-compose.yml` incluya la variable
- Revisa que no haya errores de sintaxis en el archivo `.env`

## 🔑 Mejores Prácticas

1. **✅ Siempre configura el bot en modo privado** a menos que tengas una razón específica para dejarlo público
2. **✅ Mantén tu lista de IDs actualizada** - remueve usuarios que ya no necesiten acceso
3. **✅ No compartas públicamente los IDs** de usuario de otras personas
4. **✅ Haz backup de tu configuración** incluyendo la lista de IDs autorizados
5. **✅ Revisa periódicamente los logs** para detectar intentos de acceso no autorizado

## 🔐 Otras Consideraciones de Seguridad

### API Keys
- Nunca compartas tus API keys (Gemini, Last.fm, Navidrome)
- No subas tu archivo `.env` a repositorios públicos
- Rota tus API keys periódicamente

### Navidrome
- Usa credenciales fuertes para tu cuenta de Navidrome
- Si usas Navidrome público, considera usar un usuario con permisos limitados solo para el bot

### Redes
- Si expones el bot a Internet con webhook, usa HTTPS
- Considera usar un firewall o VPN para limitar acceso

## 📞 Soporte

Si tienes problemas configurando la seguridad del bot:

1. Revisa los logs en `./logs/` o con `./docker-logs.sh`
2. Consulta la [documentación principal](README.md)
3. Abre un issue en el repositorio de GitHub

---

**Recuerda:** La seguridad es responsabilidad tuya. Configura el bot apropiadamente según tus necesidades. 🛡️

