"""
Data Dictionary - Definiciones canónicas de tablas y métricas

Responsabilidad:
- Proveer metadata de tablas
- Proveer definiciones canónicas de métricas
- Mapear aliases a métricas (fuzzy match)
- NO inventar métricas
- NO decidir qué calcular

Cada métrica declara:
- expression: SQL/agregación estándar
- requires: Columnas necesarias para ejecutar
- filters: Filtros automáticos a aplicar
- aliases: Variantes lingüísticas aceptadas
- format: Cómo mostrar el resultado
- business_notes: Contexto de negocio (opcional)

REGLAS:
1. El LLM NUNCA inventa métricas
2. resolve_semantics solo mapea alias → métrica canónica
3. run_table_query deriva columnas desde 'requires'
4. Filtros de métrica se aplican automáticamente
5. Si no hay match, retornar error con sugerencias
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class MetricDefinition:
    """Definición canónica de una métrica."""
    name: str
    description: str
    table: str
    expression: str
    data_type: str
    requires: list[str]
    filters: list[dict]
    aliases: list[str]
    format: str
    business_notes: Optional[str] = None


@dataclass
class TableDefinition:
    """Metadata de una tabla."""
    name: str
    description: str
    grain: str
    primary_key: str
    time_column: Optional[str]
    columns: dict[str, dict]


class DataDictionary:
    """
    Diccionario de datos con métricas canónicas.
    
    NUNCA inventa métricas.
    Solo mapea contra definiciones existentes.
    """
    
    def __init__(self, dictionary_path: Optional[Path] = None):
        if dictionary_path is None:
            dictionary_path = Path(__file__).parent / "dictionary.json"
        
        with open(dictionary_path, encoding="utf-8") as f:
            self._data = json.load(f)
        
        self.version = self._data["version"]
        self.updated_at = self._data["updated_at"]
    
    def get_table(self, table_name: str) -> TableDefinition:
        """
        Obtiene metadata de una tabla.
        
        Args:
            table_name: Nombre de la tabla
        
        Returns:
            TableDefinition
        
        Raises:
            KeyError: Si la tabla no existe
        """
        if table_name not in self._data["tables"]:
            raise KeyError(f"Table '{table_name}' not found in data dictionary")
        
        table_data = self._data["tables"][table_name]
        return TableDefinition(
            name=table_name,
            description=table_data["description"],
            grain=table_data["grain"],
            primary_key=table_data["primary_key"],
            time_column=table_data.get("time_column"),
            columns=table_data["columns"]
        )
    
    def get_metric(self, metric_name: str) -> MetricDefinition:
        """
        Obtiene definición canónica de una métrica.
        
        Args:
            metric_name: Nombre canónico de la métrica
        
        Returns:
            MetricDefinition
        
        Raises:
            KeyError: Si la métrica no existe
        """
        if metric_name not in self._data["metrics"]:
            raise KeyError(f"Metric '{metric_name}' not found in data dictionary")
        
        metric_data = self._data["metrics"][metric_name]
        return MetricDefinition(
            name=metric_name,
            description=metric_data["description"],
            table=metric_data["table"],
            expression=metric_data["expression"],
            data_type=metric_data["data_type"],
            requires=metric_data["requires"],
            filters=metric_data["filters"],
            aliases=metric_data["aliases"],
            format=metric_data["format"],
            business_notes=metric_data.get("business_notes")
        )
    
    def fuzzy_match_metric(self, user_term: str, threshold: float = 0.7) -> Optional[str]:
        """
        Mapea término del usuario a métrica canónica usando fuzzy match.
        
        Args:
            user_term: Término del usuario (ej: "ingresos")
            threshold: Umbral de similitud (0.0 - 1.0)
        
        Returns:
            Nombre canónico de la métrica o None si no hay match
        """
        from rapidfuzz import fuzz, process
        
        user_term_lower = user_term.lower().strip()
        
        # Construir lista de (alias, metric_name) para matching
        alias_to_metric: list[tuple[str, str]] = []
        for metric_name, metric_data in self._data["metrics"].items():
            # Agregar nombre canónico
            alias_to_metric.append((metric_name.lower(), metric_name))
            # Agregar todos los aliases
            for alias in metric_data["aliases"]:
                alias_to_metric.append((alias.lower(), metric_name))
        
        # Extraer solo los aliases para búsqueda
        aliases = [alias for alias, _ in alias_to_metric]
        
        # Buscar mejor match usando ratio de similitud
        result = process.extractOne(
            user_term_lower,
            aliases,
            scorer=fuzz.ratio,
            score_cutoff=threshold * 100  # rapidfuzz usa escala 0-100
        )
        
        if result is None:
            return None
        
        matched_alias, _, _ = result
        
        # Encontrar métrica canónica asociada al alias matched
        for alias, metric_name in alias_to_metric:
            if alias == matched_alias:
                return metric_name
        
        return None
    
    def list_tables(self) -> list[str]:
        """Lista todas las tablas disponibles."""
        return list(self._data["tables"].keys())
    
    def list_metrics(self, table: Optional[str] = None) -> list[str]:
        """
        Lista todas las métricas disponibles.
        
        Args:
            table: Filtrar por tabla (opcional)
        
        Returns:
            Lista de nombres canónicos de métricas
        """
        metrics = list(self._data["metrics"].keys())
        
        if table:
            metrics = [
                m for m in metrics
                if self._data["metrics"][m]["table"] == table
            ]
        
        return metrics


__all__ = ["DataDictionary", "MetricDefinition", "TableDefinition"]
