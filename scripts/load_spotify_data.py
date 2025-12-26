"""
Script para cargar datos de Spotify a Supabase.
Versión con mejor manejo de errores y batches pequeños.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import os
from supabase import create_client, Client

def load_spotify_data() -> List[Dict]:
    """Carga y combina archivos de streaming de Spotify."""
    base_path = Path("my_spotify_data/Spotify Account Data")
    
    file0 = json.load(open(base_path / "StreamingHistory_music_0.json", encoding="utf-8"))
    file1 = json.load(open(base_path / "StreamingHistory_music_1.json", encoding="utf-8"))
    
    all_data = file0 + file1
    print(f"Loaded {len(all_data):,} streaming records")
    return all_data

def transform_to_listening_history(raw_data: List[Dict]) -> List[Dict]:
    """Transforma datos de Spotify al schema de listening_history."""
    transformed = []
    seen_ids = set()
    
    for i, record in enumerate(raw_data):
        # Generar play_id único
        unique_str = f"{record['artistName']}|{record['trackName']}|{record['endTime']}|{i}"
        play_id = hashlib.sha256(unique_str.encode()).hexdigest()[:16]
        
        # Skip duplicados
        if play_id in seen_ids:
            continue
        seen_ids.add(play_id)
        
        # Parsear timestamp
        try:
            played_at = datetime.strptime(record['endTime'], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        
        # Limpiar strings (remover caracteres problemáticos)
        track_name = record['trackName'][:500] if record['trackName'] else "Unknown"
        artist_name = record['artistName'][:500] if record['artistName'] else "Unknown"
        
        transformed.append({
            "play_id": play_id,
            "track_name": track_name,
            "artist_name": artist_name,
            "played_at": played_at.isoformat(),
            "ms_played": int(record['msPlayed']) if record['msPlayed'] else 0
        })
    
    return transformed

def upload_to_supabase(data: List[Dict], batch_size: int = 500):
    """Carga datos a Supabase en batches."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    total_batches = (len(data) + batch_size - 1) // batch_size
    print(f"Uploading {len(data):,} records in {total_batches} batches...")
    
    uploaded = 0
    failed = 0
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            response = supabase.table("listening_history").upsert(batch).execute()
            uploaded += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: {len(batch)} records ✓")
        except Exception as e:
            failed += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: FAILED - {str(e)[:100]}")
            # Try one by one
            for record in batch:
                try:
                    supabase.table("listening_history").upsert([record]).execute()
                    uploaded += 1
                except Exception:
                    failed += 1
    
    print(f"\n✅ Upload complete: {uploaded:,} inserted, {failed:,} failed")

def main():
    """Pipeline principal."""
    print("=== Spotify Data Loader ===\n")
    
    raw_data = load_spotify_data()
    
    print("\nTransforming data...")
    listening_history = transform_to_listening_history(raw_data)
    print(f"Transformed {len(listening_history):,} unique records")
    
    print("\nUploading to Supabase...")
    upload_to_supabase(listening_history)
    
    print("\n=== Summary ===")
    print(f"Total records: {len(listening_history):,}")

if __name__ == "__main__":
    main()
