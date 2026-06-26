"""Autenticación por API key para los endpoints de Musicalo."""
import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_KEY_HEADER)) -> None:
    """
    Dependencia FastAPI que valida la API key.
    Si MUSICALO_API_KEY no está configurada, el acceso es libre (útil en desarrollo).
    """
    expected = os.getenv("MUSICALO_API_KEY", "").strip()
    if not expected:
        return  # sin clave configurada → acceso abierto
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente. Incluye la cabecera X-API-Key.",
        )
