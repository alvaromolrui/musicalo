FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# El config.toml se valida contra la versión instalada de Chainlit.
# Borrarlo aquí hace que Chainlit lo regenere en el primer arranque,
# evitando el error "Your config file is outdated".
RUN rm -f .chainlit/config.toml

# Directorio para el SQLite del historial de conversaciones
RUN mkdir -p /app/data

RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# init_db.py crea las tablas SQLite si no existen (idempotente)
CMD ["sh", "-c", "python init_db.py && chainlit run app.py --host 0.0.0.0 --port 8080"]
