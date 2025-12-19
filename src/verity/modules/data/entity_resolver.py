"""
Verity Data Engine - Entity Resolver

Handles fuzzy and alias-based matching for entity names.
Solves the "Coahuila" → "Coahuila de Zaragoza" problem.
"""
import logging
import re
import unicodedata
from typing import List, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    original: str
    resolved: str
    match_type: str  # "exact", "alias", "substring", "fuzzy", "none"
    score: float
    did_you_mean: Optional[List[str]] = None


# =============================================================================
# Mexican States Alias Map (common abbreviations and variations)
# =============================================================================
ENTIDAD_FEDERATIVA_ALIASES = {
    # Common short names -> official full names
    "coahuila": "Coahuila de Zaragoza",
    "michoacan": "Michoacán de Ocampo",
    "veracruz": "Veracruz de Ignacio de la Llave",
    "cdmx": "Ciudad de México",
    "ciudad de mexico": "Ciudad de México",
    "df": "Ciudad de México",
    "distrito federal": "Ciudad de México",
    "edomex": "México",
    "estado de mexico": "México",
    "bc": "Baja California",
    "baja california norte": "Baja California",
    "bcs": "Baja California Sur",
    "nl": "Nuevo León",
    "nuevo leon": "Nuevo León",
    "slp": "San Luis Potosí",
    "san luis potosi": "San Luis Potosí",
    "qroo": "Quintana Roo",
    "quintanaroo": "Quintana Roo",
    "ags": "Aguascalientes",
    "chis": "Chiapas",
    "chih": "Chihuahua",
    "gto": "Guanajuato",
    "gro": "Guerrero",
    "hgo": "Hidalgo",
    "jal": "Jalisco",
    "mich": "Michoacán de Ocampo",
    "mor": "Morelos",
    "nay": "Nayarit",
    "oax": "Oaxaca",
    "pue": "Puebla",
    "qro": "Querétaro",
    "sin": "Sinaloa",
    "son": "Sonora",
    "tab": "Tabasco",
    "tamps": "Tamaulipas",
    "tamaulipas": "Tamaulipas",
    "tlax": "Tlaxcala",
    "yuc": "Yucatán",
    "zac": "Zacatecas",
    "dgo": "Durango",
    "col": "Colima",
    "camp": "Campeche",
}


class EntityResolver:
    """
    Resolves user-provided entity names to actual values in the data.
    
    Resolution order:
    1. Exact match (normalized)
    2. Alias lookup
    3. Substring match
    4. Fuzzy match (if score >= threshold)
    5. Return "did_you_mean" suggestions
    """
    
    FUZZY_THRESHOLD = 0.85  # Auto-accept if score >= this
    SUGGESTION_THRESHOLD = 0.5  # Include in suggestions if score >= this
    MAX_SUGGESTIONS = 3
    
    def __init__(self, alias_maps: Optional[dict] = None):
        """
        Initialize with optional custom alias maps.
        
        Args:
            alias_maps: Dict of column_name -> {alias: canonical_value}
        """
        self.alias_maps = alias_maps or {}
        # Default: add ENTIDAD_FEDERATIVA aliases
        self.alias_maps.setdefault("ENTIDAD_FEDERATIVA", ENTIDAD_FEDERATIVA_ALIASES)
        self.alias_maps.setdefault("entidad_federativa", ENTIDAD_FEDERATIVA_ALIASES)
    
    def normalize(self, text: str) -> str:
        """
        Normalize text for matching.
        
        - Lowercase
        - Strip whitespace
        - Remove accents
        - Collapse multiple spaces
        """
        if not text:
            return ""
        
        # Lowercase and strip
        normalized = str(text).lower().strip()
        
        # Remove accents
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def resolve(
        self,
        token: str,
        column_values: List[str],
        column_name: str = ""
    ) -> ResolvedEntity:
        """
        Resolve a token against a list of known values.
        
        Args:
            token: User-provided value to resolve
            column_values: List of actual values in the column
            column_name: Column name (for alias lookup)
            
        Returns:
            ResolvedEntity with resolution result
        """
        normalized_token = self.normalize(token)
        
        # Normalize all column values for comparison
        normalized_values = {self.normalize(v): v for v in column_values if v}
        
        # 1. Exact match (normalized)
        if normalized_token in normalized_values:
            return ResolvedEntity(
                original=token,
                resolved=normalized_values[normalized_token],
                match_type="exact",
                score=1.0
            )
        
        # 2. Alias lookup
        alias_map = self.alias_maps.get(column_name, {})
        alias_map_lower = {self.normalize(k): v for k, v in alias_map.items()}
        
        if normalized_token in alias_map_lower:
            canonical = alias_map_lower[normalized_token]
            # Verify canonical exists in data
            canonical_normalized = self.normalize(canonical)
            if canonical_normalized in normalized_values:
                return ResolvedEntity(
                    original=token,
                    resolved=normalized_values[canonical_normalized],
                    match_type="alias",
                    score=1.0
                )
            # Alias points to value, but do substring check
            for norm_val, orig_val in normalized_values.items():
                if canonical_normalized in norm_val or norm_val in canonical_normalized:
                    return ResolvedEntity(
                        original=token,
                        resolved=orig_val,
                        match_type="alias",
                        score=0.95
                    )
        
        # 3. Substring match (token in value OR value in token)
        for norm_val, orig_val in normalized_values.items():
            if normalized_token in norm_val:
                return ResolvedEntity(
                    original=token,
                    resolved=orig_val,
                    match_type="substring",
                    score=0.9
                )
            if norm_val in normalized_token:
                return ResolvedEntity(
                    original=token,
                    resolved=orig_val,
                    match_type="substring",
                    score=0.85
                )
        
        # 4. Fuzzy match
        fuzzy_matches = []
        for norm_val, orig_val in normalized_values.items():
            score = SequenceMatcher(None, normalized_token, norm_val).ratio()
            if score >= self.SUGGESTION_THRESHOLD:
                fuzzy_matches.append((orig_val, score))
        
        # Sort by score descending
        fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
        
        if fuzzy_matches:
            best_match, best_score = fuzzy_matches[0]
            
            if best_score >= self.FUZZY_THRESHOLD:
                return ResolvedEntity(
                    original=token,
                    resolved=best_match,
                    match_type="fuzzy",
                    score=best_score
                )
            
            # Return with suggestions
            suggestions = [m[0] for m in fuzzy_matches[:self.MAX_SUGGESTIONS]]
            return ResolvedEntity(
                original=token,
                resolved="",
                match_type="none",
                score=best_score,
                did_you_mean=suggestions
            )
        
        # 5. No match at all
        return ResolvedEntity(
            original=token,
            resolved="",
            match_type="none",
            score=0.0,
            did_you_mean=None
        )
    
    def resolve_multiple(
        self,
        tokens: List[str],
        column_values: List[str],
        column_name: str = ""
    ) -> List[ResolvedEntity]:
        """Resolve multiple tokens."""
        return [self.resolve(t, column_values, column_name) for t in tokens]


# Singleton instance
_resolver: Optional[EntityResolver] = None

def get_entity_resolver() -> EntityResolver:
    """Get the global EntityResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
