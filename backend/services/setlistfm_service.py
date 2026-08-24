import httpx
import os
import re
import time
import asyncio
from typing import Optional, Dict, Any, List


class SetlistfmService:
    """Cliente de la API pública de setlist.fm (https://api.setlist.fm/docs/1.0/index.html)

    Permite resolver un setlist a partir de su URL o buscarlo por artista/ciudad/fecha,
    y aplanar sus canciones para poder emparejarlas contra la biblioteca de Navidrome.
    """

    _URL_ID_RE = re.compile(r"-([0-9a-fA-F]+)\.html")

    def __init__(self):
        self.api_key = os.getenv("SETLISTFM_API_KEY")
        self.base_url = "https://api.setlist.fm/rest/1.0"
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "x-api-key": self.api_key or "",
                "Accept": "application/json",
            },
        )
        # Rate limiting: la clave gratuita de setlist.fm admite ~2 peticiones/seg
        self._last_request_time = 0.0

    async def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < 0.6:
            await asyncio.sleep(0.6 - time_since_last)
        self._last_request_time = time.time()

    def parse_setlist_url(self, text: str) -> Optional[str]:
        """Extraer el ID de setlist de una URL de setlist.fm pegada en un mensaje."""
        match = re.search(r"setlist\.fm/setlist/[^\s]+", text, re.IGNORECASE)
        if not match:
            return None
        id_match = self._URL_ID_RE.search(match.group(0))
        return id_match.group(1) if id_match else None

    async def get_setlist(self, setlist_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un setlist por su ID."""
        if not self.api_key:
            print("❌ SETLISTFM_API_KEY no configurada")
            return None
        try:
            await self._rate_limit()
            response = await self.client.get(f"{self.base_url}/setlist/{setlist_id}")
            if response.status_code != 200:
                print(f"❌ Error obteniendo setlist {setlist_id}: {response.status_code}")
                return None
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo setlist {setlist_id}: {e}")
            return None

    async def search_setlists(
        self,
        artist_name: str,
        city_name: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Buscar setlists por artista y, opcionalmente, ciudad/fecha (dd-MM-yyyy)."""
        if not self.api_key:
            print("❌ SETLISTFM_API_KEY no configurada")
            return []
        try:
            params = {"artistName": artist_name}
            if city_name:
                params["cityName"] = city_name
            if date:
                params["date"] = date

            await self._rate_limit()
            response = await self.client.get(f"{self.base_url}/search/setlists", params=params)
            if response.status_code == 404:
                return []
            if response.status_code != 200:
                print(f"❌ Error buscando setlists de {artist_name}: {response.status_code}")
                return []

            data = response.json()
            setlists = data.get("setlist", [])
            if isinstance(setlists, dict):
                setlists = [setlists]
            return setlists
        except Exception as e:
            print(f"❌ Error buscando setlists de {artist_name}: {e}")
            return []

    def extract_songs(self, setlist_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aplanar las canciones de un setlist a una lista simple.

        Cada canción se representa como:
            {"title": str, "artist": str, "is_cover": bool, "cover_artist": Optional[str]}

        Se descartan las entradas marcadas como "tape" (grabación reproducida
        entre canciones, no interpretada en directo por la banda).

        Algunas entradas del setlist son en realidad varias canciones enlazadas
        sin pausa (p.ej. "Intro / 100 Amapolas"); se separan en canciones
        independientes para poder buscarlas y emparejarlas por separado.
        """
        default_artist = setlist_json.get("artist", {}).get("name", "")
        songs: List[Dict[str, Any]] = []

        sets = setlist_json.get("sets", {}).get("set", [])
        if isinstance(sets, dict):
            sets = [sets]

        for set_item in sets:
            set_songs = set_item.get("song", [])
            if isinstance(set_songs, dict):
                set_songs = [set_songs]

            for song in set_songs:
                if song.get("tape"):
                    continue
                raw_title = song.get("name", "").strip()
                if not raw_title:
                    continue

                cover = song.get("cover")
                for title in [part.strip() for part in raw_title.split("/")]:
                    if not title:
                        continue
                    songs.append({
                        "title": title,
                        "artist": default_artist,
                        "is_cover": bool(cover),
                        "cover_artist": cover.get("name") if cover else None,
                    })

        return songs

    # ------------------------------------------------------------------
    # Emparejar setlist -> biblioteca de Navidrome -> crear playlist
    #
    # Vive aquí (y no en MusicAssistant/MusicAgentService) para que el atajo
    # determinista de URL (chat()) y el tool conversacional de buscar
    # conciertos por nombre compartan exactamente la misma lógica de
    # emparejado, en vez de mantener dos copias que puedan divergir.
    # ------------------------------------------------------------------

    _TITLE_NOISE_RE = re.compile(
        r"[\(\[][^\)\]]*[\)\]]"  # paréntesis/corchetes: "(En Directo)", "(Remastered 2009)"
        r"|[-–]\s*(live|en directo|en vivo|remaster(ed)?|acoustic|acústic[oa]|demo|edit|versi[oó]n)\b.*$",
        re.IGNORECASE,
    )

    @classmethod
    def _normalize_title(cls, text: str) -> str:
        cleaned = cls._TITLE_NOISE_RE.sub("", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    async def _find_best_track_match(self, navidrome, artist: str, title: str, fuzz):
        """Busca en Navidrome la mejor coincidencia de una canción por título+artista.

        Prueba primero "artista + título" y, si no hay nada suficientemente
        parecido, reintenta solo con el título (algunas búsquedas combinadas
        no devuelven resultados aunque la canción exista en la biblioteca).

        Antes de comparar se limpia ruido conocido del título de la biblioteca
        (paréntesis, "- En Directo", remasters...) y se usa token_sort_ratio,
        que sí penaliza palabras extra genuinas. Deliberadamente NO se usa
        token_set_ratio: ese algoritmo da score ~100 cuando un título es un
        subconjunto de palabras de otro (p.ej. "Jota" vs "Jota Final"),
        produciendo falsos positivos con títulos parecidos pero distintos.
        """
        normalized_title = self._normalize_title(title)

        for query in (f"{artist} {title}", title):
            results = await navidrome.search(query, limit=10)
            tracks = results.get("tracks", [])
            if not tracks:
                continue

            best_track, best_score = None, 0.0
            for track in tracks:
                score = fuzz.token_sort_ratio(normalized_title, self._normalize_title(track.title))
                if score > best_score:
                    best_track, best_score = track, score

            if best_track and best_score >= 75:
                return best_track

        return None

    async def build_playlist_from_setlist(self, navidrome, setlist_json: Dict[str, Any]) -> Dict[str, Any]:
        """Empareja las canciones de un setlist contra la biblioteca de Navidrome y crea la playlist.

        Args:
            navidrome: instancia de NavidromeService (búsqueda + creación de playlist)
            setlist_json: el dict devuelto por get_setlist()

        Returns:
            {"success": True, "playlist_id", "playlist_name", "song_ids", "total_songs",
             "matched_count", "unmatched"} o {"success": False, "error": str}
        """
        from rapidfuzz import fuzz

        songs = self.extract_songs(setlist_json)
        if not songs:
            return {"success": False, "error": "El setlist no tiene canciones registradas."}

        song_ids: List[str] = []
        seen_ids = set()
        unmatched: List[str] = []

        for song in songs:
            track = await self._find_best_track_match(navidrome, song["artist"], song["title"], fuzz)
            if not track and song.get("is_cover") and song.get("cover_artist"):
                track = await self._find_best_track_match(navidrome, song["cover_artist"], song["title"], fuzz)

            if track:
                if track.id not in seen_ids:
                    seen_ids.add(track.id)
                    song_ids.append(track.id)
            else:
                unmatched.append(song["title"])

        if not song_ids:
            return {
                "success": False,
                "error": "No encontré ninguna canción de ese setlist en la biblioteca de Navidrome.",
            }

        if len(song_ids) > 50:
            song_ids = song_ids[:50]

        artist_name = setlist_json.get("artist", {}).get("name", "")
        venue_name = setlist_json.get("venue", {}).get("name", "")
        event_date = setlist_json.get("eventDate", "")
        playlist_name = f"{artist_name} - {venue_name} ({event_date})".strip(" -")

        playlist_id = await navidrome.create_playlist(playlist_name, song_ids)
        if not playlist_id:
            return {"success": False, "error": "No pude crear la playlist en Navidrome."}

        return {
            "success": True,
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "song_ids": song_ids,
            "total_songs": len(songs),
            "matched_count": len(song_ids),
            "unmatched": unmatched,
        }

    async def close(self):
        await self.client.aclose()
