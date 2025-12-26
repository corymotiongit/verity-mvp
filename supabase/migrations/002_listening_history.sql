-- Schema para tabla de historial de escucha de Spotify
-- Tabla: listening_history

CREATE TABLE IF NOT EXISTS listening_history (
  play_id TEXT PRIMARY KEY,
  track_name TEXT NOT NULL,
  artist_name TEXT NOT NULL,
  played_at TIMESTAMP NOT NULL,
  ms_played INTEGER NOT NULL,
  
  -- Índices para queries comunes
  CONSTRAINT positive_duration CHECK (ms_played > 0)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_listening_history_played_at ON listening_history(played_at DESC);
CREATE INDEX IF NOT EXISTS idx_listening_history_artist ON listening_history(artist_name);
CREATE INDEX IF NOT EXISTS idx_listening_history_track ON listening_history(track_name);

-- Políticas RLS (Row Level Security)
ALTER TABLE listening_history ENABLE ROW LEVEL SECURITY;

-- Política: usuarios autenticados pueden leer sus propios datos
-- (En MVP simplificado: todos los datos son del mismo usuario)
CREATE POLICY "Allow authenticated read" ON listening_history
  FOR SELECT
  TO authenticated
  USING (true);

-- Comentarios
COMMENT ON TABLE listening_history IS 'Historial de reproducción de Spotify del usuario';
COMMENT ON COLUMN listening_history.play_id IS 'ID único generado como hash(artist_name + track_name + played_at)';
COMMENT ON COLUMN listening_history.played_at IS 'Timestamp de finalización de reproducción (endTime de Spotify)';
COMMENT ON COLUMN listening_history.ms_played IS 'Duración de reproducción en milisegundos';
