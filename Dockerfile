# Usar imagen base de Python oficial
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/ ./backend/
COPY start-bot.py .
COPY docker-entrypoint.sh .

# Hacer ejecutable el script de entrada
RUN chmod +x docker-entrypoint.sh

# Crear directorio para logs
RUN mkdir -p /app/logs

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash bot && \
    chown -R bot:bot /app
USER bot

# Exponer puerto
EXPOSE 8000

# Comando por defecto usando el script de entrada
CMD ["./docker-entrypoint.sh"]
