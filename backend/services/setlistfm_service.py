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

    async def close(self):
        await self.client.aclose()
