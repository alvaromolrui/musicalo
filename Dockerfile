# Usar imagen base optimizada
FROM python:3.11-slim

# Instalar dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    bash \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias primero (mejor cache)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Limpiar dependencias de compilación para reducir tamaño
RUN apt-get purge -y gcc build-essential && \
    apt-get autoremove -y && \
    apt-get clean

# Copiar código de la aplicación
COPY backend/ ./backend/
COPY start-bot.py .
COPY docker-entrypoint.sh .

# Crear usuario no-root y configurar permisos
RUN useradd -m -s /bin/bash bot && \
    chmod +x docker-entrypoint.sh && \
    mkdir -p /app/logs && \
    chown -R bot:bot /app

# Cambiar a usuario no-root
USER bot

# Comando por defecto
CMD ["./docker-entrypoint.sh"]
