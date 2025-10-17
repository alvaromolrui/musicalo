import os
from typing import List, Optional
from datetime import datetime
from models.schemas import Track

class PlaylistService:
    """Servicio para crear y gestionar playlists en formato M3U"""
    
    def __init__(self):
        self.navidrome_url = os.getenv("NAVIDROME_URL", "http://localhost:4533")
        self.navidrome_username = os.getenv("NAVIDROME_USERNAME", "admin")
    
    def create_m3u_playlist(
        self, 
        tracks: List[Track], 
        playlist_name: str,
        description: Optional[str] = None,
        simple_format: bool = True
    ) -> str:
        """Crear playlist en formato M3U
        
        Args:
            tracks: Lista de canciones para incluir en la playlist
            playlist_name: Nombre de la playlist
            description: Descripción opcional de la playlist
            simple_format: Si True, usa formato simple (solo rutas). Si False, usa formato extendido
            
        Returns:
            Contenido de la playlist en formato M3U
        """
        
        if simple_format:
            # Formato ultra simple: SOLO nombres de archivo, nada más
            m3u_content = ""
            
            for track in tracks:
                # Solo agregar el nombre del archivo (sin ruta completa, sin metadata)
                if track.path:
                    # Extraer solo el nombre del archivo de la ruta
                    import os
                    import re
                    filename = os.path.basename(track.path)
                    
                    # Limpiar el nombre del archivo: remover números de pista (01-04 -, 02-05 -, etc.)
                    # Patrón: número-número - al inicio del nombre
                    cleaned_filename = re.sub(r'^\d{2}-\d{2}\s*-\s*', '', filename)
                    
                    m3u_content += f"{cleaned_filename}\n"
                elif track.id:
                    # Si no hay path pero hay ID, usar la URL de streaming de Navidrome
                    stream_url = f"{self.navidrome_url}/rest/stream.view?id={track.id}&u={self.navidrome_username}"
                    m3u_content += f"{stream_url}\n"
        else:
            # Formato extendido: con metadata (EXTINF, duración, etc)
            m3u_content = "#EXTM3U\n"
            if description:
                m3u_content += f"#PLAYLIST:{playlist_name}\n"
                m3u_content += f"#EXTENC:UTF-8\n"
                m3u_content += f"#DESCRIPTION:{description}\n"
            
            for track in tracks:
                # Duración en segundos
                duration = track.duration if track.duration else -1
                
                # Información del track
                artist_info = track.artist if track.artist else "Unknown Artist"
                title_info = track.title if track.title else "Unknown Track"
                
                m3u_content += f"#EXTINF:{duration},{artist_info} - {title_info}\n"
                
                # URL de streaming de Navidrome/Subsonic
                if track.id:
                    # Construir URL de stream con autenticación
                    stream_url = f"{self.navidrome_url}/rest/stream.view?id={track.id}&u={self.navidrome_username}"
                    m3u_content += f"{stream_url}\n"
                elif track.path:
                    # Si no hay ID pero hay path, usar el path
                    m3u_content += f"{track.path}\n"
                else:
                    # Fallback: comentar que no hay URL disponible
                    m3u_content += f"# No stream URL available for {artist_info} - {title_info}\n"
        
        return m3u_content
    
    def save_playlist(self, m3u_content: str, filename: str, output_dir: str = "/tmp") -> str:
        """Guardar playlist en archivo
        
        Args:
            m3u_content: Contenido de la playlist en formato M3U
            filename: Nombre del archivo (sin extensión)
            output_dir: Directorio donde guardar el archivo
            
        Returns:
            Ruta completa del archivo guardado
        """
        # Asegurar que el directorio existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Limpiar el nombre de archivo
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filepath = os.path.join(output_dir, f"{safe_filename}.m3u")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"✅ Playlist guardada en: {filepath}")
        return filepath
    
    def create_playlist_from_recommendations(
        self,
        recommendations: List,
        name: str,
        description: Optional[str] = None,
        simple_format: bool = True
    ) -> str:
        """Crear playlist M3U desde una lista de recomendaciones
        
        Args:
            recommendations: Lista de objetos Recommendation
            name: Nombre de la playlist
            description: Descripción opcional
            simple_format: Si True, usa formato simple (solo rutas). Si False, usa formato extendido
            
        Returns:
            Contenido M3U de la playlist
        """
        tracks = [rec.track for rec in recommendations]
        return self.create_m3u_playlist(tracks, name, description, simple_format)
    
    def validate_playlist(self, m3u_content: str) -> bool:
        """Validar que una playlist M3U tenga formato correcto
        
        Args:
            m3u_content: Contenido de la playlist
            
        Returns:
            True si es válida, False en caso contrario
        """
        lines = m3u_content.strip().split('\n')
        
        # Debe empezar con #EXTM3U
        if not lines or not lines[0].startswith('#EXTM3U'):
            print("❌ Playlist inválida: no empieza con #EXTM3U")
            return False
        
        # Debe tener al menos una entrada
        extinf_count = sum(1 for line in lines if line.startswith('#EXTINF'))
        if extinf_count == 0:
            print("❌ Playlist inválida: no contiene canciones")
            return False
        
        print(f"✅ Playlist válida: {extinf_count} canciones")
        return True
    
    def get_playlist_info(self, m3u_content: str) -> dict:
        """Extraer información de una playlist M3U
        
        Args:
            m3u_content: Contenido de la playlist
            
        Returns:
            Diccionario con información de la playlist
        """
        lines = m3u_content.strip().split('\n')
        
        info = {
            'name': None,
            'description': None,
            'track_count': 0,
            'total_duration': 0,
            'tracks': []
        }
        
        current_track = {}
        
        for line in lines:
            if line.startswith('#PLAYLIST:'):
                info['name'] = line.replace('#PLAYLIST:', '').strip()
            elif line.startswith('#DESCRIPTION:'):
                info['description'] = line.replace('#DESCRIPTION:', '').strip()
            elif line.startswith('#EXTINF:'):
                # Parsear duración y título
                parts = line.replace('#EXTINF:', '').split(',', 1)
                if len(parts) == 2:
                    try:
                        duration = int(parts[0])
                        info['total_duration'] += duration if duration > 0 else 0
                        current_track['duration'] = duration
                        current_track['title'] = parts[1].strip()
                    except ValueError:
                        pass
            elif line and not line.startswith('#'):
                # URL o path de la canción
                current_track['url'] = line.strip()
                info['tracks'].append(current_track.copy())
                info['track_count'] += 1
                current_track = {}
        
        return info

