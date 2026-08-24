"""
MusicAgentService: agente conversacional único con function calling (Gemini).

Sustituye el pipeline anterior (recolección de contexto en 3 niveles por
keywords + un prompt-monolito con ~40 reglas IF/THEN + una heurística de
~950 líneas de regex/scoring para extraer canciones de playlist a partir
del texto del usuario) por un bucle de tool-calling: el modelo decide qué
herramientas llamar (biblioteca, historial, similares, releases, crear
playlist) y redacta él mismo toda la respuesta final, con una sola
personalidad y memoria de conversación nativa.

Nota SDK: usa `google-genai` (no `google-generativeai`, descontinuado el
30-nov-2025). El *automatic function calling* de `google-genai` solo
soporta funciones síncronas; como toda la app es async (`httpx.AsyncClient`
en cada servicio), aquí se implementa un bucle manual de tool-calling con
`client.aio.models.generate_content`.
"""
import os
import asyncio
import logging
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.koito_service import KoitoService
from services.musicbrainz_service import MusicBrainzService
from services.setlistfm_service import SetlistfmService
from services.conversation_manager import ConversationManager
from services.system_prompts import SystemPrompts

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"
MAX_TOOL_TURNS = 6            # tope de seguridad al bucle de tool-calling
QUERY_TIMEOUT_SECONDS = 60.0  # cubre varios turnos de LLM + tools reales (red incluida), no solo recolección de datos


class MusicAgentService:
    """
    Agente musical conversacional: una sola personalidad, tools reales sobre
    Navidrome/ListenBrainz(o Koito)/MusicBrainz, y memoria de conversación nativa.
    """

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.conversation_manager = ConversationManager()

        # Servicios de datos (mismo patrón de inicialización que antes)
        self.navidrome = NavidromeService()

        self.koito = None
        self.listenbrainz = None
        history_service_configured = False

        if os.getenv("KOITO_URL"):
            try:
                self.koito = KoitoService()
                logger.info("✅ Agente musical: Koito configurado")
                history_service_configured = True
            except Exception as e:
                logger.warning(f"⚠️ Agente musical: Error inicializando Koito: {e}")

        if not history_service_configured and os.getenv("LISTENBRAINZ_USERNAME"):
            try:
                self.listenbrainz = ListenBrainzService()
                logger.info("✅ Agente musical: ListenBrainz configurado")
                history_service_configured = True
            except Exception as e:
                logger.warning(f"⚠️ Agente musical: Error inicializando ListenBrainz: {e}")

        # HISTORIAL Y DESCUBRIMIENTO: Koito si está configurado, si no ListenBrainz.
        # Mismo shape de datos en ambos - las tools de abajo no distinguen cuál es.
        if self.koito:
            self.history_service = self.koito
            self.history_service_name = "Koito"
            self.discovery_service = self.koito
        elif self.listenbrainz:
            self.history_service = self.listenbrainz
            self.history_service_name = "ListenBrainz"
            self.discovery_service = self.listenbrainz
        else:
            self.history_service = None
            self.history_service_name = None
            self.discovery_service = None

        # MUSICBRAINZ: metadatos, similares, lanzamientos
        self.musicbrainz = None
        if os.getenv("ENABLE_MUSICBRAINZ", "true").lower() == "true":
            try:
                self.musicbrainz = MusicBrainzService()
                logger.info("✅ Agente musical: MusicBrainz habilitado")
            except Exception as e:
                logger.warning(f"⚠️ Agente musical: Error inicializando MusicBrainz: {e}")

        # SETLIST.FM: crear playlists a partir de un concierto. Se instancia siempre
        # (no hace I/O en el constructor); las tools que lo usan solo se registran
        # si hay API key configurada, igual que con historial/musicbrainz.
        self.setlistfm = SetlistfmService()

        logger.info(f"📊 Servicio de historial: {self.history_service_name or 'No disponible'}")

        self._last_playlist_created: Optional[Dict[str, Any]] = None
        self._current_session = None  # sesión de la consulta en curso (ver query()), para que
        # _tool_crear_playlist/_tool_actualizar_playlist compartan la "playlist activa"

        # Registro de tools disponibles según qué servicios están configurados
        self._tool_impl: Dict[str, Any] = {}
        self._tool_declarations: List[types.FunctionDeclaration] = []
        self._register_tools()

    # ------------------------------------------------------------------
    # Registro de herramientas
    # ------------------------------------------------------------------

    def _register_tools(self):
        """Declara qué funciones puede llamar el modelo, según qué servicios están disponibles."""

        def add(name: str, description: str, properties: Dict[str, types.Schema], required: List[str], impl):
            self._tool_declarations.append(types.FunctionDeclaration(
                name=name,
                description=description,
                parameters=types.Schema(type=types.Type.OBJECT, properties=properties, required=required),
            ))
            self._tool_impl[name] = impl

        # Biblioteca (Navidrome) - siempre disponible
        add(
            "buscar_biblioteca",
            "Busca canciones, álbumes y artistas en la biblioteca musical del usuario (Navidrome) por "
            "TEXTO LITERAL (título, artista o álbum) - solo encuentra algo si ese texto aparece de "
            "verdad en un nombre. NO sirve para pedir un estilo/género/mood ('indie rock español', "
            "'música para estudiar') - eso nunca va a coincidir con ningún título/artista/álbum real. "
            "Para estilo/género usa listar_generos + filtrar_biblioteca en su lugar.",
            {
                "consulta": types.Schema(type=types.Type.STRING, description="Texto a buscar"),
                "limite": types.Schema(type=types.Type.INTEGER, description="Máx. resultados por categoría (default 20)"),
            },
            ["consulta"],
            self._tool_buscar_biblioteca,
        )
        add(
            "listar_generos",
            "Lista los géneros que existen DE VERDAD en la biblioteca del usuario, con cuántas "
            "canciones tiene cada uno (ordenados de más a menos). Llama a esta tool ANTES de "
            "filtrar_biblioteca por género cuando te pidan un estilo - así filtras por un género que "
            "realmente existe en vez de adivinar un nombre (p.ej. el usuario puede pedir 'indie rock' "
            "y en su biblioteca estar etiquetado solo como 'Alternative' o 'Rock').",
            {},
            [],
            self._tool_listar_generos,
        )
        add(
            "filtrar_biblioteca",
            "Obtiene una muestra de canciones de la biblioteca del usuario filtrada por género y/o "
            "rango de años - el género tiene que ser uno de los que devuelve listar_generos (llámala "
            "primero si no lo sabes ya), no un nombre de estilo inventado. Es una muestra, no la lista "
            "exhaustiva - útil para explorar qué tiene el usuario de un estilo/época, o para elegir "
            "candidatas para una playlist.",
            {
                "genero": types.Schema(type=types.Type.STRING, description="Género a filtrar (opcional) - debe ser uno real, de listar_generos"),
                "desde_anio": types.Schema(type=types.Type.INTEGER, description="Año mínimo (opcional)"),
                "hasta_anio": types.Schema(type=types.Type.INTEGER, description="Año máximo (opcional)"),
                "limite": types.Schema(type=types.Type.INTEGER, description="Máx. canciones a devolver (default 50)"),
            },
            [],
            self._tool_filtrar_biblioteca,
        )
        add(
            "now_playing",
            "Consulta qué se está reproduciendo ahora mismo en el servidor Navidrome.",
            {},
            [],
            self._tool_now_playing,
        )
        add(
            "crear_playlist",
            "Crea una playlist NUEVA en Navidrome con los ids de canción exactos que le pases. Úsala "
            "solo después de haber buscado/elegido las canciones con buscar_biblioteca o "
            "filtrar_biblioteca, y solo la primera vez en la conversación. Tú decides qué canciones "
            "van - no se lo devuelvas al usuario para que elija salvo que te lo pida explícitamente. "
            "Si el usuario pide cambios sobre una playlist que ya creaste en este mismo chat (quitar "
            "una canción, añadir más, cambiar el rollo), usa actualizar_playlist en su lugar - NO "
            "vuelvas a llamar a esta, o acabarás con playlists duplicadas.",
            {
                "nombre": types.Schema(type=types.Type.STRING, description="Nombre de la playlist"),
                "ids_canciones": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING),
                    description="Lista de ids de canción (de Navidrome) a incluir, en el orden deseado",
                ),
            },
            ["nombre", "ids_canciones"],
            self._tool_crear_playlist,
        )
        add(
            "ver_playlist_actual",
            "Muestra las canciones que tiene AHORA MISMO la playlist activa de esta conversación (la "
            "que creaste con crear_playlist), con sus ids. Llama a esta tool SIEMPRE antes de "
            "actualizar_playlist para un refinamiento ('quita esa canción', 'añade otra de X') - la "
            "lista que le pases a actualizar_playlist tiene que partir de lo que esta tool te devuelva "
            "(quitando/añadiendo lo que corresponda), no una lista nueva generada desde cero, o "
            "cambiarás la playlist entera en vez de solo lo que te pidieron.",
            {},
            [],
            self._tool_ver_playlist_actual,
        )
        add(
            "actualizar_playlist",
            "Reemplaza el contenido de la playlist que ya creaste en ESTA conversación (con "
            "crear_playlist) por una nueva lista de canciones - úsala para refinamientos "
            "('quita esa canción', 'pon algo más movido', 'menos lenta') en vez de crear_playlist, "
            "así no se duplica la playlist. Pásale la lista completa final (llama antes a "
            "ver_playlist_actual y parte de esa lista, no la inventes de cero) no solo lo que cambia. "
            "Si no has creado ninguna playlist todavía en esta conversación, esta tool falla - usa "
            "crear_playlist primero.",
            {
                "ids_canciones": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING),
                    description="Lista COMPLETA de ids de canción que debe tener la playlist tras el cambio",
                ),
            },
            ["ids_canciones"],
            self._tool_actualizar_playlist,
        )

        # Historial de escucha - solo si hay servicio configurado (ListenBrainz hoy, Koito mañana)
        if self.history_service:
            add(
                "top_artistas",
                "Artistas más escuchados por el usuario en un periodo de tiempo (por cantidad de "
                "escuchas, no orden cronológico). Úsalo para 'mis favoritos', 'top', 'más escuchados'.",
                {
                    "periodo": types.Schema(
                        type=types.Type.STRING,
                        description="this_week, this_month, this_year, last_week, last_month, last_year o all_time (default this_month)",
                    ),
                    "limite": types.Schema(type=types.Type.INTEGER, description="Máx. artistas (default 10)"),
                },
                [],
                self._tool_top_artistas,
            )
            add(
                "top_tracks",
                "Canciones más escuchadas por el usuario en un periodo de tiempo.",
                {
                    "periodo": types.Schema(type=types.Type.STRING, description="Igual que en top_artistas"),
                    "limite": types.Schema(type=types.Type.INTEGER, description="Máx. canciones (default 10)"),
                },
                [],
                self._tool_top_tracks,
            )
            add(
                "top_albumes",
                "Álbumes más escuchados por el usuario en un periodo de tiempo.",
                {
                    "periodo": types.Schema(type=types.Type.STRING, description="Igual que en top_artistas"),
                    "limite": types.Schema(type=types.Type.INTEGER, description="Máx. álbumes (default 10)"),
                },
                [],
                self._tool_top_albumes,
            )
            add(
                "escuchas_recientes",
                "Últimas canciones escuchadas por el usuario, en orden cronológico (lo más reciente "
                "primero). Úsalo para 'últimos', 'recientes', 'hace poco' - NO para 'favoritos'/'top'.",
                {"limite": types.Schema(type=types.Type.INTEGER, description="Máx. canciones (default 20)")},
                [],
                self._tool_escuchas_recientes,
            )
            add(
                "artistas_similares",
                "Artistas similares a uno dado, para descubrir música nueva. Combina el historial del "
                "usuario, MusicBrainz e IA como último recurso - este último no sabe qué tiene el "
                "usuario en su biblioteca, así que cada resultado incluye 'en_biblioteca' (true/false, "
                "comprobado de verdad contra Navidrome) SALVO que la comprobación fallase, en cuyo caso "
                "el campo no aparece - en ese caso no sabes si lo tiene o no, dilo así en vez de asumir "
                "que sí o que no. Si te piden algo que NO tengan, descarta o avisa de los que salgan "
                "en_biblioteca=true en vez de dar por hecho que son nuevos.",
                {
                    "artista": types.Schema(type=types.Type.STRING, description="Nombre del artista de referencia"),
                    "limite": types.Schema(type=types.Type.INTEGER, description="Máx. artistas (default 10)"),
                },
                ["artista"],
                self._tool_artistas_similares,
            )

        # Lanzamientos - solo si MusicBrainz está habilitado
        if self.musicbrainz:
            add(
                "lanzamientos_artista",
                "Lanzamientos recientes (álbumes/EPs) de un artista concreto, según MusicBrainz.",
                {
                    "artista": types.Schema(type=types.Type.STRING, description="Nombre del artista"),
                    "dias": types.Schema(type=types.Type.INTEGER, description="Ventana de días hacia atrás (default 90)"),
                },
                ["artista"],
                self._tool_lanzamientos_artista,
            )

        # Setlists de conciertos (setlist.fm) - solo si hay API key configurada
        if os.getenv("SETLISTFM_API_KEY"):
            add(
                "buscar_setlist_concierto",
                "Busca conciertos (setlists) de un artista en setlist.fm, opcionalmente filtrando por "
                "ciudad y/o fecha. Devuelve una lista de conciertos candidatos con su setlist_id, para "
                "luego crear la playlist con crear_playlist_desde_setlist. Si hay varios resultados, "
                "pregúntale al usuario cuál es (ciudad y fecha suelen bastar para desambiguar) en vez "
                "de elegir uno al azar - salvo que solo haya un resultado, ahí créala directamente.",
                {
                    "artista": types.Schema(type=types.Type.STRING, description="Nombre del artista o banda"),
                    "ciudad": types.Schema(type=types.Type.STRING, description="Ciudad del concierto (opcional)"),
                    "fecha": types.Schema(type=types.Type.STRING, description="Fecha del concierto, formato dd-MM-yyyy (opcional)"),
                },
                ["artista"],
                self._tool_buscar_setlist_concierto,
            )
            add(
                "crear_playlist_desde_setlist",
                "Crea una playlist real en Navidrome a partir de un concierto de setlist.fm ya "
                "identificado (el setlist_id que te dio buscar_setlist_concierto). Empareja cada "
                "canción tocada en el concierto contra la biblioteca del usuario automáticamente - no "
                "hace falta que tú elijas las canciones.",
                {
                    "setlist_id": types.Schema(type=types.Type.STRING, description="Id del setlist en setlist.fm"),
                },
                ["setlist_id"],
                self._tool_crear_playlist_desde_setlist,
            )

    # ------------------------------------------------------------------
    # Implementaciones de las tools (envuelven servicios ya existentes,
    # no reimplementan nada de navidrome_service/listenbrainz_service/musicbrainz_service)
    # ------------------------------------------------------------------

    async def _tool_buscar_biblioteca(self, consulta: str, limite: int = 20) -> Dict[str, Any]:
        try:
            results = await self.navidrome.search(consulta, limit=limite)
            return {
                "tracks": [t.model_dump(mode="json") for t in results.get("tracks", [])],
                "albums": [a.model_dump(mode="json") for a in results.get("albums", [])],
                "artists": [a.model_dump(mode="json") for a in results.get("artists", [])],
            }
        except Exception as e:
            logger.warning(f"buscar_biblioteca falló: {e}")
            return {"error": str(e)}

    async def _tool_listar_generos(self) -> Dict[str, Any]:
        try:
            genres = await self.navidrome.get_genres()
            return {"generos": genres}
        except Exception as e:
            logger.warning(f"listar_generos falló: {e}")
            return {"error": str(e)}

    async def _tool_filtrar_biblioteca(
        self,
        genero: Optional[str] = None,
        desde_anio: Optional[int] = None,
        hasta_anio: Optional[int] = None,
        limite: int = 50,
    ) -> Dict[str, Any]:
        try:
            filters: Dict[str, Any] = {}
            if genero:
                filters["genre"] = genero
            if desde_anio:
                filters["fromYear"] = desde_anio
            if hasta_anio:
                filters["toYear"] = hasta_anio
            tracks = await self.navidrome.get_tracks(limit=limite, **filters)
            return {"tracks": [t.model_dump(mode="json") for t in tracks]}
        except Exception as e:
            logger.warning(f"filtrar_biblioteca falló: {e}")
            return {"error": str(e)}

    async def _tool_now_playing(self) -> Dict[str, Any]:
        try:
            return {"now_playing": await self.navidrome.get_now_playing()}
        except Exception as e:
            logger.warning(f"now_playing falló: {e}")
            return {"error": str(e)}

    async def _tool_crear_playlist(self, nombre: str, ids_canciones: List[str]) -> Dict[str, Any]:
        try:
            if not ids_canciones:
                return {"error": "No se pasó ninguna canción"}
            # Guardarraíl determinista: si ya hay una playlist activa en esta
            # conversación, NO se crea una segunda aunque el modelo lo intente -
            # se le devuelve el error con los datos que necesita para corregirse
            # y llamar a actualizar_playlist en su lugar, en el mismo turno.
            if self._current_session and self._current_session.last_playlist:
                active = self._current_session.last_playlist
                return {
                    "error": (
                        f"Ya hay una playlist activa en esta conversación: '{active['name']}' "
                        f"(id={active['id']}). No crees una segunda - llama a actualizar_playlist "
                        f"con la lista completa de canciones que debería tener ahora."
                    )
                }
            playlist_id = await self.navidrome.create_playlist(nombre, ids_canciones)
            if not playlist_id:
                return {"error": "Navidrome no pudo crear la playlist"}
            self._last_playlist_created = {
                "id": playlist_id,
                "name": nombre,
                "track_count": len(ids_canciones),
                "song_ids": ids_canciones,
            }
            if self._current_session:
                self._current_session.set_last_playlist(playlist_id, nombre)
            return {"success": True, "playlist_id": playlist_id, "name": nombre, "track_count": len(ids_canciones)}
        except Exception as e:
            logger.warning(f"crear_playlist falló: {e}")
            return {"error": str(e)}

    async def _tool_ver_playlist_actual(self) -> Dict[str, Any]:
        try:
            active = self._current_session.last_playlist if self._current_session else None
            if not active:
                return {
                    "error": "No hay ninguna playlist activa en esta conversación todavía. "
                             "Usa crear_playlist para crear la primera."
                }
            tracks = await self.navidrome.get_playlist_tracks(active["id"])
            return {
                "name": active["name"],
                "playlist_id": active["id"],
                "tracks": [t.model_dump(mode="json") for t in tracks],
            }
        except Exception as e:
            logger.warning(f"ver_playlist_actual falló: {e}")
            return {"error": str(e)}

    async def _tool_actualizar_playlist(self, ids_canciones: List[str]) -> Dict[str, Any]:
        try:
            if not ids_canciones:
                return {"error": "No se pasó ninguna canción"}
            active = self._current_session.last_playlist if self._current_session else None
            if not active:
                return {
                    "error": "No hay ninguna playlist activa en esta conversación todavía. "
                             "Usa crear_playlist para crear la primera."
                }
            ok = await self.navidrome.update_playlist_songs(active["id"], ids_canciones)
            if not ok:
                return {"error": "Navidrome no pudo actualizar la playlist"}
            self._last_playlist_created = {
                "id": active["id"],
                "name": active["name"],
                "track_count": len(ids_canciones),
                "song_ids": ids_canciones,
            }
            return {
                "success": True,
                "playlist_id": active["id"],
                "name": active["name"],
                "track_count": len(ids_canciones),
            }
        except Exception as e:
            logger.warning(f"actualizar_playlist falló: {e}")
            return {"error": str(e)}

    async def _tool_top_artistas(self, periodo: str = "this_month", limite: int = 10) -> Dict[str, Any]:
        try:
            artists = await self.history_service.get_top_artists(period=periodo, limit=limite)
            return {"artists": [a.model_dump(mode="json") for a in artists]}
        except Exception as e:
            logger.warning(f"top_artistas falló: {e}")
            return {"error": str(e)}

    async def _tool_top_tracks(self, periodo: str = "this_month", limite: int = 10) -> Dict[str, Any]:
        try:
            tracks = await self.history_service.get_top_tracks(period=periodo, limit=limite)
            return {"tracks": [t.model_dump(mode="json") for t in tracks]}
        except Exception as e:
            logger.warning(f"top_tracks falló: {e}")
            return {"error": str(e)}

    async def _tool_top_albumes(self, periodo: str = "this_month", limite: int = 10) -> Dict[str, Any]:
        try:
            albums = await self.history_service.get_top_albums(period=periodo, limit=limite)
            return {"albums": albums}  # ya son dicts planos en ListenBrainzService
        except Exception as e:
            logger.warning(f"top_albumes falló: {e}")
            return {"error": str(e)}

    async def _tool_escuchas_recientes(self, limite: int = 20) -> Dict[str, Any]:
        try:
            tracks = await self.history_service.get_recent_tracks(limit=limite)
            return {"tracks": [t.model_dump(mode="json") for t in tracks]}
        except Exception as e:
            logger.warning(f"escuchas_recientes falló: {e}")
            return {"error": str(e)}

    async def _tool_artistas_similares(self, artista: str, limite: int = 10) -> Dict[str, Any]:
        try:
            artists = await self.discovery_service.get_similar_artists_from_recording(
                artista, limit=limite, musicbrainz_service=self.musicbrainz,
            )
            result = []
            for a in artists:
                item = a.model_dump(mode="json")
                en_biblioteca = await self._artist_in_library(a.name)
                # None = no se pudo comprobar (p.ej. fallo de red hacia Navidrome) -
                # se omite el campo en vez de afirmar False, para que el modelo no
                # diga con confianza "no lo tienes" cuando en realidad no lo sabemos.
                if en_biblioteca is not None:
                    item["en_biblioteca"] = en_biblioteca
                result.append(item)
            return {"artists": result}
        except Exception as e:
            logger.warning(f"artistas_similares falló: {e}")
            return {"error": str(e)}

    async def _artist_in_library(self, artist_name: str) -> Optional[bool]:
        """Comprueba si un artista ya está en la biblioteca de Navidrome.

        Devuelve None (no bool) si la comprobación falla - por ejemplo, un fallo
        transitorio de red hacia Navidrome no debe traducirse en un "no lo
        tienes" dicho con confianza (falso negativo peor que no decir nada).
        """
        try:
            results = await self.navidrome.search(artist_name, limit=5)
            name_lower = artist_name.lower().strip()
            return any(
                name_lower in art.name.lower() or art.name.lower() in name_lower
                for art in results.get("artists", [])
            )
        except Exception as e:
            logger.warning(f"No se pudo comprobar si '{artist_name}' está en la biblioteca: {e}")
            return None

    async def _tool_lanzamientos_artista(self, artista: str, dias: int = 90) -> Dict[str, Any]:
        try:
            releases = await self.musicbrainz.get_recent_releases_for_artists([artista], days=dias)
            return {"releases": releases}
        except Exception as e:
            logger.warning(f"lanzamientos_artista falló: {e}")
            return {"error": str(e)}

    async def _tool_buscar_setlist_concierto(
        self, artista: str, ciudad: Optional[str] = None, fecha: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            candidates = await self.setlistfm.search_setlists(artista, ciudad, fecha)
            if not candidates:
                return {"error": f"No encontré conciertos de {artista} en setlist.fm con esos datos."}
            conciertos = [
                {
                    "setlist_id": c.get("id"),
                    "artista": c.get("artist", {}).get("name", artista),
                    "venue": c.get("venue", {}).get("name", "?"),
                    "ciudad": c.get("venue", {}).get("city", {}).get("name", "?"),
                    "fecha": c.get("eventDate", "?"),
                }
                for c in candidates[:5]
            ]
            return {"conciertos": conciertos, "total_encontrados": len(candidates)}
        except Exception as e:
            logger.warning(f"buscar_setlist_concierto falló: {e}")
            return {"error": str(e)}

    async def _tool_crear_playlist_desde_setlist(self, setlist_id: str) -> Dict[str, Any]:
        try:
            setlist = await self.setlistfm.get_setlist(setlist_id)
            if not setlist:
                return {"error": "No pude encontrar ese setlist en setlist.fm."}
            result = await self.setlistfm.build_playlist_from_setlist(self.navidrome, setlist)
            if result.get("success"):
                self._last_playlist_created = {
                    "id": result["playlist_id"],
                    "name": result["playlist_name"],
                    "track_count": result["matched_count"],
                    "song_ids": result["song_ids"],
                }
            return result
        except Exception as e:
            logger.warning(f"crear_playlist_desde_setlist falló: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Punto de entrada principal
    # ------------------------------------------------------------------

    async def query(self, user_question: str, user_id: int, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Responde una consulta en lenguaje natural usando tool-calling.

        Devuelve un dict con al menos {success, answer, links} - es el shape
        que consume `MusicAssistant._agent_query()`.
        """
        session = self.conversation_manager.get_session(user_id)
        self._current_session = session
        self._last_playlist_created = None
        informational = bool(context and context.get("type") == "informational")

        try:
            answer, tools_used, links = await asyncio.wait_for(
                self._run_tool_loop(user_question, session, informational),
                timeout=QUERY_TIMEOUT_SECONDS,
            )

            session.add_message("user", user_question)
            session.add_message("assistant", answer)

            return {
                "answer": answer,
                "data_used": {"tools_used": tools_used},
                "links": links,
                "success": True,
                "session_id": user_id,
                "playlist_created": self._last_playlist_created,
            }
        except asyncio.TimeoutError:
            logger.warning(f"Timeout procesando consulta de usuario {user_id}")
            return {
                "answer": SystemPrompts.get_error_message("timeout"),
                "data_used": {},
                "links": [],
                "success": False,
            }
        except Exception as e:
            logger.error(f"Error procesando consulta: {e}")
            return {
                "answer": f"❌ Error procesando tu consulta: {e}",
                "data_used": {},
                "links": [],
                "success": False,
            }

    async def _run_tool_loop(self, user_question: str, session, informational: bool):
        """Bucle manual de tool-calling.

        `google-genai` solo soporta *automatic function calling* con
        funciones síncronas; nuestras tools son async, así que se orquesta
        el ciclo llamar-modelo -> ejecutar-tools -> devolver-resultado a mano.
        """
        persona = SystemPrompts.get_companion_prompt(informational=informational)

        # Memoria nativa: turnos reales de Gemini, no un bloque de texto reinyectado
        contents: List[types.Content] = []
        for msg in session.message_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=user_question)]))

        config = types.GenerateContentConfig(
            system_instruction=persona,
            tools=[types.Tool(function_declarations=self._tool_declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        tools_used: List[Dict[str, Any]] = []
        links: List[str] = []

        for _ in range(MAX_TOOL_TURNS):
            response = await self.client.aio.models.generate_content(
                model=MODEL_NAME, contents=contents, config=config,
            )

            if not response.candidates:
                return SystemPrompts.get_error_message("api_error"), tools_used, links[:5]

            calls = response.function_calls or []
            if not calls:
                return (response.text or "").strip(), tools_used, links[:5]

            contents.append(response.candidates[0].content)

            response_parts = []
            for call in calls:
                args = dict(call.args or {})
                tools_used.append({"tool": call.name, "args": args})
                impl = self._tool_impl.get(call.name)
                result = {"error": f"Herramienta desconocida: {call.name}"} if impl is None else await impl(**args)
                self._collect_links(result, links)
                response_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))

            contents.append(types.Content(role="user", parts=response_parts))

        # Se agotaron los turnos de herramientas sin que el modelo diera una respuesta final
        logger.warning(f"MAX_TOOL_TURNS alcanzado para: {user_question!r}")
        return SystemPrompts.get_error_message("api_error"), tools_used, links[:5]

    @staticmethod
    def _collect_links(result: Any, links: List[str], _depth: int = 0):
        """Recoge URLs de un resultado de tool, para el pie 'Enlaces relevantes' de la respuesta."""
        if _depth > 2 or len(links) >= 5:
            return
        if isinstance(result, dict):
            url = result.get("url")
            if isinstance(url, str) and url and url not in links:
                links.append(url)
            for value in result.values():
                MusicAgentService._collect_links(value, links, _depth + 1)
        elif isinstance(result, list):
            for item in result:
                MusicAgentService._collect_links(item, links, _depth + 1)

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    async def close(self):
        """Cerrar conexiones HTTP de los servicios subyacentes."""
        await self.navidrome.close()
        await self.setlistfm.close()
        if self.listenbrainz:
            await self.listenbrainz.close()
        if self.koito:
            await self.koito.close()
        if self.musicbrainz:
            await self.musicbrainz.close()
