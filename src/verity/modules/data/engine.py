"""
Verity Data Engine - Core Engine

Orchestrates the complete data query pipeline:
1. Intent Router (deterministic token resolution)
2. Code Generation (LLM)
3. Sandbox Execution
4. Auto-Retry
5. Response Formatting

This is the main entry point for data queries.
"""
import logging
from typing import Optional, Tuple, List, Dict, Any
from uuid import uuid4

from .schemas import (
    DatasetProfile, 
    ValueIndex, 
    CodeExecutionRequest, 
    CodeExecutionResult,
    DataEngineResponse,
    ResolvedFilter
)
from .profiler import DatasetProfiler
from .value_index import ValueIndexBuilder
from .sandbox import DataSandbox
# from .agent import CodeGeneratorAgent  # Moved to legacy_frozen/code_generator_agent.py (outside src/)
# from .charts import ChartAgent  # Moved to legacy_frozen/chart_agent.py (outside src/)
from .value_resolver import ValueResolver, get_value_resolver, get_org_alias_memory

logger = logging.getLogger(__name__)


class DataEngineCache:
    """
    In-memory cache for dataset profiles and value indices.
    
    Invalidated on dataset update/re-ingest.
    """
    
    def __init__(self):
        self._profiles: Dict[str, DatasetProfile] = {}
        self._indices: Dict[str, ValueIndex] = {}
        self._file_paths: Dict[str, str] = {}  # dataset_id -> file_path
    
    def get_profile(self, dataset_id: str) -> Optional[DatasetProfile]:
        return self._profiles.get(dataset_id)
    
    def set_profile(self, dataset_id: str, profile: DatasetProfile):
        self._profiles[dataset_id] = profile
    
    def get_index(self, dataset_id: str) -> Optional[ValueIndex]:
        return self._indices.get(dataset_id)
    
    def set_index(self, dataset_id: str, index: ValueIndex):
        self._indices[dataset_id] = index
    
    def get_file_path(self, dataset_id: str) -> Optional[str]:
        return self._file_paths.get(dataset_id)
    
    def set_file_path(self, dataset_id: str, file_path: str):
        self._file_paths[dataset_id] = file_path
    
    def invalidate(self, dataset_id: str):
        """Invalidate all cached data for a dataset."""
        self._profiles.pop(dataset_id, None)
        self._indices.pop(dataset_id, None)
        self._file_paths.pop(dataset_id, None)
        logger.info(f"Invalidated cache for dataset: {dataset_id}")
    
    def list_datasets(self) -> List[str]:
        """List all cached dataset IDs."""
        return list(self._profiles.keys())
    
    def clear_all(self):
        """Clear all cached data."""
        self._profiles.clear()
        self._indices.clear()
        self._file_paths.clear()
        logger.info("Cleared all DataEngine cache")


# Global cache instance
_cache = DataEngineCache()


class DataEngine:
    """
    Main Data Engine orchestrator.
    
    Responsibilities:
    - Ingest datasets (profile + index)
    - Route queries through Intent Router
    - Resolve entities with fuzzy matching
    - Generate and execute code
    - Handle auto-retry
    - Format responses
    """
    
    MAX_RETRIES = 2
    
    def __init__(self):
        self.profiler = DatasetProfiler()
        self.index_builder = ValueIndexBuilder()
        self.sandbox = DataSandbox()
        # LEGACY: CodeGeneratorAgent and ChartAgent have been moved to legacy_frozen/ (outside src/)
        # These are set to None to avoid breaking existing code
        self.code_generator = None  # Was: CodeGeneratorAgent()
        self.chart_agent = None  # Was: ChartAgent()
        self.cache = _cache
        
    def clear_cache(self):
        """Clear all internal caches."""
        self.cache.clear_all()
        
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache.list_datasets()),
            "datasets": self.cache.list_datasets(),
            "hits": 0, # Future
            "misses": 0
        }

    
    # =========================================================================
    # Dataset Ingestion
    # =========================================================================
    
    def ingest(self, dataset_id: str, file_path: str) -> DatasetProfile:
        """
        Ingest a dataset: profile and build value index.
        
        Args:
            dataset_id: Unique identifier for the dataset
            file_path: Relative path to file in uploads/
            
        Returns:
            DatasetProfile
        """
        logger.info(f"Ingesting dataset: {dataset_id} from {file_path}")
        
        # Invalidate existing cache
        self.cache.invalidate(dataset_id)
        
        # Profile
        profile = self.profiler.profile(dataset_id, file_path)
        self.cache.set_profile(dataset_id, profile)
        self.cache.set_file_path(dataset_id, file_path)
        
        # Build value index
        index = self.index_builder.build(dataset_id, profile)
        self.cache.set_index(dataset_id, index)
        
        logger.info(f"Ingestion complete: {profile.shape[0]} rows, {len(index.entries)} indexed tokens")
        return profile
    
    def get_or_ingest(self, dataset_id: str, file_path: str) -> Tuple[DatasetProfile, ValueIndex]:
        """
        Get cached profile/index or ingest if not cached.
        """
        profile = self.cache.get_profile(dataset_id)
        index = self.cache.get_index(dataset_id)
        
        if profile is None or index is None:
            profile = self.ingest(dataset_id, file_path)
            index = self.cache.get_index(dataset_id)
        
        return profile, index
    
    # =========================================================================
    # Intent Router
    # =========================================================================
    
    def resolve_intent(
        self, 
        query: str, 
        index: ValueIndex, 
        profile: DatasetProfile,
        org_id: Optional[str] = None
    ) -> List[ResolvedFilter]:
        """
        Resolve tokens from query against the Value Index with fuzzy matching.
        
        This happens BEFORE the LLM, making column/value resolution deterministic.
        Uses ValueResolver for 100% data-driven matching with org learning.
        """
        # Get ValueResolver scoped to this org (for learning)
        value_resolver = get_value_resolver(org_id=org_id)
        
        # Step 1: Get basic resolutions from Value Index
        resolutions = self.index_builder.resolve(query, index)
        
        filters = []
        for r in resolutions:
            filters.append(ResolvedFilter(
                column=r["column"],
                value=r["value"],
                confidence=r.get("confidence", 1.0)
            ))
        
        # Step 2: Try ValueResolver for tokens that weren't resolved
        query_tokens = self.index_builder.extract_tokens(query)
        resolved_tokens = {self.index_builder._normalize(f.value) for f in filters}
        
        pending_confirmations = []  # Collect confirmations needed
        
        for token in query_tokens:
            normalized_token = self.index_builder._normalize(token)
            if normalized_token in resolved_tokens:
                continue  # Already resolved
            
            # Try to resolve against each categorical column
            for col, analysis in profile.column_analysis.items():
                if analysis.get("type") != "categorical":
                    continue
                
                column_values = analysis.get("top_values", [])
                if not column_values:
                    continue
                
                result = value_resolver.resolve(
                    token=token,
                    column_values=column_values,
                    column_name=col
                )
                
                if result.match_type in ("exact", "learned", "substring"):
                    # High confidence - use it
                    filters.append(ResolvedFilter(
                        column=col,
                        value=result.resolved,
                        confidence=result.score
                    ))
                    logger.info(f"ValueResolver matched '{token}' -> '{result.resolved}' ({result.match_type}, score={result.score})")
                    break
                elif result.match_type == "fuzzy" and result.score >= 0.90:
                    # Auto-pick fuzzy match
                    filters.append(ResolvedFilter(
                        column=col,
                        value=result.resolved,
                        confidence=result.score
                    ))
                    logger.info(f"ValueResolver auto-picked fuzzy: '{token}' -> '{result.resolved}' (score={result.score})")
                    break
                elif result.match_type == "fuzzy" and result.needs_confirmation:
                    # Needs confirmation (0.75-0.90)
                    # For now, use it tentatively but log
                    filters.append(ResolvedFilter(
                        column=col,
                        value=result.resolved,
                        confidence=result.score
                    ))
                    pending_confirmations.append({
                        "token": token,
                        "value": result.resolved,
                        "suggestions": result.suggestions
                    })
                    logger.info(f"ValueResolver tentative (needs confirm): '{token}' -> '{result.resolved}' (score={result.score}, suggestions={result.suggestions})")
                    break
                elif result.suggestions:
                    logger.info(f"ValueResolver: '{token}' not matched. Suggestions: {result.suggestions}")
        
        if filters:
            logger.info(f"Resolved {len(filters)} filters: {[(f.column, f.value) for f in filters]}")
        
        return filters
    
    # =========================================================================
    # Query Execution Pipeline
    async def initialize(self):
        """Async initialization if needed."""
        pass
    
    # -------------------------------------------------------------------------
    # Cache Management (Admin)
    # -------------------------------------------------------------------------
    
    def clear_cache(self):
        """Clear all internal caches."""
        _cache.clear_all()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(_cache.list_datasets()),
            "datasets": _cache.list_datasets(),
            "hits": 0, # Future: Implement hits/misses tracking
            "misses": 0
        }

    async def ingest_dataset(
        self, 
        file_path: str,
        dataset_id: str = None
    ) -> DatasetProfile:
        """
        Ingest a dataset (profile and build value index) and cache it.
        This is a wrapper around the internal ingest method.
        """
        if dataset_id is None:
            # Generate a unique ID if not provided
            dataset_id = f"dataset_{uuid.uuid4().hex}"
            logger.info(f"Generated dataset_id: {dataset_id} for {file_path}")

        return self.ingest(dataset_id, file_path)

    async def query(
        self,
        user_query: str,
        dataset_id: str,
        file_path: str,
        user_role: str = "user",
        generate_chart: bool = False
    ) -> DataEngineResponse:
        """
        Execute a natural language query against a dataset.
        
        Args:
            user_query: Natural language question
            dataset_id: Dataset identifier
            file_path: Path to data file
            user_role: Role of the user requesting data
        """
        logger.info(f"Query: {user_query[:50]}... (Role: {user_role})")
        
        # 1. Get or ingest profile/index
        profile, index = self.get_or_ingest(dataset_id, file_path)
        
        # 2. Resolve intent (with EntityResolver for fuzzy matching)
        resolved_filters = self.resolve_intent(user_query, index, profile)
        
        # 3. Load DataFrame
        try:
            df = self.sandbox.load_dataframe(file_path)
        except Exception as e:
            return DataEngineResponse(
                answer=f"Error cargando el archivo: {e}",
                dataset_id=dataset_id
            )
        
        # 4. Generate and execute with retry (and recalc support)
        last_error = None
        recalc_instruction = None
        
        # Extended attempts for potential recalc
        for attempt in range(1, self.MAX_RETRIES + 3):
            try:
                # Generate code
                code = await self.code_generator.generate(
                    query=user_query,
                    profile=profile,
                    resolved_filters=resolved_filters,
                    previous_error=last_error,
                    user_role=user_role,
                    additional_instruction=recalc_instruction
                )
                
                # Create request
                request = self.code_generator.create_request(
                    dataset_id=dataset_id,
                    code=code,
                    resolved_filters=resolved_filters,
                    attempt=attempt
                )
                
                # Execute
                result = self.sandbox.execute(request, df)
                
                if result.success:
                    # Extract evidence for context (always useful)
                    op, fil, _ = self._extract_evidence(result.executed_code, resolved_filters or [])
                    evidence_ref = f"Operation: {op}, Filters: {fil}, Rows: {result.row_count}"

                    # CHART GENERATION LOGIC
                    final_chart_spec = None
                    
                    if generate_chart and result.table_preview and "rows" in result.table_preview:
                         try:
                            chart_response = await self.chart_agent.generate_spec(
                                query=user_query,
                                table_data=result.table_preview,
                                evidence_ref=evidence_ref # Use the newly defined evidence_ref
                            )
                            
                            if chart_response.chart_spec:
                                # Success!
                                final_chart_spec = {
                                    "type": "plotly",
                                    "spec": chart_response.chart_spec.model_dump()
                                }
                            elif chart_response.needs_recalc and not recalc_instruction:
                                # Needs recalc!
                                recalc_instruction = chart_response.recalc_request
                                logger.info(f"Chart recalc requested: {recalc_instruction}")
                                last_error = f"Chart agent requested recalc: {recalc_instruction}"
                                continue # Loop again!
                                
                         except Exception as exc:
                             logger.error(f"Chart gen failed in loop: {exc}")
                    
                    # If we got here, either no chart driven recalc needed, or chart success, or second attempt done
                    return await self._format_success_response(
                        user_query, result, dataset_id, resolved_filters, 
                        chart_spec_data=final_chart_spec
                    )
                else:
                    last_error = result.error
                    logger.warning(f"Attempt {attempt} failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt} exception: {e}")
        
        # All retries exhausted
        return DataEngineResponse(
            answer=f"No pude ejecutar el análisis después de {self.MAX_RETRIES} intentos. Último error: {last_error}",
            dataset_id=dataset_id
        )
    
    async def _format_success_response(
        self,
        query: str,
        result: CodeExecutionResult,
        dataset_id: str,
        resolved_filters: list = None,
        chart_spec_data: dict = None
    ) -> DataEngineResponse:
        """Format a successful execution result with structured table data and audit evidence."""
        from .schemas import TablePreview
        
        value = result.value
        table_data = result.table_preview  # Now a dict with columns/rows
        
        # Determine answer type and format
        answer_type = "text"
        table_preview = None
        table_markdown = None
        
        # Format based on result type
        # Format based on result type
        if table_data and "columns" in table_data and "rows" in table_data:
            # We have structured table data (PRIORITY)
            answer_type = "table"
            
            columns = table_data["columns"]
            rows = table_data["rows"]
            total_rows = table_data.get("total_rows", len(rows))
            
            # Create TablePreview for frontend
            table_preview = TablePreview(
                columns=columns,
                rows=rows[:50],  # Limit to 50 for preview
                total_rows=total_rows
            )
            
            # Use provided value string as description if available, else generic
            if isinstance(value, str) and "DataFrame" in value:
                 answer = value
            else:
                 answer = f"Se encontraron {total_rows} registros."
            
            # Generate markdown for chat (top 15)
            table_markdown = self._generate_markdown_table(columns, rows[:15])
            if total_rows > 15:
                table_markdown += f"\n\n*... y {total_rows - 15} filas más.*"

        elif isinstance(value, (int, float)):
            answer_type = "scalar"
            if isinstance(value, float):
                answer = f"{value:,.2f}" if abs(value) > 1000 else str(round(value, 4))
            else:
                answer = f"{value:,}"
        elif isinstance(value, str):
            answer = value
        elif isinstance(value, bool):
            answer = "Sí" if value else "No"
        elif value is None:
            answer = "No se encontraron resultados."


        elif isinstance(value, dict):
            # Dict without structured table data - format inline
            if len(value) <= 10:
                items = [f"**{k}**: {self._format_number(v)}" for k, v in value.items()]
                answer = ", ".join(items)
            else:
                answer = f"Resultado con {len(value)} elementos"
                items = [f"**{k}**: {self._format_number(v)}" for k, v in list(value.items())[:10]]
                answer += ": " + ", ".join(items) + "..."
        else:
            answer = str(value)
        
        # Extract audit evidence from code and filters
        operation, filters_applied, columns_used = self._extract_evidence(
            result.executed_code, 
            resolved_filters or []
        )
        
        # Use row evidence from sandbox execution (real tracked data)
        row_ids = result.row_ids if result.row_ids else []
        row_count = result.row_count if result.row_count else len(row_ids)
        sample_rows = result.sample_rows if result.sample_rows else []
        
        # If sandbox didn't capture, try from table_data as fallback
        if not row_ids and table_data and "rows" in table_data:
            # Fallback: generate from table (less accurate but better than nothing)
            row_ids = list(range(2, min(len(table_data["rows"]) + 2, 102)))
            row_count = table_data.get("total_rows", len(table_data["rows"]))
            
            # Generate sample rows
            if not sample_rows and "columns" in table_data:
                cols = table_data["columns"][:5]
                for i, row_data in enumerate(table_data["rows"][:3]):
                    sample = dict(zip(cols, row_data[:5]))
                    sample["_row_id"] = i + 2
                    sample_rows.append(sample)
        
        # Determine match_policy based on operation
        match_policy = "all"
        if operation == "lookup" and row_count == 1:
            match_policy = "first"
        elif operation == "lookup" and row_count > 1:
            match_policy = "all"  # Could be "error_if_multiple" for strict mode
        
        # Extract value info for scalar results
        raw_value = None
        value_type = None
        unit = None
        if answer_type == "scalar" and value is not None:
            raw_value = value
            if isinstance(value, (int, float)):
                value_type = "number"
                # Try to detect unit from column name or query
                if columns_used:
                    col_lower = columns_used[-1].lower() if columns_used else ""
                    if "precio" in col_lower or "monto" in col_lower or "costo" in col_lower:
                        unit = "MXN"  # Default for price columns
            elif isinstance(value, str):
                value_type = "text"
            elif isinstance(value, bool):
                value_type = "boolean"
        
        # Construct evidence ref string
        evidence_ref = f"Operation: {operation}, Filters: {filters_applied}, Rows: {row_count}"

        return DataEngineResponse(
            answer=answer,
            answer_type=answer_type,
            table_preview=table_preview,
            table_markdown=table_markdown,
            chart_spec=chart_spec_data,
            dataset_id=dataset_id,
            evidence_ref=evidence_ref,
            operation=operation,
            match_policy=match_policy,
            filters_applied=filters_applied,
            columns_used=columns_used or [],
            row_ids=row_ids,
            row_count=row_count,
            row_limit=100 if row_count > 100 else None,
            sample_rows=sample_rows,
            raw_value=raw_value,
            value_type=value_type,
            unit=unit,
            executed_code=result.executed_code  # Internal only
        )
    
    def _extract_evidence(self, code: str, resolved_filters: list) -> tuple:
        """Extract operation type and filters from executed code."""
        if not code:
            return None, None, None
        
        # Detect operation type
        operation = "query"
        if "len(" in code or "count()" in code or ".shape" in code:
            operation = "count"
        elif "sum(" in code or ".sum()" in code:
            operation = "aggregate_sum"
        elif "mean(" in code or ".mean()" in code:
            operation = "aggregate_mean"
        elif "groupby" in code:
            operation = "group_aggregate"
        elif "['" in code and "==" in code:
            operation = "lookup"
        elif "filter" in code.lower() or "[" in code:
            operation = "filter"
        
        # Extract filters from resolved_filters
        filters_applied = []
        columns_used = []
        for f in resolved_filters:
            filters_applied.append(f"{f.column} = '{f.value}'")
            if f.column not in columns_used:
                columns_used.append(f.column)
        
        # Try to detect additional columns from code
        import re
        col_matches = re.findall(r"\['([^']+)'\]", code)
        for col in col_matches:
            if col not in columns_used:
                columns_used.append(col)
        
        return operation, filters_applied or None, columns_used or None
    
    def _generate_markdown_table(self, columns: list, rows: list) -> str:
        """Generate a markdown table from columns and rows."""
        if not columns or not rows:
            return ""
        
        # Header
        header = "| " + " | ".join(str(c) for c in columns) + " |"
        separator = "|" + "|".join(["---"] * len(columns)) + "|"
        
        # Rows
        row_lines = []
        for row in rows:
            formatted = [self._format_number(v) for v in row]
            row_lines.append("| " + " | ".join(formatted) + " |")
        
        return header + "\n" + separator + "\n" + "\n".join(row_lines)
    
    def _format_number(self, val) -> str:
        """Format numbers nicely for display."""
        if val is None:
            return ""
        if isinstance(val, float):
            if abs(val) >= 1_000_000:
                return f"${val/1_000_000:,.2f}M"
            elif abs(val) >= 1_000:
                return f"${val:,.0f}"
            else:
                return f"{val:.2f}"
        if isinstance(val, int):
            if abs(val) >= 1_000_000:
                return f"{val/1_000_000:,.2f}M"
            else:
                return f"{val:,}"
        return str(val)


# Singleton instance
_engine: Optional[DataEngine] = None

def get_data_engine() -> DataEngine:
    """Get the global DataEngine instance."""
    global _engine
    if _engine is None:
        _engine = DataEngine()
    return _engine
