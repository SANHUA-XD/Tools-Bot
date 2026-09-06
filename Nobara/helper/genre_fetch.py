"""
Genre lookup for filter genre-tagging (/add auto-tags, /syncgenre backfills).

Tries TMDB (movies/TV) first, falls back to AniList (anime/manga) if TMDB
finds nothing. Returns a list of lowercase genre strings matching
Nobara/modules/cust_filters.py's GENRE_KEYWORDS list, or None.
"""

import httpx
from config import config

TMDB_GENRE_MAP = {
    28: "action", 12: "adventure", 16: "animation", 35: "comedy", 80: "crime",
    99: "documentary", 18: "drama", 10751: "family", 14: "fantasy",
    36: "historical", 27: "horror", 10402: "music", 9648: "mystery",
    10749: "romance", 878: "sci-fi", 10770: "drama", 53: "thriller",
    10752: "war", 37: "western",
    # TV-specific ids
    10759: "action adventure", 10762: "family", 10763: "documentary",
    10764: "drama", 10765: "sci-fi", 10766: "drama", 10767: "drama",
    10768: "war",
}


async def _fetch_tmdb_genres(query: str):
    if not getattr(config, "TMDB_API_KEY", None):
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.themoviedb.org/3/search/multi",
                params={"api_key": config.TMDB_API_KEY, "query": query},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    for result in data.get("results", []):
        genre_ids = result.get("genre_ids", [])
        names = [TMDB_GENRE_MAP[g] for g in genre_ids if g in TMDB_GENRE_MAP]
        if names:
            # de-dupe while keeping order
            seen = set()
            return [n for n in names if not (n in seen or seen.add(n))]
    return None


async def _fetch_anilist_genres(query: str):
    gql = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        genres
      }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://graphql.anilist.co",
                json={"query": gql, "variables": {"search": query}},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    genres = (data.get("data") or {}).get("Media", {}).get("genres") if data.get("data") else None
    if not genres:
        return None
    return [g.lower() for g in genres]


async def fetch_genres(query: str):
    """Try TMDB first, then AniList. Returns a list of genre strings, or None."""
    genres = await _fetch_tmdb_genres(query)
    if genres:
        return genres
    return await _fetch_anilist_genres(query)
