import google.generativeai as genai
import os
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter
import re
import random
from models.schemas import UserProfile, Recommendation, Track, ScrobbleTrack, ScrobbleArtist, MusicAnalysis
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.musicbrainz_service import MusicBrainzService
from services.cache_manager import cache_manager, cached
from services.analytics_system import analytics_system
from services.adaptive_learning_system import adaptive_learning_system
from services.hybrid_recommendation_engine import HybridRecommendationEngine, RecommendationStrategy
from services.advanced_personalization_system import advanced_personalization_system
from services.error_recovery_system import error_recovery_system
from services.advanced_monitoring_system import advanced_monitoring_system
from services.user_features_system import user_features_system

class MusicRecommendationService:
    def __init__(self):
        # Configurar Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.navidrome = NavidromeService()
        self.listenbrainz = ListenBrainzService()
        
        # Inicializar MusicBrainz para metadatos y descubrimiento
        self.musicbrainz = None
        if os.getenv("ENABLE_MUSICBRAINZ", "true").lower() == "true":
            try:
                self.musicbrainz = MusicBrainzService()
                print("✅ MusicBrainz habilitado para metadatos y descubrimiento")
            except Exception as e:
                print(f"⚠️ Error inicializando MusicBrainz: {e}")
        
        # Cache simple para optimizar rendimiento
        self._library_artists_cache = None
        self._library_artists_cache_time = 0
        self._cache_ttl = 300  # 5 minutos
        
        print("✅ Servicio de recomendaciones usando ListenBrainz + MusicBrainz + Aprendizaje Adaptativo + Motor Híbrido + Características Avanzadas")
        
        # Inicializar motor híbrido
        self.hybrid_engine = HybridRecommendationEngine(self)
    
    async def initialize_monitoring(self):
        """Inicializar sistemas de monitoreo después de que el event loop esté ejecutándose"""
        try:
            await advanced_monitoring_system.start_monitoring()
            print("✅ Sistema de monitoreo avanzado iniciado")
        except Exception as e:
            print(f"⚠️ Error iniciando monitoreo avanzado: {e}")
    
    async def _get_library_artists_cached(self) -> set:
        """Obtener lista de artistas de biblioteca con caché mejorado
        
        Returns:
            Set de nombres de artistas en minúsculas
        """
        async def fetch_artists():
            """Función para obtener artistas de la biblioteca"""
            try:
                library_data = await self.navidrome.get_artists(limit=500)
                artists_set = {artist.name.lower() for artist in library_data}
                print(f"📚 Biblioteca cargada: {len(artists_set)} artistas")
                return artists_set
            except Exception as e:
                print(f"⚠️ Error obteniendo artistas de biblioteca: {e}")
                return set()
        
        # Usar el nuevo sistema de caché
        return await cache_manager.get_with_fallback(
            "library_artists",
            fetch_artists,
            cache_type="library_data"
        )
    
    async def analyze_user_profile(self, user_profile: UserProfile) -> MusicAnalysis:
        """Analizar el perfil musical del usuario"""
        try:
            # Análisis de géneros
            genres = []
            for track in user_profile.recent_tracks:
                # Simular extracción de género (en un caso real, usarías APIs de música)
                genre = await self._extract_genre(track.artist, track.name)
                if genre:
                    genres.append(genre)
            
            genre_distribution = dict(Counter(genres))
            total_tracks = len(genres)
            if total_tracks > 0:
                genre_distribution = {k: v/total_tracks for k, v in genre_distribution.items()}
            
            # Análisis de patrones temporales
            time_patterns = self._analyze_time_patterns(user_profile.recent_tracks)
            
            # Análisis de diversidad de artistas
            unique_artists = set()
            for track in user_profile.recent_tracks:
                unique_artists.add(track.artist)
            
            artist_diversity = len(unique_artists) / max(len(user_profile.recent_tracks), 1)
            
            # Análisis de humor basado en patrones de escucha
            mood_analysis = await self._analyze_mood_patterns(user_profile.recent_tracks)
            
            return MusicAnalysis(
                genre_distribution=genre_distribution,
                tempo_preferences={},  # Se podría implementar con análisis de audio
                mood_analysis=mood_analysis,
                time_patterns=time_patterns,
                artist_diversity=artist_diversity,
                discovery_rate=self._calculate_discovery_rate(user_profile)
            )
            
        except Exception as e:
            print(f"Error analizando perfil: {e}")
            return MusicAnalysis(
                genre_distribution={},
                tempo_preferences={},
                mood_analysis={},
                time_patterns={},
                artist_diversity=0.0,
                discovery_rate=0.0
            )
    
    async def generate_recommendations(
        self, 
        user_profile: UserProfile, 
        limit: int = 10, 
        include_new_music: bool = True,
        recommendation_type: str = "general",
        genre_filter: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        from_library_only: bool = False
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en el perfil del usuario
        
        Args:
            user_profile: Perfil del usuario con sus gustos
            limit: Número de recomendaciones a generar
            include_new_music: Si True, incluye música que no está en la biblioteca (usando ListenBrainz)
            recommendation_type: 'general', 'album', 'artist', 'track'
            genre_filter: Género o estilo específico para filtrar
            custom_prompt: Descripción libre y específica del usuario sobre lo que busca
            from_library_only: Si True, SOLO recomienda música de la biblioteca del usuario (no descubrimiento)
        """
        try:
            # Si hay genre_filter pero no custom_prompt, convertir el genre_filter en custom_prompt
            if genre_filter and not custom_prompt:
                custom_prompt = f"música de género {genre_filter}"
                print(f"🎯 Convirtiendo filtro de género '{genre_filter}' en prompt personalizado")
            
            # Mensaje de log con información del prompt personalizado
            if from_library_only:
                print(f"📚 Generando {limit} recomendaciones SOLO de tu biblioteca...")
            elif custom_prompt:
                print(f"🎯 Generando {limit} recomendaciones con criterios específicos: {custom_prompt[:100]}...")
            else:
                print(f"🎯 Generando {limit} recomendaciones...")
            
            # Analizar perfil del usuario
            analysis = await self.analyze_user_profile(user_profile)
            
            recommendations = []
            
            # Si solo quiere recomendaciones de biblioteca, ir directo a eso
            if from_library_only:
                print("📚 Modo: Solo recomendaciones de tu biblioteca (sin descubrimiento)")
                library_recs = await self._generate_library_only_recommendations(
                    user_profile,
                    analysis,
                    limit,
                    recommendation_type=recommendation_type,
                    genre_filter=genre_filter,
                    custom_prompt=custom_prompt
                )
                return library_recs
            
            # DECISIÓN: ¿Usar IA o solo ListenBrainz+MusicBrainz?
            # IA solo para peticiones específicas (con género o custom_prompt)
            # ListenBrainz+MusicBrainz para recomendaciones generales basadas en historial
            use_ai = bool(genre_filter or custom_prompt)
            
            if use_ai:
                # Usuario pidió algo específico - usar IA
                if not custom_prompt and genre_filter:
                    custom_prompt = f"música de género {genre_filter}"
                
                print(f"🎨 Generando recomendaciones con IA (criterio específico: {custom_prompt[:100]}...)...")
                custom_recs = await self._generate_custom_prompt_recommendations(
                    user_profile,
                    analysis,
                    custom_prompt,
                    limit,
                    recommendation_type
                )
                recommendations.extend(custom_recs)
                print(f"✅ Encontradas {len(custom_recs)} recomendaciones de IA")
            
            # Usar ListenBrainz+MusicBrainz para descubrimiento basado en historial
            if len(recommendations) < limit and include_new_music and len(user_profile.top_artists) > 0:
                remaining_limit = limit - len(recommendations)
                
                if use_ai:
                    print(f"🌍 Complementando con ListenBrainz+MusicBrainz...")
                else:
                    print(f"🌍 Generando recomendaciones desde ListenBrainz+MusicBrainz basadas en tu historial...")
                
                new_music_recs = await self._generate_listenbrainz_recommendations(
                    user_profile, 
                    remaining_limit, 
                    recommendation_type=recommendation_type,
                    genre_filter=genre_filter,
                    custom_prompt=custom_prompt
                )
                
                # Filtrar duplicados con recomendaciones existentes
                existing_keys = {f"{r.track.artist.lower()}|{r.track.title.lower()}" for r in recommendations}
                filtered_recs = [r for r in new_music_recs 
                                if f"{r.track.artist.lower()}|{r.track.title.lower()}" not in existing_keys]
                
                recommendations.extend(filtered_recs)
                if len(filtered_recs) < len(new_music_recs):
                    print(f"⚠️ Filtrados {len(new_music_recs) - len(filtered_recs)} duplicados")
                print(f"✅ Encontradas {len(filtered_recs)} recomendaciones de música nueva")
            
            # Si no hay suficientes, buscar en la biblioteca
            if len(recommendations) < limit:
                print("📚 Buscando en tu biblioteca de Navidrome...")
                library_tracks = await self.navidrome.get_tracks(limit=200)
                
                # Filtrar canciones ya conocidas
                known_tracks = {track.name.lower() for track in user_profile.recent_tracks}
                unknown_tracks = [
                    track for track in library_tracks 
                    if track.title.lower() not in known_tracks
                ]
                
                # Generar recomendaciones usando IA
                library_recs = await self._generate_ai_recommendations(
                    user_profile, analysis, unknown_tracks, limit - len(recommendations)
                )
                
                # Filtrar duplicados con recomendaciones existentes
                existing_keys = {f"{r.track.artist.lower()}|{r.track.title.lower()}" for r in recommendations}
                filtered_lib_recs = [r for r in library_recs 
                                    if f"{r.track.artist.lower()}|{r.track.title.lower()}" not in existing_keys]
                
                recommendations.extend(filtered_lib_recs)
                if len(filtered_lib_recs) < len(library_recs):
                    print(f"⚠️ Filtrados {len(library_recs) - len(filtered_lib_recs)} duplicados de biblioteca")
                print(f"✅ Encontradas {len(filtered_lib_recs)} recomendaciones de tu biblioteca")
            
            # Eliminar duplicados finales (por si acaso)
            unique_recommendations = []
            seen_final = set()
            for rec in recommendations:
                key = f"{rec.track.artist.lower()}|{rec.track.title.lower()}"
                if key not in seen_final:
                    unique_recommendations.append(rec)
                    seen_final.add(key)
            
            if len(unique_recommendations) < len(recommendations):
                print(f"⚠️ Eliminados {len(recommendations) - len(unique_recommendations)} duplicados finales")
            
            print(f"🎵 Total de recomendaciones únicas: {len(unique_recommendations)}")
            return unique_recommendations[:limit]
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones: {e}")
            return []
    
    async def _generate_listenbrainz_recommendations(
        self, 
        user_profile: UserProfile, 
        limit: int,
        recommendation_type: str = "general",
        genre_filter: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> List[Recommendation]:
        """Generar recomendaciones usando ListenBrainz (música nueva que no tienes)
        
        Args:
            user_profile: Perfil del usuario
            limit: Número de recomendaciones
            recommendation_type: 'general', 'album', 'artist', 'track'
            genre_filter: Filtro de género/estilo
            custom_prompt: Descripción específica del usuario sobre lo que busca
        """
        try:
            recommendations = []
            processed_artists = set()
            
            # Obtener lista de artistas de la biblioteca para excluirlos (con cache)
            library_artists = await self._get_library_artists_cached()
            
            # Seleccionar aleatoriamente algunos top artistas para variar las recomendaciones
            # OPTIMIZACIÓN: Reducido de 5 a 3 artistas para ser más rápido
            available_top_artists = user_profile.top_artists[:8]  # Considerar top 8
            num_artists_to_use = min(3, len(available_top_artists))  # Máximo 3 artistas
            selected_artists = random.sample(available_top_artists, num_artists_to_use) if len(available_top_artists) > num_artists_to_use else available_top_artists
            
            print(f"🔍 Generando recomendaciones de ListenBrainz para {len(selected_artists)} artistas (optimizado para velocidad)")
            
            # Para asegurar diversidad, tomar 1 recomendación por artista
            # Obtener artistas similares basados en los artistas seleccionados
            for top_artist in selected_artists:
                if len(recommendations) >= limit:
                    break
                
                print(f"🎤 Buscando artistas similares a: {top_artist.name}")
                # Obtener más artistas similares y seleccionar aleatoriamente
                # OPTIMIZACIÓN: Reducido de 10 a 7 para ser más rápido
                similar_artists = await self.listenbrainz.get_similar_artists_from_recording(
                    top_artist.name, 
                    limit=7,
                    musicbrainz_service=self.musicbrainz
                )
                print(f"   Encontrados {len(similar_artists)} artistas similares")
                
                # Aleatorizar el orden de artistas similares
                if similar_artists:
                    random.shuffle(similar_artists)
                
                # IMPORTANTE: Solo tomar 1 artista similar por cada top_artist para diversidad
                # Y EXCLUIR artistas que ya están en la biblioteca
                similar_artist = None
                for candidate in similar_artists:
                    candidate_lower = candidate.name.lower()
                    if (candidate.name not in processed_artists and 
                        candidate_lower not in library_artists):
                        similar_artist = candidate
                        print(f"   ✅ Seleccionado: {candidate.name} (NO está en biblioteca)")
                        break
                    elif candidate_lower in library_artists:
                        print(f"   ⏭️ Skipping {candidate.name}: ya está en biblioteca")
                
                if not similar_artist:
                    print(f"   ⚠️ No hay artistas similares nuevos para {top_artist.name}")
                    continue
                    
                processed_artists.add(similar_artist.name)
                
                # Aplicar filtro de género si existe
                if genre_filter:
                    # Por ahora, incluir todos los artistas similares
                    # En una implementación futura se podría consultar tags del artista
                    pass
                
                # Crear recomendación del artista similar
                print(f"   ➕ Agregando recomendación: {similar_artist.name}")
                
                # Personalizar según el tipo de recomendación
                title = ""
                reason = ""
                album_name = ""
                artist_url = similar_artist.url if hasattr(similar_artist, 'url') and similar_artist.url else ""
                
                if recommendation_type == "album":
                    # Obtener el álbum top del artista similar (usar MusicBrainz)
                    if self.musicbrainz:
                        top_albums = await self.musicbrainz.get_artist_top_albums_enhanced(similar_artist.name, limit=1)
                    else:
                        top_albums = []
                    if top_albums:
                        album_data = top_albums[0]
                        title = album_data.get("name", f"Álbum de {similar_artist.name}")
                        album_name = album_data.get("name", "")
                        artist_url = album_data.get("url", artist_url)
                        reason = f"📀 Álbum top de artista similar a {top_artist.name}"
                    else:
                        title = f"Discografía de {similar_artist.name}"
                        reason = f"📀 Similar a {top_artist.name}"
                
                elif recommendation_type == "track":
                    # Obtener la canción top del artista similar (usar MusicBrainz)
                    if self.musicbrainz:
                        top_tracks = await self.musicbrainz.get_artist_top_tracks_enhanced(similar_artist.name, limit=1)
                    else:
                        top_tracks = []
                    if top_tracks:
                        track_data = top_tracks[0]
                        title = track_data.name
                        artist_url = track_data.url if track_data.url else artist_url
                        reason = f"🎵 Canción top de artista similar a {top_artist.name}"
                    else:
                        title = f"Música de {similar_artist.name}"
                        reason = f"🎵 Similar a {top_artist.name}"
                
                elif recommendation_type == "artist":
                    title = similar_artist.name
                    reason = f"🌟 Similar a {top_artist.name}"
                
                else:
                    title = f"Descubre {similar_artist.name}"
                    reason = f"🌟 Artista similar a {top_artist.name} que te puede gustar"
                
                # Crear el objeto Track primero
                track = Track(
                    id=f"listenbrainz_{recommendation_type}_{similar_artist.name.replace(' ', '_')}_{title.replace(' ', '_')[:30]}",
                    title=title,
                    artist=similar_artist.name,
                    album=album_name,
                    duration=None,
                    year=None,
                    genre=genre_filter if genre_filter else "",
                    play_count=None,
                    path=artist_url if artist_url else "",  # Usar URL en el campo path
                    cover_url=None
                )
                
                # Crear la recomendación
                recommendation = Recommendation(
                    track=track,
                    reason=reason,
                    confidence=0.85,  # Score alto para música nueva
                    source="ListenBrainz+MusicBrainz",
                    tags=[genre_filter] if genre_filter else []
                )
                recommendations.append(recommendation)
            
            print(f"✅ Total de recomendaciones de ListenBrainz: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones de ListenBrainz: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_custom_prompt_recommendations(
        self,
        user_profile: UserProfile,
        analysis: MusicAnalysis,
        custom_prompt: str,
        limit: int,
        recommendation_type: str = "general"
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en una descripción específica del usuario usando IA
        
        Args:
            user_profile: Perfil del usuario
            analysis: Análisis del perfil musical
            custom_prompt: Descripción específica de lo que el usuario busca
            limit: Número de recomendaciones
            recommendation_type: Tipo de recomendación
        """
        try:
            print(f"🎨 Generando recomendaciones con prompt personalizado: {custom_prompt}")
            
            # Preparar contexto del usuario
            recent_artists = [track.artist for track in user_profile.recent_tracks[:15]]
            top_artists = [artist.name for artist in user_profile.top_artists[:10]]
            
            # Obtener artistas de biblioteca para excluir (con cache)
            library_artists_set = await self._get_library_artists_cached()
            library_artists_list = list(library_artists_set)
            
            # Crear un prompt MUY estricto para evitar análisis
            ai_prompt = f"""TAREA: Genera {limit} recomendaciones musicales.

PERFIL DEL USUARIO:
Top artistas: {', '.join(top_artists[:5]) if top_artists else 'Desconocidos'}

EXCLUIR (ya los tiene): {', '.join(library_artists_list[:20]) if library_artists_list else 'Ninguno'}

CRITERIO: {custom_prompt}

INSTRUCCIONES:
1. Recomienda {limit} artistas/álbumes DIFERENTES
2. NO recomiendes artistas que ya tiene
3. Si pide un género, IGNORA su perfil y recomienda SOLO ese género
4. Genera SOLO la lista, SIN análisis previo

FORMATO OBLIGATORIO (cada línea):
[Artista] - [Álbum/Nombre] | [Razón de 15-40 palabras con mayúscula inicial y punto final.]

EJEMPLOS VÁLIDOS:
Radiohead - OK Computer | Rock alternativo innovador de 1997 con experimentación electrónica y letras introspectivas que definen una generación.
Aphex Twin - Selected Ambient Works | Electrónica ambient pionera con texturas sonoras profundas y atmósferas envolventes perfectas para inmersión.

❌ NO HAGAS:
- Análisis del perfil
- Explicaciones
- Introducciones
- Numeración

✅ EMPIEZA DIRECTAMENTE:
"""

            # Generar con Gemini con configuración para respuestas más predecibles y rápidas
            # OPTIMIZACIÓN: Reducido max_output_tokens para respuestas más rápidas
            generation_config = {
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 800,  # Suficiente para 5-10 recomendaciones
            }
            
            response = self.model.generate_content(
                ai_prompt,
                generation_config=generation_config
            )
            
            # Manejar errores de seguridad de Gemini
            try:
                ai_response = response.text.strip()
            except ValueError as e:
                # Si la respuesta fue bloqueada por seguridad, intentar sin lista de biblioteca
                print(f"⚠️ Respuesta bloqueada por filtros de seguridad de Gemini")
                print(f"   Reintentando sin lista detallada de biblioteca...")
                
                # Prompt simplificado sin artistas específicos
                ai_prompt_simple = f"""TAREA: Genera {limit} recomendaciones musicales.

PERFIL: Escucha {', '.join(top_artists[:3]) if top_artists else 'música variada'}

CRITERIO: {custom_prompt}

FORMATO (cada línea):
[Artista] - [Álbum] | [Razón de 15-40 palabras con mayúscula y punto.]

NO generes análisis. EMPIEZA DIRECTAMENTE:
"""
                
                response = self.model.generate_content(ai_prompt_simple, generation_config=generation_config)
                try:
                    ai_response = response.text.strip()
                except ValueError:
                    print(f"❌ IA bloqueada por seguridad incluso con prompt simple")
                    return []
            
            print(f"📝 Respuesta de IA recibida (longitud: {len(ai_response)})")
            print(f"📝 DEBUG - Respuesta completa:\n{ai_response}\n---END---")
            
            # Procesar las recomendaciones de la IA
            recommendations = []
            seen_tracks = set()  # Para evitar duplicados
            
            # Limpiar la respuesta de la IA
            # A veces genera texto antes o marcadores de formato
            lines_raw = ai_response.split('\n')
            
            # Filtrar líneas válidas: deben tener formato [ARTISTA] - [NOMBRE] | [RAZÓN]
            valid_lines = []
            for line in lines_raw:
                line = line.strip()
                if not line:
                    continue
                
                # Remover numeración si existe (1., 2., etc)
                line_clean = re.sub(r'^\d+[\.\)]\s*', '', line)
                
                # Debe tener - y | para ser válida
                if '-' in line_clean and '|' in line_clean:
                    # Verificar que no sea una línea de análisis
                    lower = line_clean.lower()
                    if not any(skip in lower for skip in ['**', 'basado en', 'perfil', 'análisis', 'usuario', 'género']):
                        valid_lines.append(line_clean)
            
            print(f"📝 DEBUG - Encontradas {len(valid_lines)} líneas válidas de {len(lines_raw)} totales")
            if len(valid_lines) > 0:
                print(f"📝 DEBUG - Primera línea válida: {valid_lines[0][:100]}")
            
            for line in valid_lines:
                if len(recommendations) >= limit:
                    break
                
                # Buscar el formato: [ARTISTA] - [NOMBRE] | [RAZÓN]
                try:
                    parts = line.split('|', 1)
                    artist_and_name = parts[0].strip()
                    reason = parts[1].strip() if len(parts) > 1 else "Recomendado según tus criterios"
                    
                    # Si la razón es muy corta (probablemente un fragmento), skip
                    if len(reason) < 20:
                        print(f"   ⚠️ Razón muy corta ({len(reason)} chars), skipping: {reason}")
                        continue
                    
                    # Dividir artista y nombre
                    if ' - ' in artist_and_name:
                        artist, name = artist_and_name.split(' - ', 1)
                    elif '-' in artist_and_name:
                        artist, name = artist_and_name.split('-', 1)
                    else:
                        # Si no hay separador, asumir que es el nombre del artista
                        artist = artist_and_name
                        name = artist_and_name
                    
                    artist = artist.strip()
                    name = name.strip()
                    
                    # VALIDACIÓN POST-PARSEO: Verificar que la razón NO sea un fragmento de análisis
                    # Los fragmentos tienen patrones específicos:
                    is_invalid = False
                    
                    # Patrones de fragmento con markdown o análisis
                    if any(pattern in reason for pattern in ['):**', '**', ':**', '*:', 'céntrico', 'fi:', 'hop:', 'rock:', 'punk:', 'jazz:', 'pop:', 'metal:']):
                        print(f"   ⚠️ Razón con patrón markdown/análisis, skipping: {reason[:60]}")
                        is_invalid = True
                    
                    # Empieza con minúscula (fragmento de oración)
                    if reason and reason[0].islower():
                        print(f"   ⚠️ Razón empieza con minúscula (fragmento), skipping: {reason[:60]}")
                        is_invalid = True
                    
                    # Frases de análisis (más exhaustivo)
                    analysis_phrases = [
                        'la lista de', 'el usuario', 'artistas recientes', 'demuestran', 'sugiere',
                        'tu sección', 'tu perfil', 'tus gustos', 'monopolizada por', 'indica una',
                        'la presencia de', 'apuntan a', 'predilección por', 'esto sugiere',
                        'basado en', 'el análisis'
                    ]
                    if any(phrase in reason.lower() for phrase in analysis_phrases):
                        print(f"   ⚠️ Razón con frase de análisis, skipping: {reason[:60]}")
                        is_invalid = True
                    
                    # Razón muy corta (menos de 8 palabras)
                    if len(reason.split()) < 8:
                        print(f"   ⚠️ Razón muy corta ({len(reason.split())} palabras), skipping: {reason}")
                        is_invalid = True
                    
                    # Detectar si la razón parece ser un fragmento de título de sección
                    # Ej: "Hip Hop Español Clásico y Colaborativo:**"
                    if reason.endswith(':**') or reason.endswith('**'):
                        print(f"   ⚠️ Razón parece título de sección, skipping: {reason[:60]}")
                        is_invalid = True
                    
                    # Detectar palabras truncadas al inicio (señal de fragmento)
                    # Ej: "hop Español" (debería ser "Hip hop Español")
                    first_word = reason.split()[0] if reason.split() else ""
                    if first_word and len(first_word) <= 3 and first_word[0].isupper():
                        # Verificar si parece un fragmento de palabra
                        common_fragments = ['hop', 'fi', 'pop', 'rap', 'dub', 'ska']
                        if first_word.lower() in common_fragments:
                            print(f"   ⚠️ Razón empieza con fragmento de palabra ({first_word}), skipping: {reason[:60]}")
                            is_invalid = True
                    
                    if is_invalid:
                        continue
                    
                    # VALIDACIÓN: Verificar que el artista NO esté en biblioteca
                    if artist.lower() in library_artists_set:
                        print(f"   ⏭️ Skipping {artist}: ya está en biblioteca")
                        continue
                    
                    # Verificar duplicados
                    track_key = f"{artist.lower()}|{name.lower()}"
                    if track_key in seen_tracks:
                        print(f"   ⚠️ Duplicado detectado, skipping: {artist} - {name}")
                        continue
                    seen_tracks.add(track_key)
                    
                    # Crear objeto Track
                    track = Track(
                        id=f"ai_custom_{artist.replace(' ', '_')}_{name.replace(' ', '_')[:30]}",
                        title=name,
                        artist=artist,
                        album=name if recommendation_type == "album" else "",
                        duration=None,
                        year=None,
                        genre=custom_prompt if custom_prompt else "",
                        play_count=None,
                        path="",
                        cover_url=None
                    )
                    
                    # Limpiar la razón (cortar si es muy larga y agregar ...)
                    if len(reason) > 200:
                        reason = reason[:197] + "..."
                    
                    # Crear recomendación
                    recommendation = Recommendation(
                        track=track,
                        reason=reason,
                        confidence=0.95,  # Alta confianza porque es específico
                        source="AI (Gemini)",
                        tags=["custom", "specific"]
                    )
                    recommendations.append(recommendation)
                    print(f"   ✅ Agregada: {artist} - {name}")
                    print(f"      Razón: {reason[:80]}...")
                    
                except Exception as e:
                    print(f"   ⚠️ Error parseando línea: {line[:100]} | {e}")
                    continue
            
            print(f"🎨 Total recomendaciones personalizadas generadas: {len(recommendations)}")
            
            # Si se generaron recomendaciones usando IA, intentar buscar en MusicBrainz
            # para agregar URLs y más información
            if self.musicbrainz and recommendations:
                print("🔍 Enriqueciendo recomendaciones con datos de MusicBrainz...")
                for rec in recommendations[:limit]:
                    try:
                        # Si es artista, buscar info del artista
                        if recommendation_type == "artist":
                            artist_info = await self.musicbrainz.verify_artist_metadata(rec.track.artist)
                            if artist_info.get("found") and artist_info.get("url"):
                                rec.track.path = artist_info["url"]
                        # Si es álbum, buscar álbumes del artista
                        elif recommendation_type == "album":
                            top_albums = await self.musicbrainz.get_artist_top_albums(rec.track.artist, limit=5)
                            if top_albums:
                                # Buscar el álbum específico o usar el primero
                                for album_data in top_albums:
                                    if rec.track.title.lower() in album_data.get("name", "").lower():
                                        rec.track.path = album_data.get("url", "")
                                        break
                    except Exception as e:
                        print(f"   ⚠️ No se pudo enriquecer {rec.track.artist}: {e}")
                        continue
            
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones personalizadas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_ai_recommendations(
        self, 
        user_profile: UserProfile, 
        analysis: MusicAnalysis, 
        candidate_tracks: List[Track], 
        limit: int
    ) -> List[Recommendation]:
        """Generar recomendaciones usando IA desde la biblioteca del usuario"""
        try:
            # Preparar contexto para la IA
            recent_artists = [track.artist for track in user_profile.recent_tracks[:10]]
            top_artists = [artist.name for artist in user_profile.top_artists[:5]]
            
            # Crear lista de canciones disponibles en la biblioteca
            available_tracks = [f"{t.artist} - {t.title}" for t in candidate_tracks[:50]]
            
            # Crear prompt MUY ESTRICTO para evitar análisis previo
            prompt = f"""TAREA: Recomienda {limit} canciones de la biblioteca del usuario.

PERFIL:
- Top artistas: {', '.join(top_artists[:5])}
- Escucha recientemente: {', '.join(recent_artists[:5])}

CANCIONES DISPONIBLES:
{chr(10).join(available_tracks[:30])}

INSTRUCCIONES:
1. Recomienda {limit} canciones DIFERENTES de la lista
2. NO generes análisis ni explicaciones previas
3. EMPIEZA DIRECTAMENTE con las recomendaciones
4. Basadas en similitud con sus gustos

FORMATO OBLIGATORIO (cada línea):
[Artista] - [Canción] | [Razón de 10-30 palabras con mayúscula inicial y punto final.]

EJEMPLO:
The Beatles - Hey Jude | Clásico del rock con melodías memorables y letras emotivas perfectas para tu gusto por música atemporal.

❌ NO HAGAS:
- Análisis del perfil
- Explicaciones previas
- Introducciones
- Numeración

✅ EMPIEZA DIRECTAMENTE CON LA PRIMERA RECOMENDACIÓN:
"""
            
            # Generar con Gemini con configuración para respuestas predecibles
            generation_config = {
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 600,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            ai_suggestions = response.text.strip()
            
            print(f"📝 Respuesta de IA para biblioteca (longitud: {len(ai_suggestions)})")
            
            # Procesar sugerencias de IA con parseo ROBUSTO
            recommendations = []
            seen_tracks = set()
            
            lines_raw = ai_suggestions.split('\n')
            
            # Filtrar líneas válidas: deben tener formato [ARTISTA] - [CANCIÓN] | [RAZÓN]
            for line in lines_raw:
                if len(recommendations) >= limit:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Remover numeración si existe (1., 2., etc)
                line_clean = re.sub(r'^\d+[\.\)]\s*', '', line)
                
                # DEBE tener - y | para ser válida
                if '-' not in line_clean or '|' not in line_clean:
                    continue
                
                try:
                    # Parsear: [ARTISTA] - [CANCIÓN] | [RAZÓN]
                    parts = line_clean.split('|', 1)
                    if len(parts) != 2:
                        continue
                    
                    artist_and_song = parts[0].strip()
                    reason = parts[1].strip()
                    
                    # VALIDACIONES DE RAZÓN
                    # 1. No debe contener patrones de markdown o análisis
                    if any(pattern in reason for pattern in ['**', '):**', 'céntrico', 'fi:', 'hop:', 'rock:', 'punk:']):
                        print(f"   ⚠️ Razón con patrón inválido, skipping: {reason[:60]}")
                        continue
                    
                    # 2. Debe empezar con mayúscula (no es fragmento de oración)
                    if reason and reason[0].islower():
                        print(f"   ⚠️ Razón empieza con minúscula, skipping: {reason[:60]}")
                        continue
                    
                    # 3. No debe contener frases de análisis
                    if any(phrase in reason.lower() for phrase in ['la lista de', 'el usuario', 'artistas recientes', 'demuestran', 'sugiere', 'análisis', 'perfil']):
                        print(f"   ⚠️ Razón con frase de análisis, skipping: {reason[:60]}")
                        continue
                    
                    # 4. Debe tener longitud razonable
                    if len(reason) < 20 or len(reason.split()) < 8:
                        print(f"   ⚠️ Razón muy corta, skipping: {reason}")
                        continue
                    
                    # 5. Dividir artista y canción
                    if ' - ' not in artist_and_song:
                        continue
                    
                    artist, song = artist_and_song.split(' - ', 1)
                    artist = artist.strip()
                    song = song.strip()
                    
                    if not artist or not song:
                        continue
                    
                    # Verificar duplicados
                    track_key = f"{artist.lower()}|{song.lower()}"
                    if track_key in seen_tracks:
                        continue
                    seen_tracks.add(track_key)
                    
                    # Buscar en la biblioteca
                    matches = await self._find_track_matches(f"{artist} {song}", candidate_tracks)
                    
                    if matches:
                        track = matches[0]
                        
                        # Limpiar la razón (cortar si es muy larga)
                        if len(reason) > 200:
                            reason = reason[:197] + "..."
                        
                        recommendation = Recommendation(
                            track=track,
                            reason=reason,
                            confidence=0.8,
                            source="ai",
                            tags=["ai-recommendation"]
                        )
                        recommendations.append(recommendation)
                        print(f"   ✅ Agregada: {artist} - {song}")
                        
                except Exception as e:
                    print(f"   ⚠️ Error parseando línea: {line_clean[:100]} | {e}")
                    continue
            
            print(f"🎨 Total recomendaciones de biblioteca con IA: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones con IA: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_library_only_recommendations(
        self,
        user_profile: UserProfile,
        analysis: MusicAnalysis,
        limit: int,
        recommendation_type: str = "general",
        genre_filter: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> List[Recommendation]:
        """Generar recomendaciones SOLO de la biblioteca del usuario
        
        Útil para redescubrir música que ya tiene pero no ha escuchado recientemente.
        
        Args:
            user_profile: Perfil del usuario
            analysis: Análisis musical del usuario
            limit: Número de recomendaciones
            recommendation_type: 'general', 'album', 'artist', 'track'
            genre_filter: Filtro de género si se especifica
            custom_prompt: Criterio específico del usuario
        """
        try:
            print(f"📚 Buscando recomendaciones en tu biblioteca de Navidrome...")
            
            # Preparar contexto del usuario
            recent_artists = [track.artist for track in user_profile.recent_tracks[:15]]
            top_artists = [artist.name for artist in user_profile.top_artists[:10]]
            
            # Obtener música de la biblioteca según el tipo
            if recommendation_type == "album":
                # Obtener álbumes
                library_items = await self.navidrome.get_albums(limit=500)
                item_type = "álbumes"
            elif recommendation_type == "artist":
                # Obtener artistas
                library_items = await self.navidrome.get_artists(limit=500)
                item_type = "artistas"
            else:
                # Obtener tracks por defecto
                library_items = await self.navidrome.get_tracks(limit=500)
                item_type = "canciones"
            
            # Filtrar por género si se especifica
            if genre_filter:
                print(f"   Filtrando por género: {genre_filter}")
                filtered_items = []
                for item in library_items:
                    # Buscar en el género del item
                    item_genre = getattr(item, 'genre', '').lower() if hasattr(item, 'genre') else ''
                    if genre_filter.lower() in item_genre:
                        filtered_items.append(item)
                
                if filtered_items:
                    library_items = filtered_items
                    print(f"   Encontrados {len(filtered_items)} {item_type} de género '{genre_filter}'")
                else:
                    print(f"   ⚠️ No se encontraron {item_type} del género '{genre_filter}', usando toda la biblioteca")
            
            # Filtrar música que NO ha escuchado recientemente (para redescubrir)
            recent_track_names = {track.name.lower() for track in user_profile.recent_tracks[:50]}
            recent_artist_names = {track.artist.lower() for track in user_profile.recent_tracks[:50]}
            
            rediscovery_items = []
            for item in library_items:
                # Para tracks: excluir si ya lo escuchó recientemente
                if recommendation_type == "track" or recommendation_type == "general":
                    item_name = getattr(item, 'title', getattr(item, 'name', '')).lower()
                    if item_name not in recent_track_names:
                        rediscovery_items.append(item)
                # Para álbumes/artistas: excluir si escuchó mucho de ese artista recientemente
                elif recommendation_type == "album":
                    item_artist = getattr(item, 'artist', '').lower()
                    # Permitir si no ha escuchado mucho de ese artista (max 3 veces en recientes)
                    recent_count = sum(1 for t in user_profile.recent_tracks[:50] if t.artist.lower() == item_artist)
                    if recent_count < 3:
                        rediscovery_items.append(item)
                elif recommendation_type == "artist":
                    item_artist = getattr(item, 'name', '').lower()
                    recent_count = sum(1 for t in user_profile.recent_tracks[:50] if t.artist.lower() == item_artist)
                    if recent_count < 3:
                        rediscovery_items.append(item)
            
            print(f"   📊 Total en biblioteca: {len(library_items)} {item_type}")
            print(f"   🔍 Para redescubrir (no escuchados recientemente): {len(rediscovery_items)} {item_type}")
            
            # Si no hay suficientes items para redescubrir, usar toda la biblioteca
            if len(rediscovery_items) < limit:
                print(f"   ⚠️ Pocos items para redescubrir, usando toda la biblioteca")
                candidate_items = library_items
            else:
                candidate_items = rediscovery_items
            
            # Crear lista formateada de items disponibles
            # OPTIMIZACIÓN: Reducir a 30 items para evitar bloqueos de seguridad de Gemini
            available_items_list = []
            for item in candidate_items[:30]:  # Limitar a 30 para evitar bloqueos
                if recommendation_type == "album":
                    available_items_list.append(f"{item.artist} - {item.name}")
                elif recommendation_type == "artist":
                    available_items_list.append(f"{item.name}")
                else:  # track
                    artist = getattr(item, 'artist', 'Unknown')
                    title = getattr(item, 'title', 'Unknown')
                    available_items_list.append(f"{artist} - {title}")
            
            # Construir prompt para IA
            criteria = custom_prompt if custom_prompt else f"música que disfrutes basada en tus gustos"
            if genre_filter:
                criteria = f"música de género {genre_filter}"
            
            prompt = f"""TAREA: Recomienda {limit} {item_type} de la biblioteca del usuario.

PERFIL DEL USUARIO:
- Top artistas: {', '.join(top_artists[:5])}
- Escucha recientemente: {', '.join(recent_artists[:5])}

CRITERIO: {criteria}

{item_type.upper()} DISPONIBLES EN BIBLIOTECA:
{chr(10).join(available_items_list[:30])}

INSTRUCCIONES:
1. Recomienda {limit} {item_type} DIFERENTES de la lista
2. Prioriza música que coincida con el criterio y el perfil del usuario
3. NO generes análisis ni explicaciones previas
4. EMPIEZA DIRECTAMENTE con las recomendaciones

FORMATO OBLIGATORIO (cada línea):
"""
            
            if recommendation_type == "artist":
                prompt += "[Artista] | [Razón de 10-30 palabras con mayúscula inicial y punto final.]"
            else:
                prompt += "[Artista] - [Nombre] | [Razón de 10-30 palabras con mayúscula inicial y punto final.]"
            
            prompt += """

EJEMPLO:
Pink Floyd - Wish You Were Here | Rock progresivo atmosférico con guitarras emotivas y letras introspectivas perfectas para momentos reflexivos.

❌ NO HAGAS:
- Análisis del perfil
- Explicaciones previas
- Introducciones
- Numeración

✅ EMPIEZA DIRECTAMENTE:
"""
            
            # Generar con Gemini
            generation_config = {
                'temperature': 0.8,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 800,
            }
            
            # Intentar generar respuesta con manejo de bloqueo de seguridad
            try:
                response = self.model.generate_content(prompt, generation_config=generation_config)
                ai_response = response.text.strip()
                print(f"📝 Respuesta de IA recibida (longitud: {len(ai_response)})")
            except ValueError as e:
                # Si fue bloqueado por seguridad, intentar con prompt más simple
                if "finish_reason" in str(e) or "response.text" in str(e):
                    print(f"⚠️ Respuesta bloqueada por filtros de seguridad de Gemini")
                    print(f"   Reintentando con prompt simplificado...")
                    
                    # Prompt mucho más simple sin listas largas
                    simple_prompt = f"""Recomienda {limit} {item_type} de música para redescubrir.

PERFIL: Escucha {', '.join(top_artists[:3])}
CRITERIO: {criteria}
TIPO: {item_type}

FORMATO (cada línea):"""
                    
                    if recommendation_type == "artist":
                        simple_prompt += "\n[Artista] | [Razón corta]"
                    else:
                        simple_prompt += "\n[Artista] - [Nombre] | [Razón corta]"
                    
                    simple_prompt += "\n\nEMPIEZA DIRECTAMENTE:"
                    
                    try:
                        response = self.model.generate_content(simple_prompt, generation_config=generation_config)
                        ai_response = response.text.strip()
                        print(f"📝 Respuesta de IA recibida con prompt simple (longitud: {len(ai_response)})")
                    except:
                        print(f"❌ Fallo también con prompt simple, usando fallback básico")
                        # Fallback: recomendar aleatoriamente de los candidatos
                        return await self._generate_random_library_recommendations(
                            candidate_items, limit, recommendation_type
                        )
                else:
                    raise
            
            # Parsear recomendaciones
            recommendations = []
            seen_items = set()
            
            lines_raw = ai_response.split('\n')
            
            for line in lines_raw:
                if len(recommendations) >= limit:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Remover numeración
                line_clean = re.sub(r'^\d+[\.\)]\s*', '', line)
                
                # Para artistas, el formato es diferente
                if recommendation_type == "artist":
                    # Formato: [Artista] | [Razón]
                    if '|' not in line_clean:
                        continue
                else:
                    # Formato: [Artista] - [Nombre] | [Razón]
                    if '-' not in line_clean or '|' not in line_clean:
                        continue
                
                try:
                    parts = line_clean.split('|', 1)
                    if len(parts) != 2:
                        continue
                    
                    item_info = parts[0].strip()
                    reason = parts[1].strip()
                    
                    # Validaciones de razón (igual que antes)
                    if any(pattern in reason for pattern in ['**', '):**', ':**', '*:', 'céntrico', 'fi:', 'hop:', 'rock:', 'punk:', 'jazz:', 'pop:', 'metal:']):
                        continue
                    if reason and reason[0].islower():
                        continue
                    if len(reason) < 20 or len(reason.split()) < 8:
                        continue
                    
                    # Parsear según tipo
                    if recommendation_type == "artist":
                        artist_name = item_info
                        item_key = artist_name.lower()
                        
                        # Buscar artista en la biblioteca
                        matching_item = None
                        for item in candidate_items:
                            if item.name.lower() == artist_name.lower():
                                matching_item = item
                                break
                        
                        if matching_item and item_key not in seen_items:
                            seen_items.add(item_key)
                            # Convertir a Track para el formato de Recommendation
                            track = Track(
                                id=matching_item.id,
                                title=f"Descubre {matching_item.name}",
                                artist=matching_item.name,
                                album="",
                                duration=None,
                                year=None,
                                genre=getattr(matching_item, 'genre', ''),
                                play_count=getattr(matching_item, 'play_count', None),
                                path=getattr(matching_item, 'path', ''),
                                cover_url=getattr(matching_item, 'cover_url', None)
                            )
                            recommendations.append(Recommendation(
                                track=track,
                                reason=reason,
                                confidence=0.85,
                                source="biblioteca",
                                tags=["library-recommendation", "rediscovery"]
                            ))
                    
                    else:
                        # Para álbumes y tracks
                        if ' - ' not in item_info:
                            continue
                        
                        artist, name = item_info.split(' - ', 1)
                        artist = artist.strip()
                        name = name.strip()
                        
                        item_key = f"{artist.lower()}|{name.lower()}"
                        
                        if item_key in seen_items:
                            continue
                        seen_items.add(item_key)
                        
                        # Buscar en biblioteca
                        matching_item = None
                        for item in candidate_items:
                            item_artist = getattr(item, 'artist', '')
                            item_name = getattr(item, 'name', getattr(item, 'title', ''))
                            
                            if (item_artist.lower() == artist.lower() and 
                                item_name.lower() == name.lower()):
                                matching_item = item
                                break
                        
                        if matching_item:
                            # Convertir a Track
                            if recommendation_type == "album":
                                track = Track(
                                    id=matching_item.id,
                                    title=matching_item.name,
                                    artist=matching_item.artist,
                                    album=matching_item.name,
                                    duration=None,
                                    year=getattr(matching_item, 'year', None),
                                    genre=getattr(matching_item, 'genre', ''),
                                    play_count=getattr(matching_item, 'play_count', None),
                                    path=getattr(matching_item, 'path', ''),
                                    cover_url=getattr(matching_item, 'cover_url', None),
                                    track_count=getattr(matching_item, 'track_count', None)
                                )
                            else:  # track
                                track = matching_item
                            
                            if len(reason) > 200:
                                reason = reason[:197] + "..."
                            
                            recommendations.append(Recommendation(
                                track=track,
                                reason=reason,
                                confidence=0.85,
                                source="biblioteca",
                                tags=["library-recommendation", "rediscovery"]
                            ))
                            print(f"   ✅ Agregada: {artist} - {name}")
                
                except Exception as e:
                    print(f"   ⚠️ Error parseando línea: {line_clean[:100]} | {e}")
                    continue
            
            print(f"📚 Total recomendaciones de biblioteca: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones de biblioteca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_random_library_recommendations(
        self,
        candidate_items: List,
        limit: int,
        recommendation_type: str
    ) -> List[Recommendation]:
        """Generar recomendaciones aleatorias de biblioteca como fallback
        
        Usado cuando la IA falla o es bloqueada por filtros de seguridad.
        
        Args:
            candidate_items: Lista de items disponibles en biblioteca
            limit: Número de recomendaciones
            recommendation_type: Tipo de recomendación
            
        Returns:
            Lista de recomendaciones aleatorias
        """
        print(f"🎲 Generando {limit} recomendaciones aleatorias de biblioteca (fallback)")
        
        recommendations = []
        
        # Seleccionar items aleatorios
        import random
        selected_items = random.sample(candidate_items, min(limit, len(candidate_items)))
        
        for item in selected_items:
            try:
                # Convertir a Track según el tipo
                if recommendation_type == "artist":
                    track = Track(
                        id=item.id,
                        title=f"Descubre {item.name}",
                        artist=item.name,
                        album="",
                        duration=None,
                        year=None,
                        genre=getattr(item, 'genre', ''),
                        play_count=getattr(item, 'play_count', None),
                        path=getattr(item, 'path', ''),
                        cover_url=getattr(item, 'cover_url', None)
                    )
                    reason = f"Artista de tu biblioteca que no has escuchado recientemente."
                elif recommendation_type == "album":
                    track = Track(
                        id=item.id,
                        title=item.name,
                        artist=item.artist,
                        album=item.name,
                        duration=None,
                        year=getattr(item, 'year', None),
                        genre=getattr(item, 'genre', ''),
                        play_count=getattr(item, 'play_count', None),
                        path=getattr(item, 'path', ''),
                        cover_url=getattr(item, 'cover_url', None),
                        track_count=getattr(item, 'track_count', None)
                    )
                    reason = f"Álbum de {item.artist} que no has escuchado recientemente."
                else:  # track
                    track = item
                    reason = f"Canción de {item.artist} que no has escuchado recientemente."
                
                recommendations.append(Recommendation(
                    track=track,
                    reason=reason,
                    confidence=0.7,
                    source="biblioteca",
                    tags=["library-recommendation", "random"]
                ))
            except Exception as e:
                print(f"   ⚠️ Error creando recomendación aleatoria: {e}")
                continue
        
        print(f"🎲 Generadas {len(recommendations)} recomendaciones aleatorias")
        return recommendations
    
    async def _generate_similarity_recommendations(
        self, 
        user_profile: UserProfile, 
        candidate_tracks: List[Track], 
        limit: int
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en similitud"""
        try:
            # Obtener artistas favoritos
            favorite_artists = set()
            for track in user_profile.recent_tracks:
                favorite_artists.add(track.artist.lower())
            
            for artist in user_profile.top_artists:
                favorite_artists.add(artist.name.lower())
            
            # Buscar canciones de artistas similares o del mismo género
            recommendations = []
            
            for track in candidate_tracks:
                if len(recommendations) >= limit:
                    break
                
                # Similitud por artista
                if track.artist.lower() in favorite_artists:
                    recommendation = Recommendation(
                        track=track,
                        reason=f"Artista favorito: {track.artist}",
                        confidence=0.9,
                        source="similarity",
                        tags=["favorite-artist"]
                    )
                    recommendations.append(recommendation)
                
                # Similitud por género (simulado)
                elif await self._is_similar_genre(track, user_profile):
                    recommendation = Recommendation(
                        track=track,
                        reason=f"Género similar a tus gustos",
                        confidence=0.7,
                        source="similarity",
                        tags=["similar-genre"]
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            print(f"Error generando recomendaciones por similitud: {e}")
            return []
    
    async def _extract_genre(self, artist: str, track: str) -> Optional[str]:
        """Extraer género de una canción (simulado)"""
        # En un caso real, usarías APIs como Spotify, MusicBrainz, etc.
        genre_mapping = {
            "rock": ["rock", "metal", "punk", "grunge"],
            "pop": ["pop", "indie pop", "synthpop"],
            "electronic": ["electronic", "techno", "house", "ambient"],
            "jazz": ["jazz", "blues", "soul"],
            "classical": ["classical", "orchestral", "chamber"],
            "hip-hop": ["hip-hop", "rap", "trap"]
        }
        
        # Búsqueda simple por palabras clave
        text = f"{artist} {track}".lower()
        for genre, keywords in genre_mapping.items():
            if any(keyword in text for keyword in keywords):
                return genre
        
        return "unknown"
    
    def _analyze_time_patterns(self, tracks: List[ScrobbleTrack]) -> Dict[str, int]:
        """Analizar patrones temporales de escucha"""
        time_patterns = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
        
        for track in tracks:
            if track.date:
                hour = track.date.hour
                if 6 <= hour < 12:
                    time_patterns["morning"] += 1
                elif 12 <= hour < 17:
                    time_patterns["afternoon"] += 1
                elif 17 <= hour < 22:
                    time_patterns["evening"] += 1
                else:
                    time_patterns["night"] += 1
        
        return time_patterns
    
    async def _analyze_mood_patterns(self, tracks: List[ScrobbleTrack]) -> Dict[str, float]:
        """Analizar patrones de humor musical"""
        # Simulación de análisis de humor
        return {
            "energetic": 0.4,
            "melancholic": 0.3,
            "peaceful": 0.2,
            "aggressive": 0.1
        }
    
    def _calculate_discovery_rate(self, user_profile: UserProfile) -> float:
        """Calcular tasa de descubrimiento de nueva música"""
        if not user_profile.recent_tracks:
            return 0.0
        
        # Contar artistas únicos en las últimas 50 canciones
        recent_artists = set()
        for track in user_profile.recent_tracks[:50]:
            recent_artists.add(track.artist)
        
        # Comparar con artistas conocidos
        known_artists = set()
        for artist in user_profile.top_artists:
            known_artists.add(artist.name)
        
        new_artists = recent_artists - known_artists
        return len(new_artists) / len(recent_artists) if recent_artists else 0.0
    
    async def _find_track_matches(self, artist_song: str, tracks: List[Track]) -> List[Track]:
        """Buscar coincidencias de canciones en la biblioteca"""
        matches = []
        search_terms = artist_song.lower().split()
        
        for track in tracks:
            track_text = f"{track.artist} {track.title}".lower()
            if any(term in track_text for term in search_terms):
                matches.append(track)
        
        return matches[:3]  # Máximo 3 coincidencias
    
    async def _is_similar_genre(self, track: Track, user_profile: UserProfile) -> bool:
        """Determinar si una canción es de un género similar"""
        # Simulación simple
        user_genres = set()
        for track_data in user_profile.recent_tracks:
            genre = await self._extract_genre(track_data.artist, track_data.name)
            if genre:
                user_genres.add(genre)
        
        track_genre = await self._extract_genre(track.artist, track.title)
        return track_genre in user_genres
    
    async def generate_library_playlist(
        self,
        description: str,
        limit: int = 15
    ) -> List[Recommendation]:
        """Generar playlist SOLO de la biblioteca local
        
        Args:
            description: Descripción de lo que busca el usuario
            limit: Número de canciones (puede ser sobrescrito si se detecta en la descripción)
            
        Returns:
            Lista de recomendaciones de la biblioteca
        """
        try:
            print(f"📚 Generando playlist de biblioteca: {description}")
            
            # PASO 0: Detectar cantidad solicitada en la descripción (si existe)
            detected_count = self._extract_song_count(description)
            if detected_count:
                limit = detected_count
                print(f"✨ Usando cantidad detectada de la descripción: {limit} canciones")
            
            # PASO 0.5: Obtener géneros disponibles en la biblioteca para mapeo inteligente
            available_genres = await self._get_available_genres()
            print(f"🎭 Géneros disponibles en biblioteca: {len(available_genres)}")
            
            # PASO 1: Intentar detectar nombres de artistas específicos
            artist_names = self._extract_artist_names(description)
            all_tracks = []
            seen_ids = set()
            
            print(f"🔍 Análisis de descripción: '{description}'")
            print(f"   Artistas detectados: {artist_names if artist_names else 'Ninguno'}")
            
            if artist_names:
                print(f"🎤 Artistas detectados: {artist_names}")
                print(f"🎯 Modo: Playlist específica de artista(s)")
                
                # Buscar canciones específicas de esos artistas
                for artist_name in artist_names:
                    print(f"   🔍 Buscando canciones de '{artist_name}'...")
                    results = await self.navidrome.search(artist_name, limit=100)
                    
                    print(f"      Resultados búsqueda: {len(results.get('tracks', []))} tracks, {len(results.get('albums', []))} albums, {len(results.get('artists', []))} artists")
                    
                    # Priorizar tracks del artista exacto
                    matches_found = 0
                    for track in results.get('tracks', []):
                        if track.id not in seen_ids:
                            # Verificar si es del artista (coincidencia flexible)
                            if artist_name.lower() in track.artist.lower() or track.artist.lower() in artist_name.lower():
                                all_tracks.append(track)
                                seen_ids.add(track.id)
                                matches_found += 1
                    
                    print(f"      ✓ {matches_found} canciones coinciden con el artista")
                    
                    # También agregar de álbumes
                    for album in results.get('albums', []):
                        if artist_name.lower() in album.artist.lower():
                            # Buscar tracks del álbum
                            album_tracks = await self.navidrome.search(f"{album.artist} {album.name}", limit=30)
                            for track in album_tracks.get('tracks', []):
                                if track.id not in seen_ids:
                                    all_tracks.append(track)
                                    seen_ids.add(track.id)
                
                print(f"✅ Encontradas {len(all_tracks)} canciones de los artistas especificados")
                
                # Si encontramos canciones del artista, NO buscar más
                # Solo crear playlist con canciones de ese artista
                if len(all_tracks) > 0:
                    print(f"🎵 Playlist exclusiva de {', '.join(artist_names)}")
                    # Saltar a la selección final
                    if len(all_tracks) >= limit:
                        # Tenemos suficientes canciones del artista
                        selected = self._smart_track_selection(
                            all_tracks, 
                            artist_names,
                            limit, 
                            description
                        )
                        
                        recommendations = [
                            Recommendation(
                                track=track,
                                reason=f"Canción de {track.artist}",
                                confidence=0.9,
                                source="library"
                            ) for track in selected
                        ]
                        
                        print(f"🎵 Generadas {len(recommendations)} recomendaciones de biblioteca")
                        return recommendations
                    else:
                        print(f"⚠️ Solo {len(all_tracks)} canciones encontradas del artista")
                        # Si hay pocas, devolver todas las que hay
                        recommendations = [
                            Recommendation(
                                track=track,
                                reason=f"Canción de {track.artist}",
                                confidence=0.9,
                                source="library"
                            ) for track in all_tracks
                        ]
                        print(f"🎵 Generadas {len(recommendations)} recomendaciones de biblioteca")
                        return recommendations
            
            # PASO 2: Si no hay artistas específicos o no se encontraron suficientes, buscar por género/keywords
            if len(all_tracks) < limit:
                # Intentar detectar género musical con mapeo inteligente
                genres_detected = self._extract_genres(description)
                if genres_detected:
                    print(f"🎸 Géneros detectados: {genres_detected}")
                    
                    # Filtrar solo los géneros que realmente existen en la biblioteca
                    valid_genres = [g for g in genres_detected if g in available_genres]
                    if valid_genres:
                        print(f"✅ Géneros válidos en biblioteca: {valid_genres}")
                        
                        # ESTRATEGIA 1: Buscar por género usando getRandomSongs
                        for genre in valid_genres:
                            try:
                                print(f"   🔍 Buscando por género '{genre}' con getRandomSongs...")
                                genre_tracks = await self.navidrome.get_tracks(limit=100, genre=genre)
                                added_count = 0
                                for track in genre_tracks:
                                    if track.id not in seen_ids:
                                        all_tracks.append(track)
                                        seen_ids.add(track.id)
                                        added_count += 1
                                print(f"   ✓ Género '{genre}' (getRandomSongs): {added_count} canciones nuevas")
                            except Exception as e:
                                print(f"   ⚠️ Error con getRandomSongs para '{genre}': {e}")
                        
                        # ESTRATEGIA 2: Buscar por género usando search (más robusto)
                        for genre in valid_genres:
                            try:
                                print(f"   🔍 Buscando por género '{genre}' con search...")
                                search_results = await self.navidrome.search(genre, limit=100)
                                added_count = 0
                                for track in search_results.get('tracks', []):
                                    if track.id not in seen_ids:
                                        # Verificar que el género coincida (filtro más flexible)
                                        if track.genre and (
                                            genre.lower() in track.genre.lower() or 
                                            track.genre.lower() in genre.lower() or
                                            any(word in track.genre.lower() for word in genre.lower().split())
                                        ):
                                            all_tracks.append(track)
                                            seen_ids.add(track.id)
                                            added_count += 1
                                print(f"   ✓ Género '{genre}' (search): {added_count} canciones nuevas")
                            except Exception as e:
                                print(f"   ⚠️ Error con search para '{genre}': {e}")
                        
                        # ESTRATEGIA 2.5: Si no encuentra nada, buscar sin filtro de género
                        if len(all_tracks) < 10:
                            print(f"   🔄 Pocas canciones encontradas, buscando sin filtro de género...")
                            for genre in valid_genres:
                                try:
                                    search_results = await self.navidrome.search(genre, limit=50)
                                    added_count = 0
                                    for track in search_results.get('tracks', []):
                                        if track.id not in seen_ids:
                                            all_tracks.append(track)
                                            seen_ids.add(track.id)
                                            added_count += 1
                                    print(f"   ✓ Género '{genre}' (sin filtro): {added_count} canciones nuevas")
                                except Exception as e:
                                    print(f"   ⚠️ Error sin filtro para '{genre}': {e}")
                        
                        # ESTRATEGIA 2.75: Si aún hay pocas canciones, usar MusicBrainz
                        if len(all_tracks) < 15 and self.musicbrainz:
                            print(f"   🎯 Pocas canciones encontradas ({len(all_tracks)}), activando MusicBrainz...")
                            
                            # Extraer filtros adicionales de la descripción
                            additional_filters = self._extract_filters_from_description(description)
                            
                            # Usar MusicBrainz para cada género válido
                            for genre in valid_genres[:2]:  # Limitar a 2 géneros para no tardar mucho
                                mb_tracks = await self._find_genre_artists_with_musicbrainz(
                                    genre,
                                    additional_filters,
                                    max_artists=50
                                )
                                
                                for track in mb_tracks:
                                    if track.id not in seen_ids:
                                        all_tracks.append(track)
                                        seen_ids.add(track.id)
                                
                                if mb_tracks:
                                    print(f"   ✅ MusicBrainz agregó {len(mb_tracks)} canciones para '{genre}'")
                    else:
                        print(f"⚠️ Ninguno de los géneros detectados existe literalmente en la biblioteca")
                        print(f"   Detectados: {genres_detected}")
                        print(f"   Disponibles: {list(available_genres)[:10]}...")
                        
                        # ESTRATEGIA INTELIGENTE: Usar IA para identificar artistas del género solicitado
                        print(f"🤖 Usando IA para identificar artistas que coinciden con el género solicitado...")
                        ai_matched_tracks = await self._ai_match_artists_by_genre(
                            description, 
                            genres_detected,
                            limit=200
                        )
                        
                        for track in ai_matched_tracks:
                            if track.id not in seen_ids:
                                all_tracks.append(track)
                                seen_ids.add(track.id)
                        
                        print(f"   ✅ IA identificó {len(ai_matched_tracks)} canciones del género solicitado")
                        
                        # ESTRATEGIA MUSICBRAINZ: Si aún hay pocas canciones, usar MusicBrainz como complemento
                        if len(all_tracks) < 20 and self.musicbrainz:
                            print(f"   🎯 Complementando con MusicBrainz ({len(all_tracks)} canciones hasta ahora)...")
                            
                            # Extraer filtros adicionales de la descripción
                            additional_filters = self._extract_filters_from_description(description)
                            
                            # Usar MusicBrainz para cada género detectado
                            for genre in genres_detected[:2]:  # Limitar a 2 géneros
                                mb_tracks = await self._find_genre_artists_with_musicbrainz(
                                    genre,
                                    additional_filters,
                                    max_artists=50
                                )
                                
                                for track in mb_tracks:
                                    if track.id not in seen_ids:
                                        all_tracks.append(track)
                                        seen_ids.add(track.id)
                                
                                if mb_tracks:
                                    print(f"   ✅ MusicBrainz agregó {len(mb_tracks)} canciones para '{genre}'")
                
                # ESTRATEGIA 3: Buscar por keywords generales
                keywords = self._extract_keywords(description)
                print(f"🔑 Palabras clave extraídas: {keywords}")
                
                for keyword in keywords[:3]:  # Usar hasta 3 keywords
                    try:
                        print(f"   🔍 Buscando por keyword '{keyword}'...")
                        results = await self.navidrome.search(keyword, limit=50)
                        added_count = 0
                        for track in results.get('tracks', []):
                            if track.id not in seen_ids:
                                all_tracks.append(track)
                                seen_ids.add(track.id)
                                added_count += 1
                        print(f"   ✓ Keyword '{keyword}': {added_count} canciones nuevas")
                    except Exception as e:
                        print(f"   ⚠️ Error buscando keyword '{keyword}': {e}")
            
            # PASO 3: Si no hay artistas específicos, obtener una muestra grande de la biblioteca
            # para que el algoritmo de selección tenga suficiente material
            # IMPORTANTE: Solo agregar si no hay suficientes canciones ya
            if not artist_names and len(all_tracks) < limit * 2:
                # Sin artistas específicos, necesitamos una muestra grande para seleccionar
                target_pool_size = max(200, limit * 5)  # Al menos 5x el límite solicitado
                print(f"🎲 Sin artistas específicos y pocas canciones ({len(all_tracks)}): obteniendo {target_pool_size} aleatorias...")
                random_tracks = await self.navidrome.get_tracks(limit=target_pool_size)
                for track in random_tracks:
                    if track.id not in seen_ids:
                        all_tracks.append(track)
                        seen_ids.add(track.id)
                print(f"✅ Agregadas {len(random_tracks)} canciones aleatorias")
            elif not artist_names:
                print(f"✅ Ya hay {len(all_tracks)} canciones, no se agregan aleatorias")
            
            # PASO 4: Si aún no hay suficientes (caso con artistas específicos), completar
            elif len(all_tracks) < limit * 2:
                print(f"⚠️ Solo {len(all_tracks)} canciones de artistas específicos, complementando...")
                additional = max(100, limit * 2)
                random_tracks = await self.navidrome.get_tracks(limit=additional)
                for track in random_tracks:
                    if track.id not in seen_ids:
                        all_tracks.append(track)
                        seen_ids.add(track.id)
            
            # PASO 5: FALLBACK AGRESIVO - Si aún no hay suficientes canciones, obtener más
            if len(all_tracks) < limit:
                print(f"🚨 FALLBACK: Solo {len(all_tracks)} canciones encontradas, obteniendo más...")
                # Intentar obtener más canciones aleatorias
                fallback_tracks = await self.navidrome.get_tracks(limit=300)
                for track in fallback_tracks:
                    if track.id not in seen_ids:
                        all_tracks.append(track)
                        seen_ids.add(track.id)
                print(f"✅ Fallback agregó {len(fallback_tracks)} canciones más")
            
            print(f"📊 Total de canciones disponibles antes de filtrado: {len(all_tracks)}")
            
            if not all_tracks:
                print("❌ No se encontraron canciones en la biblioteca")
                return []
            
            # POST-FILTRADO: Aplicar filtro de idioma si se especificó
            description_lower = description.lower()
            if 'español' in description_lower or 'castellano' in description_lower:
                print(f"🇪🇸 Aplicando filtro de idioma ESPAÑOL...")
                all_tracks = self._filter_by_language(all_tracks, 'spanish')
                print(f"   ✅ Quedan {len(all_tracks)} canciones en español")
            elif 'inglés' in description_lower or 'english' in description_lower:
                print(f"🇬🇧 Aplicando filtro de idioma INGLÉS...")
                all_tracks = self._filter_by_language(all_tracks, 'english')
                print(f"   ✅ Quedan {len(all_tracks)} canciones en inglés")
            
            if not all_tracks:
                print("❌ No quedan canciones después del filtrado de idioma")
                return []
            
            print(f"📊 Total de canciones disponibles después de filtrado: {len(all_tracks)}")
            
            # NUEVO ALGORITMO: Selección con diversidad garantizada de artistas
            selected_tracks = self._smart_track_selection(
                all_tracks,
                artist_names,
                limit,
                description
            )
            
            # Crear recomendaciones
            recommendations = []
            for track in selected_tracks:
                rec = Recommendation(
                    track=track,
                    reason=f"De tu biblioteca: coincide con '{description}'",
                    confidence=0.90,  # Alta confianza porque es de la biblioteca
                    source="biblioteca",
                    tags=["local", "biblioteca"]
                )
                recommendations.append(rec)
            
            print(f"🎵 Generadas {len(recommendations)} recomendaciones de biblioteca")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando playlist de biblioteca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _smart_track_selection(
        self,
        all_tracks: List[Track],
        artist_names: List[str],
        limit: int,
        description: str
    ) -> List[Track]:
        """Selección inteligente de canciones con garantía de diversidad de artistas
        
        Args:
            all_tracks: Lista completa de canciones disponibles
            artist_names: Lista de artistas detectados en la descripción
            limit: Número de canciones a seleccionar
            description: Descripción original de la playlist
            
        Returns:
            Lista de tracks seleccionadas con buena diversidad
        """
        import random
        from collections import defaultdict
        
        print(f"🎯 Seleccionando {limit} canciones con diversidad de artistas...")
        
        # Si no hay artistas específicos y hay muchas canciones, pre-filtrar con IA
        if not artist_names and len(all_tracks) > limit * 3:
            print(f"🤖 Usando IA para pre-filtrar canciones relevantes...")
            all_tracks = self._ai_filter_tracks(all_tracks, description, limit * 3)
            print(f"✅ Pre-filtradas a {len(all_tracks)} canciones más relevantes")
        
        # Agrupar canciones por artista
        tracks_by_artist = defaultdict(list)
        for track in all_tracks:
            artist_key = track.artist.lower() if track.artist else "unknown"
            tracks_by_artist[artist_key].append(track)
        
        print(f"📊 Canciones agrupadas en {len(tracks_by_artist)} artistas diferentes")
        
        # Si hay artistas específicos solicitados, dar prioridad equitativa
        if artist_names:
            print(f"🎤 Distribuyendo equitativamente entre {len(artist_names)} artistas: {artist_names}")
            
            # Calcular cuántas canciones por artista
            songs_per_artist = max(1, limit // len(artist_names))
            remaining = limit % len(artist_names)
            
            selected = []
            artist_count = defaultdict(int)
            
            # Primera pasada: asignar songs_per_artist a cada artista
            for artist_name in artist_names:
                artist_lower = artist_name.lower()
                
                # Buscar el grupo de canciones que coincida con este artista
                matching_tracks = []
                for artist_key, tracks in tracks_by_artist.items():
                    if artist_lower in artist_key or artist_key in artist_lower:
                        matching_tracks.extend(tracks)
                
                if matching_tracks:
                    # Aleatorizar y tomar songs_per_artist
                    random.shuffle(matching_tracks)
                    to_take = min(songs_per_artist, len(matching_tracks))
                    selected.extend(matching_tracks[:to_take])
                    artist_count[artist_lower] = to_take
                    print(f"   ✓ {artist_name}: {to_take} canciones")
                else:
                    print(f"   ✗ {artist_name}: no se encontraron canciones")
            
            # Segunda pasada: rellenar con canciones adicionales si hay espacio
            if len(selected) < limit and remaining > 0:
                # Tomar más canciones de los artistas que tienen más disponibles
                for artist_name in artist_names:
                    if len(selected) >= limit:
                        break
                    
                    artist_lower = artist_name.lower()
                    matching_tracks = []
                    for artist_key, tracks in tracks_by_artist.items():
                        if artist_lower in artist_key or artist_key in artist_lower:
                            # Excluir canciones ya seleccionadas
                            for track in tracks:
                                if track not in selected:
                                    matching_tracks.append(track)
                    
                    if matching_tracks:
                        random.shuffle(matching_tracks)
                        additional = min(1, len(matching_tracks), limit - len(selected))
                        selected.extend(matching_tracks[:additional])
                        print(f"   + {artist_name}: +{additional} adicional(es)")
            
            # Aleatorizar el orden final para mezclar mejor
            random.shuffle(selected)
            
            print(f"✅ Seleccionadas {len(selected)} canciones con distribución equitativa")
            return selected[:limit]
        
        else:
            # No hay artistas específicos: selección por diversidad general
            print(f"🎲 Selección diversificada sin artistas específicos")
            
            # Calcular máximo de canciones por artista (evitar que un artista domine)
            max_per_artist = max(2, limit // max(5, len(tracks_by_artist) // 3))
            
            selected = []
            artist_usage = defaultdict(int)
            
            # Crear lista de todos los artistas disponibles
            available_artists = list(tracks_by_artist.keys())
            random.shuffle(available_artists)
            
            # Iterar round-robin por los artistas
            round_num = 0
            while len(selected) < limit and round_num < 10:  # Max 10 rondas para evitar loop infinito
                added_this_round = False
                
                for artist_key in available_artists:
                    if len(selected) >= limit:
                        break
                    
                    # Verificar si este artista aún puede aportar canciones
                    if artist_usage[artist_key] < max_per_artist:
                        artist_tracks = tracks_by_artist[artist_key]
                        
                        # Buscar una canción que no hayamos usado
                        for track in artist_tracks:
                            if track not in selected:
                                selected.append(track)
                                artist_usage[artist_key] += 1
                                added_this_round = True
                                break
                
                if not added_this_round:
                    # No se agregó nada en esta ronda, salir del loop
                    break
                
                round_num += 1
            
            # Aleatorizar el orden final
            random.shuffle(selected)
            
            # Mostrar estadísticas
            artists_used = len([count for count in artist_usage.values() if count > 0])
            print(f"✅ Seleccionadas {len(selected)} canciones de {artists_used} artistas diferentes")
            print(f"   Promedio: {len(selected)/artists_used:.1f} canciones por artista")
            
            return selected[:limit]
    
    def _ai_filter_tracks(
        self,
        tracks: List[Track],
        description: str,
        target_count: int
    ) -> List[Track]:
        """Usar IA para filtrar canciones relevantes basándose en la descripción
        
        Args:
            tracks: Lista completa de canciones
            description: Descripción de lo que se busca
            target_count: Número aproximado de canciones a mantener
            
        Returns:
            Lista filtrada de canciones más relevantes
        """
        import random
        
        try:
            # Limitar a un máximo razonable para la IA
            sample_size = min(len(tracks), 100)
            sampled_tracks = random.sample(tracks, sample_size) if len(tracks) > sample_size else tracks
            
            # Formatear para la IA
            tracks_text = ""
            for i, track in enumerate(sampled_tracks):
                genre_text = f" [{track.genre}]" if track.genre else ""
                year_text = f" ({track.year})" if track.year else ""
                tracks_text += f"{i}. {track.artist} - {track.title}{genre_text}{year_text}\n"
            
            # Detectar especificaciones en la descripción
            description_lower = description.lower()
            special_instructions = []
            
            # Detectar idioma
            if 'español' in description_lower or 'castellano' in description_lower:
                special_instructions.append("CRÍTICO: Solo canciones en ESPAÑOL (artistas españoles o latinoamericanos). RECHAZA artistas anglosajones como Pink Floyd, Oasis en inglés, Prodigy, etc.")
            elif 'inglés' in description_lower or 'english' in description_lower:
                special_instructions.append("CRÍTICO: Solo canciones en INGLÉS. RECHAZA artistas hispanos.")
            
            # Detectar década/año
            decades = ['60', '70', '80', '90', '2000', '2010', '2020']
            for decade in decades:
                if decade in description_lower or f'{decade}s' in description_lower:
                    special_instructions.append(f"CRÍTICO: Priorizar música de los años {decade}")
            
            # Detectar características especiales
            if 'acústic' in description_lower:
                special_instructions.append("IMPORTANTE: Preferir versiones acústicas o unplugged")
            if 'en vivo' in description_lower or 'live' in description_lower:
                special_instructions.append("IMPORTANTE: Preferir grabaciones en vivo")
            if 'relajant' in description_lower or 'chill' in description_lower or 'tranquil' in description_lower:
                special_instructions.append("IMPORTANTE: Música relajante, tempo lento")
            if 'energétic' in description_lower or 'enérgic' in description_lower or 'rock duro' in description_lower:
                special_instructions.append("IMPORTANTE: Música energética, tempo rápido")
            
            special_text = "\n".join([f"⚠️ {inst}" for inst in special_instructions]) if special_instructions else ""
            
            # Log de especificaciones detectadas
            if special_instructions:
                print(f"🎯 Especificaciones detectadas:")
                for inst in special_instructions:
                    print(f"   • {inst}")
            
            prompt = f"""Analiza esta lista de canciones y selecciona las que mejor coincidan con: "{description}"

{special_text}

Canciones disponibles:
{tracks_text}

INSTRUCCIONES:
1. Selecciona las {min(target_count, sample_size)} canciones que MEJOR se ajusten a la descripción
2. Si hay instrucciones CRÍTICAS arriba, DEBES seguirlas estrictamente - NO INCLUYAS canciones que las violen
3. Considera: género, estilo, IDIOMA del artista (español vs inglés), época según la descripción
4. IDIOMA: Si pide español, RECHAZA totalmente artistas que cantan en inglés (Pink Floyd, The Police, etc.)
5. IDIOMA: Si pide inglés, RECHAZA totalmente artistas hispanos
6. Prioriza DIVERSIDAD de artistas (máximo 2-3 canciones por artista)
7. Responde SOLO con los números separados por comas
8. Ejemplo: 1,5,8,12,15,20,23,27,30,35,40,42,45,48,50

Selecciona ahora (máximo {min(target_count, sample_size)} canciones):"""

            response = self.model.generate_content(prompt)
            selected_indices = self._parse_selection(response.text)
            
            # Construir lista de canciones seleccionadas
            filtered = []
            for idx in selected_indices:
                if idx < len(sampled_tracks):
                    filtered.append(sampled_tracks[idx])
            
            # Si quedaron muy pocas, agregar más aleatorias
            if len(filtered) < target_count // 2:
                remaining = [t for t in tracks if t not in filtered]
                additional_needed = min(target_count - len(filtered), len(remaining))
                filtered.extend(random.sample(remaining, additional_needed))
            
            return filtered
            
        except Exception as e:
            print(f"⚠️ Error en filtrado por IA: {e}")
            # Fallback: devolver muestra aleatoria
            return random.sample(tracks, min(target_count, len(tracks)))
    
    def _extract_artist_names(self, text: str) -> List[str]:
        """Extraer nombres de artistas de una descripción
        
        Detecta nombres de artistas en formatos como:
        - "música de mujeres, vera fauna y cala vento"
        - "playlist con Pink Floyd, Queen y The Beatles"
        - "canciones de Extremoduro"
        
        Args:
            text: Texto con posibles nombres de artistas
            
        Returns:
            Lista de nombres de artistas detectados
        """
        import re
        
        artists = []
        
        # Palabras que indican que lo siguiente es un artista
        artist_indicators = ['de', 'con', 'música de', 'canciones de', 'temas de']
        
        # ESTRATEGIA 1: Detectar listas separadas por comas
        # "mujeres, vera fauna y cala vento" → ["mujeres", "vera fauna", "cala vento"]
        # Buscar patrones después de palabras indicadoras
        for indicator in artist_indicators:
            pattern = rf'{indicator}\s+(.+?)(?:\s+para|\s+de\s+los|\.|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                artists_text = match.group(1)
                # Dividir por comas, "y", "&"
                parts = re.split(r',|\s+y\s+|\s+&\s+', artists_text)
                for part in parts:
                    # Limpiar espacios
                    part = part.strip()
                    # Remover palabras comunes al inicio/final
                    part = re.sub(r'^(la|el|los|las|un|una)\s+', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'\s+(para|con|de)$', '', part, flags=re.IGNORECASE)
                    if part and len(part) > 2:
                        artists.append(part)
        
        # ESTRATEGIA 2: Usar IA para detectar nombres de artistas en texto ambiguo
        # Si no hay artistas o el texto parece ser un nombre de artista completo
        if not artists and len(text.strip()) < 50:
            # Si el texto completo (sin palabras de comando) parece ser un artista
            text_clean = text.lower()
            
            # Remover palabras de comando Y géneros comunes
            remove_words = [
                'playlist', 'lista', 'música', 'canciones', 'de', 'con',
                'en español', 'español', 'castellano', 
                'en ingles', 'inglés', 'english',
                'rock', 'indie', 'pop', 'jazz', 'blues', 'metal', 
                'punk', 'folk', 'electronic', 'rap', 'reggae',
                'acústico', 'en vivo', 'live', 'relajante', 'energético'
            ]
            
            for word in remove_words:
                text_clean = text_clean.replace(word, ' ')
            text_clean = ' '.join(text_clean.split())  # Normalizar espacios
            
            # Si queda algo significativo después de quitar géneros/idiomas
            # Podría ser un nombre de artista
            # Criterios: más de 2 caracteres Y (más de 2 palabras O más de 8 caracteres)
            # Y no contiene números (que indicarían cantidad de canciones)
            text_clean = text_clean.strip()
            word_count = len(text_clean.split())
            char_count = len(text_clean)
            
            if text_clean and not any(char.isdigit() for char in text_clean):
                # Casos válidos:
                # - Nombres largos: "el mató a un policía motorizado" (3+ palabras)
                # - Nombres cortos pero únicos: "oasis", "queen", "muse" (1 palabra pero >2 chars)
                if word_count >= 3 or (word_count >= 1 and char_count > 3):
                    # Podría ser un nombre de artista
                    print(f"🤔 Texto ambiguo, podría ser nombre de artista: '{text_clean}'")
                    artists.append(text_clean)
        
        # ESTRATEGIA 3: Detectar nombres propios (palabras con mayúscula)
        # Solo si aún no se encontraron artistas
        if not artists:
            # Buscar secuencias de palabras que empiezan con mayúscula
            capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            cap_matches = re.findall(capitalized_pattern, text)
            
            # Filtrar palabras comunes que suelen ir con mayúscula
            common_words = {'Playlist', 'Lista', 'Música', 'Canciones', 'Album', 'Disco'}
            for match in cap_matches:
                if match not in common_words and len(match) > 2:
                    artists.append(match)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_artists = []
        for artist in artists:
            artist_lower = artist.lower()
            if artist_lower not in seen:
                seen.add(artist_lower)
                unique_artists.append(artist)
        
        if unique_artists:
            print(f"🎤 Nombres de artistas extraídos: {unique_artists}")
        
        return unique_artists
    
    def _extract_song_count(self, text: str) -> Optional[int]:
        """Extraer cantidad de canciones solicitada en la descripción
        
        Detecta formatos como:
        - "20 canciones"
        - "15 temas"
        - "10 tracks"
        - "playlist de 25 canciones"
        
        Args:
            text: Texto de la descripción
            
        Returns:
            Número de canciones solicitadas, o None si no se especifica
        """
        import re
        
        # Patrones para detectar cantidad de canciones
        patterns = [
            r'(\d+)\s*(?:canciones|cancion|temas|tema|tracks|track|songs|song)',
            r'(?:de|con)\s*(\d+)\s*(?:canciones|cancion|temas|tema|tracks|track)',
            r'playlist\s*(?:de|con)?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                # Validar que sea un número razonable (entre 5 y 200)
                if 5 <= count <= 200:
                    print(f"🔢 Cantidad detectada: {count} canciones")
                    return count
        
        return None
    
    def _extract_genres(self, text: str) -> List[str]:
        """Extraer géneros musicales de la descripción con mapeo inteligente
        
        Args:
            text: Texto de la descripción
            
        Returns:
            Lista de géneros musicales detectados
        """
        text_lower = text.lower()
        
        # Mapeo inteligente de géneros con relaciones y variaciones
        # Cada entrada mapea a géneros reales que pueden existir en la biblioteca
        genre_mappings = {
            # ROCK y variaciones (usando nombres exactos de la biblioteca)
            'rock': [
                'Rock', 'Alternative', 'Alternativ und Indie', 'Alternatif et Indé'
            ],
            
            # INDIE y variaciones (usando nombres exactos de la biblioteca)
            'indie': [
                'Alternative', 'Alternativ und Indie', 'Alternatif et Indé'
            ],
            
            # POP
            'pop': ['Pop'],
            
            # JAZZ
            'jazz': ['Jazz'],
            
            # BLUES
            'blues': ['Blues'],
            
            # METAL
            'metal': ['Metal', 'Heavy Metal'],
            
            # PUNK
            'punk': ['Punk'],
            
            # FOLK
            'folk': ['Folk'],
            
            # ELECTRÓNICA
            'electronic': ['Electronica', 'Electronic'],
            
            # HIP HOP / RAP
            'hip hop': ['Hip-Hop', 'Rap'],
            'rap': ['Hip-Hop', 'Rap'],
            
            # REGGAE
            'reggae': ['Reggae'],
            
            # COUNTRY
            'country': ['Country'],
            
            # CLÁSICA
            'classical': ['Classical'],
            
            # ALTERNATIVO (mapea a varios géneros relacionados)
            'alternative': [
                'Alternative', 'Alternativ und Indie', 'Alternatif et Indé'
            ],
            
            # SKA
            'ska': ['Ska'],
            
            # SOUL
            'soul': ['Soul'],
            
            # FUNK
            'funk': ['Funk'],
            
            # DISCO
            'disco': ['Disco'],
            
            # GRUNGE
            'grunge': ['Grunge'],
            
            # PROGRESSIVE
            'progressive': ['Progressive'],
            
            # FLAMENCO
            'flamenco': ['Flamenco'],
            
            # LATIN
            'latin': ['Latin'],
            
            # SALSA
            'salsa': ['Salsa'],
            
            # RUMBA
            'rumba': ['Rumba'],
            
            # WORLD MUSIC
            'world': ['World Music'],
            
            # OTHER
            'other': ['Other'],
        }
        
        detected_genres = []
        
        # Buscar coincidencias en el texto (más flexible)
        for requested_genre, possible_genres in genre_mappings.items():
            # Buscar el género en el texto (más flexible)
            if (requested_genre in text_lower or 
                f" {requested_genre} " in text_lower or
                text_lower.startswith(requested_genre) or
                text_lower.endswith(requested_genre) or
                f"canciones de {requested_genre}" in text_lower or
                f"música de {requested_genre}" in text_lower or
                f"playlist de {requested_genre}" in text_lower):
                # Agregar todos los géneros relacionados que podrían existir en la biblioteca
                detected_genres.extend(possible_genres)
                print(f"🎸 Género '{requested_genre}' detectado → mapea a: {possible_genres}")
        
        # Eliminar duplicados manteniendo orden
        unique_genres = []
        seen = set()
        for genre in detected_genres:
            if genre not in seen:
                unique_genres.append(genre)
                seen.add(genre)
        
        return unique_genres
    
    async def _get_available_genres(self) -> set:
        """Obtener todos los géneros disponibles en la biblioteca
        
        Returns:
            Set con todos los géneros únicos disponibles
        """
        try:
            # Obtener una muestra grande de canciones para extraer géneros
            tracks = await self.navidrome.get_tracks(limit=500)
            
            genres = set()
            for track in tracks:
                if track.genre:
                    # Limpiar y normalizar el género
                    genre = track.genre.strip()
                    if genre:
                        genres.add(genre)
            
            print(f"🎭 Encontrados {len(genres)} géneros únicos en biblioteca")
            return genres
            
        except Exception as e:
            print(f"⚠️ Error obteniendo géneros disponibles: {e}")
            # Fallback: géneros comunes
            return {
                'rock', 'pop', 'jazz', 'blues', 'metal', 'punk', 'folk', 
                'electronic', 'hip-hop', 'rap', 'reggae', 'country', 
                'classical', 'alternative', 'indie', 'world music'
            }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extraer palabras clave de una descripción
        
        Args:
            text: Texto del que extraer keywords
            
        Returns:
            Lista de palabras clave
        """
        import re
        
        # Remover palabras comunes (stop words en español)
        stop_words = {
            'de', 'la', 'el', 'para', 'con', 'los', 'las', 'un', 'una',
            'del', 'al', 'y', 'o', 'en', 'a', 'por', 'que', 'es', 'su',
            'música', 'canciones', 'canción', 'playlist', 'lista', 'haz', 'hacer'
        }
        
        # Extraer palabras
        words = re.findall(r'\w+', text.lower())
        
        # Filtrar stop words y palabras muy cortas
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Limitar a las primeras 5 palabras clave más relevantes
        return keywords[:5]
    
    def _format_tracks_for_ai(self, tracks: List[Track]) -> str:
        """Formatear tracks para que la IA los pueda leer y seleccionar
        
        Args:
            tracks: Lista de tracks
            
        Returns:
            String formateado con la lista de tracks
        """
        formatted = ""
        for i, track in enumerate(tracks):
            formatted += f"{i}. {track.artist} - {track.title}"
            if track.album:
                formatted += f" (Álbum: {track.album})"
            if track.genre:
                formatted += f" [Género: {track.genre}]"
            if track.year:
                formatted += f" ({track.year})"
            formatted += "\n"
        return formatted
    
    async def _ai_match_artists_by_genre(
        self,
        description: str,
        genres: List[str],
        limit: int = 200
    ) -> List[Track]:
        """Usar IA para identificar artistas que coinciden con un género solicitado
        
        Cuando el género no existe literalmente en los metadatos, la IA usa su
        conocimiento musical para identificar qué artistas de la biblioteca
        pertenecen a ese género.
        
        Args:
            description: Descripción original de la playlist
            genres: Lista de géneros solicitados
            limit: Número máximo de canciones a obtener
            
        Returns:
            Lista de tracks de artistas que coinciden con el género
        """
        try:
            # Obtener una muestra grande y diversa de la biblioteca
            sample_size = min(500, limit * 3)
            print(f"   📚 Obteniendo muestra de {sample_size} canciones de la biblioteca...")
            library_tracks = await self.navidrome.get_tracks(limit=sample_size)
            
            if not library_tracks:
                return []
            
            # Extraer artistas únicos
            artists_map = {}
            for track in library_tracks:
                artist = track.artist
                if artist not in artists_map:
                    artists_map[artist] = []
                artists_map[artist].append(track)
            
            artists_list = list(artists_map.keys())
            print(f"   🎤 {len(artists_list)} artistas únicos en la muestra")
            
            # Crear prompt para la IA
            genres_text = ', '.join(genres)
            artists_text = '\n'.join([f"{i}. {artist}" for i, artist in enumerate(artists_list[:100])])
            
            # Detectar si hay especificación de idioma
            description_lower = description.lower()
            language_filter = ""
            if 'español' in description_lower or 'castellano' in description_lower:
                language_filter = "\n⚠️ CRÍTICO: El usuario pidió música en ESPAÑOL. RECHAZA artistas que cantan en inglés (Pink Floyd, The Police, Oasis, Radiohead, etc.). SOLO artistas españoles o latinoamericanos."
            elif 'inglés' in description_lower or 'english' in description_lower:
                language_filter = "\n⚠️ CRÍTICO: El usuario pidió música en INGLÉS. RECHAZA artistas hispanos."
            
            prompt = f"""Eres un experto en música con conocimiento enciclopédico de todos los géneros musicales.

TAREA: Identifica qué artistas de esta lista pertenecen a los géneros: {genres_text}

CONTEXTO: El usuario pidió "{description}"{language_filter}

ARTISTAS DISPONIBLES:
{artists_text}

INSTRUCCIONES:
1. Analiza cada artista y determina si pertenece a los géneros solicitados
2. Usa tu conocimiento musical sobre cada artista (nacionalidad, idioma en que canta, estilo)
3. Considera sub-géneros y géneros relacionados
4. Si hay filtro de IDIOMA arriba (⚠️ CRÍTICO), es OBLIGATORIO seguirlo - rechaza artistas del idioma incorrecto
5. Selecciona SOLO los artistas que cumplan TODOS los criterios (género + idioma si aplica)
6. Responde SOLO con los números de los artistas seleccionados, separados por comas

EJEMPLO: 5,12,23,34,45,67,89

Números de artistas que coinciden:"""

            # Generar con IA
            response = self.model.generate_content(prompt)
            selected_indices = self._parse_selection(response.text)
            
            # Construir lista de tracks de los artistas seleccionados
            matched_tracks = []
            selected_artists = set()
            
            for idx in selected_indices:
                if idx < len(artists_list):
                    artist = artists_list[idx]
                    selected_artists.add(artist)
                    # Agregar todas las canciones de este artista
                    matched_tracks.extend(artists_map[artist])
            
            print(f"   🎯 IA seleccionó {len(selected_artists)} artistas: {list(selected_artists)[:5]}...")
            
            return matched_tracks[:limit]
            
        except Exception as e:
            print(f"   ⚠️ Error en matching por IA: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _filter_by_language(self, tracks: List[Track], language: str) -> List[Track]:
        """Filtrar canciones por idioma del artista usando conocimiento de la IA
        
        Args:
            tracks: Lista de canciones a filtrar
            language: 'spanish' o 'english'
            
        Returns:
            Lista de canciones del idioma solicitado
        """
        try:
            # Extraer artistas únicos
            artists = list(set([track.artist for track in tracks if track.artist]))
            
            if not artists:
                return tracks
            
            print(f"   🎤 Filtrando {len(artists)} artistas por idioma {language}...")
            
            # Preparar prompt para la IA
            artists_text = '\n'.join([f"{i}. {artist}" for i, artist in enumerate(artists[:150])])
            
            language_name = "ESPAÑOL" if language == "spanish" else "INGLÉS"
            reject_examples = "Pink Floyd, The Police, Oasis, Radiohead, The Beatles" if language == "spanish" else "Extremoduro, Vetusta Morla, Los Planetas"
            
            prompt = f"""Eres un experto en música mundial. Identifica qué artistas cantan en {language_name}.

ARTISTAS:
{artists_text}

CRITERIOS:
- Si {language_name} = ESPAÑOL: Solo artistas de España o Latinoamérica que cantan en español
- Si {language_name} = INGLÉS: Solo artistas anglosajones o que cantan en inglés
- RECHAZA completamente: {reject_examples}
- Usa tu conocimiento sobre la nacionalidad e idioma de cada artista

INSTRUCCIONES:
Responde SOLO con los números de los artistas que cantan en {language_name}, separados por comas.

Ejemplo: 1,5,8,12,23,34,56,78,90

Números de artistas en {language_name}:"""

            response = self.model.generate_content(prompt)
            selected_indices = self._parse_selection(response.text)
            
            # Crear set de artistas válidos
            valid_artists = set()
            for idx in selected_indices:
                if idx < len(artists):
                    valid_artists.add(artists[idx].lower())
            
            print(f"   ✓ {len(valid_artists)} artistas válidos en {language_name}: {list(valid_artists)[:5]}...")
            
            # Filtrar canciones
            filtered_tracks = []
            for track in tracks:
                if track.artist and track.artist.lower() in valid_artists:
                    filtered_tracks.append(track)
            
            return filtered_tracks
            
        except Exception as e:
            print(f"   ⚠️ Error filtrando por idioma: {e}")
            # Si falla, devolver todas
            return tracks
    
    async def _find_genre_artists_with_musicbrainz(
        self,
        genre: str,
        additional_filters: Optional[Dict[str, Any]] = None,
        max_artists: int = 50
    ) -> List[Track]:
        """Usar MusicBrainz para identificar artistas del género en la biblioteca
        
        Se usa cuando la búsqueda local no encuentra resultados para un género.
        
        Args:
            genre: Género musical a buscar
            additional_filters: Filtros adicionales (country, year_from, year_to)
            max_artists: Máximo de artistas a verificar
            
        Returns:
            Lista de tracks de artistas que cumplen
        """
        if not self.musicbrainz:
            print("   ⚠️ MusicBrainz no disponible")
            return []
        
        try:
            print(f"🎯 MusicBrainz: Buscando artistas de '{genre}' en tu biblioteca...")
            
            # Paso 1: Obtener lista de artistas de la biblioteca
            print(f"   📚 Obteniendo artistas de la biblioteca...")
            library_tracks = await self.navidrome.get_tracks(limit=500)
            
            # Extraer artistas únicos
            unique_artists = list(set([track.artist for track in library_tracks if track.artist]))
            print(f"   🎤 {len(unique_artists)} artistas únicos en biblioteca")
            
            # Paso 2: Preparar filtros para MusicBrainz
            filters = {"genre": genre}
            if additional_filters:
                filters.update(additional_filters)
            
            # Paso 3: Consultar MusicBrainz para identificar cuáles son del género
            matching_artists_data = await self.musicbrainz.find_matching_artists_in_library(
                unique_artists,
                filters,
                max_artists=max_artists
            )
            
            if not matching_artists_data:
                print(f"   ❌ Ningún artista de tu biblioteca cumple con '{genre}'")
                return []
            
            # Extraer nombres de artistas que coinciden
            matching_artist_names = set([a["name"].lower() for a in matching_artists_data])
            print(f"   ✅ Artistas coincidentes: {list(matching_artist_names)}")
            
            # Paso 4: Filtrar tracks solo de esos artistas
            matching_tracks = []
            for track in library_tracks:
                if track.artist and track.artist.lower() in matching_artist_names:
                    matching_tracks.append(track)
            
            print(f"   🎵 {len(matching_tracks)} canciones de {len(matching_artist_names)} artistas verificados")
            
            return matching_tracks
            
        except Exception as e:
            print(f"   ❌ Error en búsqueda con MusicBrainz: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_filters_from_description(self, description: str) -> Dict[str, Any]:
        """Extraer filtros estructurados de la descripción
        
        Ejemplos:
            "indie español de los 2000" → {genre: "indie", country: "ES", year_from: 2000, year_to: 2009}
            "rock británico de los 70" → {genre: "rock", country: "GB", year_from: 1970, year_to: 1979}
        """
        import re
        
        filters = {}
        desc_lower = description.lower()
        
        # Detectar país/idioma
        country_map = {
            "español": "ES", "española": "ES", "castellano": "ES",
            "británico": "GB", "británica": "GB", "inglés": "GB", "inglesa": "GB",
            "americano": "US", "americana": "US",
            "francés": "FR", "francesa": "FR",
            "italiano": "IT", "italiana": "IT",
            "alemán": "DE", "alemana": "DE"
        }
        
        for keyword, country_code in country_map.items():
            if keyword in desc_lower:
                filters["country"] = country_code
                break
        
        # Detectar década
        decade_patterns = [
            (r'(de los |años? )?(60|60s|sesentas?)', 1960, 1969),
            (r'(de los |años? )?(70|70s|setentas?)', 1970, 1979),
            (r'(de los |años? )?(80|80s|ochentas?)', 1980, 1989),
            (r'(de los |años? )?(90|90s|noventas?)', 1990, 1999),
            (r'(de los |años? )?(2000|2000s|dos mil)', 2000, 2009),
            (r'(de los |años? )?(2010|2010s)', 2010, 2019),
        ]
        
        for pattern, year_from, year_to in decade_patterns:
            if re.search(pattern, desc_lower):
                filters["year_from"] = year_from
                filters["year_to"] = year_to
                break
        
        return filters
    
    def _parse_selection(self, text: str) -> List[int]:
        """Parsear la selección de índices de la IA
        
        Args:
            text: Texto de respuesta de la IA
            
        Returns:
            Lista de índices seleccionados
        """
        import re
        
        # Buscar todos los números en el texto
        numbers = re.findall(r'\d+', text)
        
        # Convertir a enteros
        indices = [int(n) for n in numbers if int(n) < 1000]  # Filtrar números muy grandes
        
        return indices
    
    async def process_recommendation_feedback(
        self, 
        user_id: int, 
        recommendation_id: str, 
        feedback_type: str,
        recommendation_context: Dict[str, Any] = None
    ):
        """Procesar feedback del usuario sobre una recomendación"""
        try:
            await adaptive_learning_system.process_feedback(
                user_id=user_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                context=recommendation_context
            )
            logger.debug(f"📚 Feedback procesado: {user_id} - {feedback_type}")
        except Exception as e:
            logger.error(f"❌ Error procesando feedback: {e}")
    
    async def get_personalized_weights(self, user_id: int, features: Dict[str, Any]) -> Dict[str, float]:
        """Obtener pesos personalizados para recomendaciones basados en aprendizaje"""
        try:
            return adaptive_learning_system.get_recommendation_weights(user_id, features)
        except Exception as e:
            logger.error(f"❌ Error obteniendo pesos personalizados: {e}")
            return {}
    
    async def get_user_learning_insights(self, user_id: int) -> Dict[str, Any]:
        """Obtener insights de aprendizaje del usuario"""
        try:
            return adaptive_learning_system.get_user_insights(user_id)
        except Exception as e:
            logger.error(f"❌ Error obteniendo insights de aprendizaje: {e}")
            return {"error": str(e)}
    
    async def _apply_learning_weights(
        self, 
        recommendations: List[Recommendation], 
        user_id: int
    ) -> List[Recommendation]:
        """Aplicar pesos de aprendizaje a las recomendaciones"""
        try:
            if not recommendations:
                return recommendations
            
            # Obtener pesos personalizados
            weights = await self.get_personalized_weights(user_id, {})
            
            if not weights:
                return recommendations
            
            # Aplicar pesos a las recomendaciones
            for rec in recommendations:
                # Extraer características de la recomendación
                features = {
                    'artist': rec.track.artist,
                    'genre': getattr(rec.track, 'genre', ''),
                    'mood': getattr(rec, 'mood', ''),
                    'activity': getattr(rec, 'activity', '')
                }
                
                # Calcular peso personalizado
                personalized_weight = 0.0
                for feature, value in features.items():
                    if value and feature in weights:
                        personalized_weight += weights[feature]
                
                # Ajustar confianza con peso personalizado
                if personalized_weight > 0:
                    rec.confidence = min(1.0, rec.confidence * (1 + personalized_weight * 0.3))
                
                # Agregar información de personalización
                rec.tags.append(f"personalized:{personalized_weight:.2f}")
            
            # Reordenar por confianza ajustada
            recommendations.sort(key=lambda x: x.confidence, reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error aplicando pesos de aprendizaje: {e}")
            return recommendations
    
    async def generate_hybrid_recommendations(
        self, 
        user_profile: UserProfile, 
        user_id: int,
        max_recommendations: int = 20,
        strategy_preferences: Optional[Dict[str, float]] = None
    ) -> List[Recommendation]:
        """Generar recomendaciones usando el motor híbrido"""
        try:
            # Convertir preferencias de estrategia si es necesario
            strategy_weights = None
            if strategy_preferences:
                strategy_weights = {}
                for strategy_name, weight in strategy_preferences.items():
                    try:
                        strategy_enum = RecommendationStrategy(strategy_name)
                        strategy_weights[strategy_enum] = weight
                    except ValueError:
                        logger.warning(f"⚠️ Estrategia desconocida: {strategy_name}")
            
            # Generar recomendaciones híbridas
            hybrid_scores = await self.hybrid_engine.generate_hybrid_recommendations(
                user_profile, user_id, max_recommendations, strategy_weights
            )
            
            # Convertir a formato Recommendation
            recommendations = []
            for score in hybrid_scores:
                recommendation = Recommendation(
                    track=score.track,
                    confidence=score.confidence,
                    reasoning=score.reasoning,
                    tags=[f"hybrid:{score.strategy.value}", f"score:{score.score:.2f}"]
                )
                
                # Agregar metadatos
                if score.metadata:
                    recommendation.tags.extend([f"{k}:{v}" for k, v in score.metadata.items()])
                
                recommendations.append(recommendation)
            
            logger.info(f"✅ Generadas {len(recommendations)} recomendaciones híbridas")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones híbridas: {e}")
            # Fallback a recomendaciones normales
            return await self.generate_recommendations(user_profile)
    
    async def analyze_advanced_user_profile(
        self, 
        user_profile: UserProfile, 
        user_id: int,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analizar perfil avanzado del usuario"""
        try:
            return await advanced_personalization_system.analyze_user_profile(
                user_profile, user_id, context_data
            )
        except Exception as e:
            logger.error(f"❌ Error analizando perfil avanzado: {e}")
            return {"error": str(e)}
    
    async def get_contextual_recommendations(
        self, 
        user_id: int, 
        context: str,
        available_tracks: List[Track]
    ) -> List[Track]:
        """Obtener recomendaciones contextuales"""
        try:
            return advanced_personalization_system.get_contextual_recommendations(
                user_id, context, available_tracks
            )
        except Exception as e:
            logger.error(f"❌ Error obteniendo recomendaciones contextuales: {e}")
            return []
    
    def get_hybrid_engine_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del motor híbrido"""
        try:
            return self.hybrid_engine.get_engine_stats()
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas del motor híbrido: {e}")
            return {"error": str(e)}
    
    def get_personalization_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema de personalización"""
        try:
            return advanced_personalization_system.get_system_stats()
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de personalización: {e}")
            return {"error": str(e)}
    
    async def discover_new_music(self, user_profile: UserProfile, user_id: int, 
                               discovery_type: str = 'mixed') -> List[Recommendation]:
        """Descubrir nueva música usando el sistema de características"""
        try:
            return await user_features_system.discover_music(user_profile, user_id, discovery_type)
        except Exception as e:
            logger.error(f"❌ Error descubriendo música: {e}")
            return []
    
    def track_user_activity(self, user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
        """Rastrear actividad del usuario para gamificación"""
        try:
            user_features_system.track_user_activity(user_id, activity_type, metadata)
        except Exception as e:
            logger.error(f"❌ Error rastreando actividad: {e}")
    
    def get_user_profile_enhanced(self, user_id: int) -> Dict[str, Any]:
        """Obtener perfil mejorado del usuario con gamificación"""
        try:
            return user_features_system.get_user_profile_enhanced(user_id)
        except Exception as e:
            logger.error(f"❌ Error obteniendo perfil mejorado: {e}")
            return {"error": str(e)}
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener tabla de clasificación de usuarios"""
        try:
            return user_features_system.get_leaderboard(limit)
        except Exception as e:
            logger.error(f"❌ Error obteniendo leaderboard: {e}")
            return []
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obtener estado de salud del sistema"""
        try:
            return advanced_monitoring_system.get_system_health()
        except Exception as e:
            logger.error(f"❌ Error obteniendo salud del sistema: {e}")
            return {"error": str(e)}
    
    def get_detailed_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener métricas detalladas del sistema"""
        try:
            return advanced_monitoring_system.get_detailed_metrics(hours)
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas detalladas: {e}")
            return {"error": str(e)}
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener estadísticas de errores"""
        try:
            return error_recovery_system.get_error_stats(hours)
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de errores: {e}")
            return {"error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado de salud completo"""
        try:
            return error_recovery_system.get_health_status()
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de salud: {e}")
            return {"error": str(e)}