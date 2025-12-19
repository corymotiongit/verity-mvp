"""
Verity Data Engine - Value Index

Builds an inverted index of normalized values to their source columns.
This is the KEY piece that enables semantic resolution without manual configuration.

Example:
    "no sectorizada" -> [{"column": "TIPO_ENTIDAD", "count": 37}]
    "hidalgo" -> [{"column": "ENTIDAD_FEDERATIVA", "count": 11}, {"column": "MUNICIPIO", "count": 2}]
"""
import logging
import re
import unicodedata
from typing import Dict, List, Optional, Set

from .schemas import ValueIndex, ValueIndexEntry, DatasetProfile

logger = logging.getLogger(__name__)


class ValueIndexBuilder:
    """
    Builds and queries the Value Index for semantic token resolution.
    
    The Value Index maps normalized text values to their source columns,
    enabling the Intent Router to resolve user queries like "no sectorizada"
    to the correct column without LLM guessing.
    """
    
    # Tokens to ignore (common Spanish articles, prepositions, etc.)
    STOPWORDS: Set[str] = {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'de', 'del', 'en', 'por', 'para', 'con', 'sin',
        'que', 'cual', 'cuales', 'como', 'donde',
        'y', 'o', 'a', 'e',
        'es', 'son', 'hay', 'tiene', 'tienen',
        'cuantos', 'cuantas', 'cuanto', 'cuanta',
        'todos', 'todas', 'cada', 'me', 'te', 'se',
        'the', 'a', 'an', 'is', 'are', 'of', 'in', 'for', 'with'
    }
    
    # Minimum token length to index
    MIN_TOKEN_LENGTH = 2
    
    # Maximum values to index per column
    MAX_VALUES_PER_COLUMN = 1000
    
    def build(self, dataset_id: str, profile: DatasetProfile) -> ValueIndex:
        """
        Build a Value Index from a dataset profile.
        
        Args:
            dataset_id: Unique identifier for the dataset
            profile: DatasetProfile containing column analysis
            
        Returns:
            ValueIndex with normalized tokens mapped to columns
        """
        index = ValueIndex(dataset_id=dataset_id)
        
        for col, analysis in profile.column_analysis.items():
            if analysis.get("type") != "categorical":
                continue
            
            top_values = analysis.get("top_values", [])
            top_counts = analysis.get("top_counts", [])
            
            for i, value in enumerate(top_values[:self.MAX_VALUES_PER_COLUMN]):
                if value is None:
                    continue
                    
                # Normalize the value
                normalized = self._normalize(str(value))
                if not normalized or len(normalized) < self.MIN_TOKEN_LENGTH:
                    continue
                
                count = top_counts[i] if i < len(top_counts) else 0
                
                # Add to index
                if normalized not in index.entries:
                    index.entries[normalized] = []
                
                # Check if column already exists for this token
                existing = next((e for e in index.entries[normalized] if e.column == col), None)
                if existing:
                    existing.count += count
                else:
                    index.entries[normalized].append(ValueIndexEntry(
                        column=col,
                        count=count,
                        sample_values=[str(value)]
                    ))
                
                # Also index individual words from multi-word values
                words = normalized.split()
                if len(words) > 1:
                    for word in words:
                        if len(word) >= self.MIN_TOKEN_LENGTH and word not in self.STOPWORDS:
                            if word not in index.entries:
                                index.entries[word] = []
                            existing = next((e for e in index.entries[word] if e.column == col), None)
                            if not existing:
                                index.entries[word].append(ValueIndexEntry(
                                    column=col,
                                    count=count,
                                    sample_values=[str(value)]
                                ))
        
        logger.info(f"Built value index for {dataset_id}: {len(index.entries)} unique tokens")
        return index
    
    def _normalize(self, value: str) -> str:
        """
        Normalize a value for indexing.
        
        - Lowercase
        - Remove accents
        - Remove punctuation
        - Strip whitespace
        - Collapse multiple spaces
        """
        # Lowercase
        normalized = value.lower().strip()
        
        # Remove accents
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Remove punctuation (keep alphanumeric and spaces)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def extract_tokens(self, query: str) -> List[str]:
        """
        Extract meaningful tokens from a user query.
        
        Args:
            query: User's natural language query
            
        Returns:
            List of normalized tokens to lookup
        """
        normalized = self._normalize(query)
        words = normalized.split()
        
        # Filter stopwords and short tokens
        tokens = [w for w in words if len(w) >= self.MIN_TOKEN_LENGTH and w not in self.STOPWORDS]
        
        # Also try consecutive word pairs (bigrams) for multi-word values
        bigrams = []
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if words[i] not in self.STOPWORDS or words[i+1] not in self.STOPWORDS:
                bigrams.append(bigram)
        
        return tokens + bigrams
    
    def resolve(self, query: str, index: ValueIndex) -> List[Dict]:
        """
        Resolve tokens from query against the Value Index.
        
        Args:
            query: User's natural language query
            index: ValueIndex to search
            
        Returns:
            List of resolved mappings: [{"token": "...", "column": "...", "value": "..."}]
        """
        tokens = self.extract_tokens(query)
        resolved = []
        
        for token in tokens:
            entries = index.lookup(token)
            if entries:
                # Sort by count (most common first)
                sorted_entries = sorted(entries, key=lambda e: e.count, reverse=True)
                best = sorted_entries[0]
                resolved.append({
                    "token": token,
                    "column": best.column,
                    "value": best.sample_values[0] if best.sample_values else token,
                    "count": best.count,
                    "confidence": self._calculate_confidence(token, sorted_entries)
                })
        
        return resolved
    
    def _calculate_confidence(self, token: str, entries: List[ValueIndexEntry]) -> float:
        """
        Calculate confidence score for a resolution.
        
        High confidence if:
        - Token appears in only one column
        - High count relative to other columns
        """
        if len(entries) == 1:
            return 1.0
        
        # Multiple columns contain this value
        total = sum(e.count for e in entries)
        if total == 0:
            return 0.5
        
        best_ratio = entries[0].count / total
        return round(best_ratio, 2)
