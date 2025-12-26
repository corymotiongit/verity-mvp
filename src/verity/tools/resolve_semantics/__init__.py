"""
resolve_semantics@1.0 - Resolución semántica usando Data Dictionary

Responsabilidad:
- Convertir pregunta del usuario a plan de datos estructurado
- Usar Data Dictionary para mapear términos a métricas
- Hacer fuzzy match contra aliases canónicos
- NO inventar métricas
- Si no encuentra match, retornar error con sugerencias
- Persistir confidence por conversación para tracking

Input: pregunta + data_dictionary_version + available_tables
Output: tables + metrics (con alias_matched canónico) + filters + time_grain + confidence

REGLA CRÍTICA: confidence debe persistirse para análisis de calidad.
Ver schema.json para contrato completo.
"""

from verity.tools.base import BaseTool, ToolDefinition
from typing import Any
import json
from pathlib import Path

from verity.exceptions import AmbiguousMetricException, NoTableMatchException, UnresolvedMetricException


class ResolveSemanticsTool(BaseTool):
    """
    Tool determinista (con fuzzy match) para resolver semántica.
    
    NO usa LLM para decidir métricas.
    Solo mapea contra Data Dictionary existente.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        """Carga definición desde schema.json"""
        schema_path = Path(__file__).parent / "schema.json"
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        
        return ToolDefinition(
            name="resolve_semantics",
            version="1.0",
            input_schema=schema["input"],
            output_schema=schema["output"],
            is_deterministic=False,  # Tiene fuzzy match
            execution_mode="local"
        )
    
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Resuelve semántica de la pregunta.
        
        Proceso:
        1. Cargar Data Dictionary
        2. Extraer términos clave de la pregunta
        3. Hacer fuzzy match contra aliases de métricas
        4. Si no hay match, retornar unresolved_terms
        5. Construir plan de datos estructurado
        """
        from rapidfuzz import fuzz, process
        from verity.data import DataDictionary

        question = input_data["question"]
        available_tables = input_data["available_tables"]
        intent = (input_data.get("intent") or "").strip().lower()

        conversation_context = input_data.get("conversation_context") if isinstance(input_data, dict) else None
        if not isinstance(conversation_context, dict):
            conversation_context = {}
        last_metric = conversation_context.get("last_metric") if isinstance(conversation_context.get("last_metric"), str) else None
        last_table = conversation_context.get("last_table") if isinstance(conversation_context.get("last_table"), str) else None

        # Cargar Data Dictionary v1 (authoritative)
        dd = DataDictionary()

        # Reglas estrictas
        threshold = 85  # fijo (>=85)
        ambiguity_margin = 3  # puntos; si está muy cerca, pedir aclaración

        # Construir índice alias -> métricas (un alias puede mapear a múltiples métricas)
        alias_to_metrics: dict[str, set[str]] = {}
        for metric_name in dd.list_metrics():
            metric_def = dd.get_metric(metric_name)

            canonical_variants = {
                metric_name.lower(),
                metric_name.lower().replace("_", " "),
            }
            for v in canonical_variants:
                alias_to_metrics.setdefault(v, set()).add(metric_name)

            for alias in metric_def.aliases:
                variants = {
                    alias.lower(),
                    alias.lower().replace("_", " "),
                }
                for v in variants:
                    alias_to_metrics.setdefault(v, set()).add(metric_name)

        aliases = list(alias_to_metrics.keys())

        # Generar frases candidatas (determinístico, sin NLP creativo)
        phrases = self._candidate_phrases(question)

        def _looks_like_followup(q: str) -> bool:
            qn = self._normalize_text(q)
            # Heurística conservadora: follow-ups cortos o con conectores típicos
            if len(qn) <= 14:
                return True
            if qn.startswith("y "):
                return True
            if any(t in qn for t in ["lo mismo", "igual", "tambien", "también", "ahora", "y ahora", "y por", "y para"]):
                return True
            return False

        is_followup = _looks_like_followup(question)

        # Agregar por métrica el mejor score observado en cualquier frase
        metric_best: dict[str, dict[str, Any]] = {}
        for phrase in phrases:
            if not phrase:
                continue

            extracted = process.extract(
                phrase,
                aliases,
                scorer=fuzz.WRatio,
                limit=8,
            )

            for matched_alias, score, _ in extracted:
                metrics_for_alias = alias_to_metrics.get(matched_alias) or set()
                for metric_name in metrics_for_alias:
                    base_score = float(score)

                    # Contexto conversacional leve: solo sesgo en follow-ups.
                    boost = 0.0
                    boost_reasons: list[str] = []
                    if is_followup and last_metric and metric_name == last_metric:
                        boost += 3.0
                        boost_reasons.append("last_metric")
                    if is_followup and last_table:
                        try:
                            if dd.get_metric(metric_name).table == last_table:
                                boost += 1.5
                                boost_reasons.append("last_table")
                        except KeyError:
                            pass

                    # Conservador: no permitir que el boost rescate matches muy débiles.
                    boosted_score = base_score
                    if boost and base_score >= 70.0:
                        boosted_score = min(100.0, base_score + boost)

                    existing = metric_best.get(metric_name)
                    if existing is None or boosted_score > existing["score"]:
                        metric_best[metric_name] = {
                            "metric": metric_name,
                            "score": float(boosted_score),
                            "base_score": float(base_score),
                            "context_boost": float(boosted_score - base_score),
                            "context_boost_reasons": boost_reasons,
                            "matched_alias": matched_alias,
                            "matched_phrase": phrase,
                        }

        ranked = sorted(metric_best.values(), key=lambda x: x["score"], reverse=True)

        # Sugerencias para errores (top 5)
        suggestions = [
            {"metric": r["metric"], "score": r["score"], "matched_alias": r["matched_alias"]}
            for r in ranked[:5]
        ]

        if not ranked or ranked[0]["score"] < threshold:
            raise UnresolvedMetricException(user_input=question, suggestions=suggestions)

        # Ambigüedad: múltiples métricas por encima del umbral y demasiado cercanas
        top = ranked[0]
        candidates_close = [
            r for r in ranked
            if r["score"] >= threshold and (top["score"] - r["score"]) <= ambiguity_margin
        ]
        if len(candidates_close) >= 2:
            raise AmbiguousMetricException(user_input=question, candidates=candidates_close[:5])

        metric_name = top["metric"]
        metric_def = dd.get_metric(metric_name)
        table_def = dd.get_table(metric_def.table)

        # Tabla requerida debe estar disponible
        if metric_def.table not in available_tables:
            raise NoTableMatchException(table=metric_def.table, available_tables=available_tables)

        # Confidence real: score base + penalidades simples
        confidence = top["score"] / 100.0
        penalty = 0.0
        if len(top["matched_alias"]) <= 5:
            penalty += 0.05
        # Penalizar matches perfectos sobre queries muy cortas (p.ej., abreviaturas/identificadores)
        if top["score"] >= 99.5 and len(top["matched_phrase"]) <= 10:
            penalty += 0.05
        if top["matched_phrase"] != self._normalize_text(question):
            penalty += 0.03
        # Penalizar supuestos implícitos (cuando usamos contexto conversacional para sesgar)
        ctx_boost = float(top.get("context_boost", 0.0) or 0.0)
        if ctx_boost > 0:
            penalty += min(0.18, 0.06 + (ctx_boost / 100.0))
        confidence = max(0.0, min(1.0, confidence - penalty))

        matched_metrics = [
            {
                "name": metric_name,
                "alias_matched": top["matched_alias"],
                "definition": metric_def.expression,
                "requires": metric_def.requires,
                "filters": metric_def.filters,
                "format": metric_def.format,
                "match_score": top["score"],
                "matched_phrase": top["matched_phrase"],
                "base_match_score": float(top.get("base_score", top["score"])),
                "context_boost": float(top.get("context_boost", 0.0)),
                "context_boost_reasons": top.get("context_boost_reasons", []),
            }
        ]

        # Filters: incluir filtros automáticos de la(s) métrica(s)
        all_filters: list[dict[str, Any]] = []
        for m in matched_metrics:
            all_filters.extend(m.get("filters", []))

        def _infer_time_grain_for_compare(q: str) -> str:
            qn = self._normalize_text(q)
            if any(k in qn for k in ["semana", "semanas", "week", "weeks", "wow", "last week", "semana pasada"]):
                return "week"
            if any(k in qn for k in ["dia", "días", "dias", "day", "days", "diario", "daily"]):
                return "day"
            return "month"

        def _infer_period_tokens(q: str, grain: str) -> tuple[dict[str, str], dict[str, str]]:
            qn = self._normalize_text(q)
            # Baseline vs compare (determinístico, MVP)
            if grain == "week":
                return ({"relative": "previous_week"}, {"relative": "current_week"})
            if grain == "day":
                return ({"relative": "previous_day"}, {"relative": "current_day"})
            # default month
            if any(k in qn for k in ["año pasado", "ano pasado", "year over year", "yoy"]):
                return ({"relative": "same_month_last_year"}, {"relative": "current_month"})
            if any(k in qn for k in ["mes pasado", "last month", "mom"]):
                return ({"relative": "previous_month"}, {"relative": "current_month"})
            return ({"relative": "previous_month"}, {"relative": "current_month"})

        output: dict[str, Any] = {
            "tables": [metric_def.table],
            "metrics": matched_metrics,
            "filters": all_filters,
            "confidence": confidence,
            "unresolved_terms": [],
            "data_dictionary_version": dd.version,
        }

        # COMPARE_PERIODS semantics: time_column explícita + group_by temporal + baseline vs compare
        is_compare = intent == "compare"
        if is_compare and table_def.time_column:
            grain = _infer_time_grain_for_compare(question)
            baseline, compare = _infer_period_tokens(question, grain)
            output.update(
                {
                    "time_column": table_def.time_column,
                    "time_grain": grain,
                    "group_by": [f"{table_def.time_column}__{grain}"],
                    "baseline_period": baseline,
                    "compare_period": compare,
                }
            )
        return output
    
    def _normalize_text(self, text: str) -> str:
        return (
            text.lower()
            .replace("_", " ")
            .replace("?", " ")
            .replace("!", " ")
            .replace(".", " ")
            .replace(",", " ")
            .replace(";", " ")
            .replace(":", " ")
            .strip()
        )

    def _candidate_phrases(self, question: str) -> list[str]:
        """Genera frases candidatas para matching (determinístico)."""
        normalized = self._normalize_text(question)
        tokens = [t for t in normalized.split() if t]

        stopwords = {
            "cual",
            "cuales",
            "cuanto",
            "cuantos",
            "como",
            "donde",
            "cuando",
            "quien",
            "quienes",
            "para",
            "sobre",
            "desde",
            "hasta",
            "entre",
            "tenemos",
            "tiene",
            "tienen",
            "dame",
            "muestra",
            "quiero",
            "necesito",
            "por",
            "del",
            "de",
            "la",
            "el",
            "los",
            "las",
            "un",
            "una",
            "y",
            "o",
            "en",
            "a",
            "al",
            "con",
            "sin",
            "mes",
            "meses",
            "dia",
            "días",
            "semana",
            "semanas",
            "año",
            "años",
        }

        content_tokens = [t for t in tokens if t not in stopwords and len(t) >= 3]

        phrases: list[str] = []
        phrases.append(normalized)

        # Unigrams
        phrases.extend(content_tokens)

        # Bigrams/trigrams para capturar expresiones compuestas
        for n in (2, 3):
            for i in range(0, len(content_tokens) - n + 1):
                phrases.append(" ".join(content_tokens[i : i + n]))

        # Dedup preservando orden
        seen: set[str] = set()
        out: list[str] = []
        for p in phrases:
            p = p.strip()
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
        return out


__all__ = ["ResolveSemanticsTool"]
