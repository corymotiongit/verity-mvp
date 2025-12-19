"""
Verity Data Engine - Value Resolver

100% data-driven value resolution with fuzzy matching and organizational learning.
NO hardcoded aliases - learns from user confirmations.
"""
import logging
import re
import unicodedata
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ResolvedValue:
    """Result of value resolution."""
    original: str
    resolved: str
    column: str
    match_type: str  # "exact", "substring", "fuzzy", "learned", "none"
    score: float
    needs_confirmation: bool = False
    suggestions: Optional[List[str]] = None
    

@dataclass
class ConfirmationRequest:
    """Request for user confirmation when match is uncertain."""
    token: str
    column: str
    suggestions: List[str]
    scores: List[float]
    

# =============================================================================
# Organization Alias Memory (per-org learning)
# =============================================================================
class OrgAliasMemory:
    """
    Stores confirmed aliases per organization.
    
    When a user confirms "Coahuila" -> "Coahuila de Zaragoza",
    this is remembered for future queries from that org.
    """
    
    def __init__(self):
        # org_id -> {normalized_alias: canonical_value}
        self._memory: Dict[str, Dict[str, str]] = {}
    
    def get(self, org_id: str, alias: str) -> Optional[str]:
        """Get a learned alias for this org."""
        org_memory = self._memory.get(org_id, {})
        normalized = self._normalize(alias)
        return org_memory.get(normalized)
    
    def learn(self, org_id: str, alias: str, canonical: str):
        """Store a confirmed alias mapping."""
        if org_id not in self._memory:
            self._memory[org_id] = {}
        normalized = self._normalize(alias)
        self._memory[org_id][normalized] = canonical
        logger.info(f"[OrgAliasMemory] Learned: '{alias}' -> '{canonical}' for org {org_id}")
    
    def get_all(self, org_id: str) -> Dict[str, str]:
        """Get all learned aliases for an org."""
        return self._memory.get(org_id, {}).copy()
    
    def _normalize(self, text: str) -> str:
        """Normalize for consistent lookup."""
        if not text:
            return ""
        normalized = str(text).lower().strip()
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        return re.sub(r'\s+', ' ', normalized)


# Global memory instance
_org_alias_memory = OrgAliasMemory()


class ValueResolver:
    """
    100% data-driven value resolver.
    
    Resolution order:
    1. Learned aliases (from org memory)
    2. Exact match (normalized)
    3. Substring match
    4. Fuzzy match (SequenceMatcher)
    
    Thresholds:
    - score >= 0.90: Auto-pick
    - 0.75 <= score < 0.90: Request confirmation
    - score < 0.75: Return suggestions but no auto-pick
    """
    
    AUTOPICK_THRESHOLD = 0.90
    CONFIRMATION_THRESHOLD = 0.60  # Lowered to catch more typos
    SUGGESTION_THRESHOLD = 0.40  # Lowered for broader suggestions
    MAX_SUGGESTIONS = 3
    
    def __init__(self, org_id: Optional[str] = None):
        self.org_id = org_id
        self.memory = _org_alias_memory
    
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
        normalized = str(text).lower().strip()
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        return re.sub(r'\s+', ' ', normalized)
    
    def resolve(
        self,
        token: str,
        column_values: List[str],
        column_name: str = ""
    ) -> ResolvedValue:
        """
        Resolve a token against column values using data-driven matching.
        
        Args:
            token: User-provided value to resolve
            column_values: List of actual values in the column
            column_name: Column name for context
            
        Returns:
            ResolvedValue with resolution result
        """
        normalized_token = self.normalize(token)
        
        # Build normalized value map
        normalized_values = {}
        for v in column_values:
            if v is not None:
                normalized_values[self.normalize(str(v))] = str(v)
        
        # 1. Check learned aliases first (org memory)
        if self.org_id:
            learned = self.memory.get(self.org_id, token)
            if learned:
                # Verify learned value still exists in data
                learned_normalized = self.normalize(learned)
                if learned_normalized in normalized_values:
                    return ResolvedValue(
                        original=token,
                        resolved=normalized_values[learned_normalized],
                        column=column_name,
                        match_type="learned",
                        score=1.0
                    )
        
        # 2. Exact match (normalized)
        if normalized_token in normalized_values:
            return ResolvedValue(
                original=token,
                resolved=normalized_values[normalized_token],
                column=column_name,
                match_type="exact",
                score=1.0
            )
        
        # 3. Substring match (token in value OR value in token)
        for norm_val, orig_val in normalized_values.items():
            if normalized_token in norm_val:
                # Token is substring of value (e.g., "Coahuila" in "Coahuila de Zaragoza")
                score = len(normalized_token) / len(norm_val)
                score = min(0.95, score + 0.3)  # Boost substring matches
                return ResolvedValue(
                    original=token,
                    resolved=orig_val,
                    column=column_name,
                    match_type="substring",
                    score=score
                )
            if norm_val in normalized_token:
                # Value is substring of token
                score = len(norm_val) / len(normalized_token)
                return ResolvedValue(
                    original=token,
                    resolved=orig_val,
                    column=column_name,
                    match_type="substring",
                    score=score
                )
        
        # 4. Fuzzy match (SequenceMatcher)
        fuzzy_matches = []
        for norm_val, orig_val in normalized_values.items():
            score = SequenceMatcher(None, normalized_token, norm_val).ratio()
            if score >= self.SUGGESTION_THRESHOLD:
                fuzzy_matches.append((orig_val, score))
        
        # Sort by score descending
        fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
        
        if fuzzy_matches:
            best_match, best_score = fuzzy_matches[0]
            suggestions = [m[0] for m in fuzzy_matches[:self.MAX_SUGGESTIONS]]
            
            if best_score >= self.AUTOPICK_THRESHOLD:
                # Auto-pick
                return ResolvedValue(
                    original=token,
                    resolved=best_match,
                    column=column_name,
                    match_type="fuzzy",
                    score=best_score
                )
            elif best_score >= self.CONFIRMATION_THRESHOLD:
                # Needs confirmation
                return ResolvedValue(
                    original=token,
                    resolved=best_match,  # Tentative
                    column=column_name,
                    match_type="fuzzy",
                    score=best_score,
                    needs_confirmation=True,
                    suggestions=suggestions
                )
            else:
                # Return suggestions but no match
                return ResolvedValue(
                    original=token,
                    resolved="",
                    column=column_name,
                    match_type="none",
                    score=best_score,
                    needs_confirmation=False,
                    suggestions=suggestions
                )
        
        # 5. No match at all
        return ResolvedValue(
            original=token,
            resolved="",
            column=column_name,
            match_type="none",
            score=0.0
        )
    
    def confirm(self, token: str, confirmed_value: str):
        """
        Confirm a resolution and learn it for future queries.
        
        Called when user confirms a suggestion.
        """
        if self.org_id:
            self.memory.learn(self.org_id, token, confirmed_value)
    
    def get_confirmation_request(self, result: ResolvedValue) -> Optional[ConfirmationRequest]:
        """Get a confirmation request if resolution needs user input."""
        if result.needs_confirmation and result.suggestions:
            return ConfirmationRequest(
                token=result.original,
                column=result.column,
                suggestions=result.suggestions,
                scores=[result.score]  # Simplified; could include all scores
            )
        return None


# Singleton factory
_resolvers: Dict[str, ValueResolver] = {}

def get_value_resolver(org_id: Optional[str] = None) -> ValueResolver:
    """Get a ValueResolver, optionally scoped to an organization."""
    key = org_id or "__global__"
    if key not in _resolvers:
        _resolvers[key] = ValueResolver(org_id=org_id)
    return _resolvers[key]

def get_org_alias_memory() -> OrgAliasMemory:
    """Get the global org alias memory."""
    return _org_alias_memory
