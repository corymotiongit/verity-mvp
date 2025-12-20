"""
Checkpoint Logger - Log inmutable de ejecuciones

Responsabilidad:
- Crear checkpoint por cada ejecución de tool
- Almacenar de forma inmutable
- Proveer query por conversation_id
- Storage pluggable (JSON / SQLite / Postgres / BigQuery)

Usos:
- Steps Panel (UI)
- Debug
- Auditoría
- Re-ejecución
- Comparar modelos
"""

from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import datetime
from typing import Literal, Any
from dataclasses import dataclass, asdict


@dataclass
class Checkpoint:
    """Checkpoint inmutable de una ejecución."""
    checkpoint_id: str
    conversation_id: str
    tool: str
    input: dict[str, Any]
    output: dict[str, Any]
    status: Literal["ok", "error", "timeout"]
    timestamp: str  # ISO-8601
    execution_time_ms: float = 0.0


class CheckpointStorage(ABC):
    """Interfaz para storage de checkpoints."""
    
    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> None:
        """Guarda un checkpoint."""
        pass
    
    @abstractmethod
    def query(self, conversation_id: str) -> list[Checkpoint]:
        """Obtiene todos los checkpoints de una conversación."""
        pass


class CheckpointLogger:
    """
    Logger de checkpoints con storage pluggable.
    
    Storage puede ser:
    - JSONFileStorage (dev)
    - SQLiteStorage (local)
    - PostgresStorage (prod)
    - BigQueryStorage (analytics)
    """
    
    def __init__(self, storage: CheckpointStorage):
        self._storage = storage
    
    def log(
        self,
        conversation_id: str,
        tool: str,
        input_data: dict,
        output_data: dict,
        status: Literal["ok", "error", "timeout"],
        execution_time_ms: float = 0.0
    ) -> str:
        """
        Crea y guarda un checkpoint.
        
        Args:
            conversation_id: ID de la conversación
            tool: Nombre de la tool ejecutada
            input_data: Input de la tool
            output_data: Output de la tool
            status: Estado de la ejecución
            execution_time_ms: Tiempo de ejecución
        
        Returns:
            checkpoint_id generado
        """
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid4()),
            conversation_id=conversation_id,
            tool=tool,
            input=input_data,
            output=output_data,
            status=status,
            timestamp=datetime.utcnow().isoformat(),
            execution_time_ms=execution_time_ms
        )
        
        self._storage.save(checkpoint)
        return checkpoint.checkpoint_id
    
    def get_by_conversation(self, conversation_id: str) -> list[Checkpoint]:
        """
        Obtiene todos los checkpoints de una conversación.
        
        Args:
            conversation_id: ID de la conversación
        
        Returns:
            Lista de checkpoints ordenados por timestamp
        """
        return self._storage.query(conversation_id=conversation_id)


__all__ = ["Checkpoint", "CheckpointStorage", "CheckpointLogger"]
