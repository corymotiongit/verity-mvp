"""Analiza datos de Spotify para diseño de schema."""
import json
from pathlib import Path
from datetime import datetime

base_path = Path("my_spotify_data/Spotify Account Data")

# Cargar ambos archivos
file0 = json.load(open(base_path / "StreamingHistory_music_0.json", encoding="utf-8"))
file1 = json.load(open(base_path / "StreamingHistory_music_1.json", encoding="utf-8"))

all_data = file0 + file1

print(f"Total records: {len(all_data):,}")
print(f"Date range: {all_data[-1]['endTime']} → {all_data[0]['endTime']}")

# Estadísticas
artists = set(r["artistName"] for r in all_data)
tracks = set(r["trackName"] for r in all_data)
total_ms = sum(r["msPlayed"] for r in all_data)

print(f"\nUnique artists: {len(artists):,}")
print(f"Unique tracks: {len(tracks):,}")
print(f"Total listening time: {total_ms / 1000 / 60 / 60:.1f} hours")

# Top 5 artistas por tiempo escuchado
from collections import defaultdict
artist_time = defaultdict(int)
for r in all_data:
    artist_time[r["artistName"]] += r["msPlayed"]

top_artists = sorted(artist_time.items(), key=lambda x: x[1], reverse=True)[:5]
print("\nTop 5 artists by listening time:")
for artist, ms in top_artists:
    print(f"  {artist}: {ms / 1000 / 60:.1f} min")

# Sample de datos recientes
print("\nSample (últimos 3 registros):")
for r in all_data[:3]:
    print(f"  {r['endTime']} | {r['artistName']} - {r['trackName']} ({r['msPlayed']/1000:.1f}s)")
