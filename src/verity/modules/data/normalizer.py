"""
Verity Data Engine - File Normalizer

Transforms raw uploaded files into canonical format for consistent processing.

Pipeline:
1. Upload → Save raw file (original preserved)
2. Normalize → Generate canonical file (UTF-8, clean headers, consistent format)
3. Audit → Log all transformations applied

The Data Executor always operates on canonical files.
"""
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TransformRule:
    """Record of a single transformation applied."""
    rule: str
    details: dict = field(default_factory=dict)


@dataclass
class NormalizationAudit:
    """Complete audit log of file normalization."""
    doc_id: str
    raw_file: str
    canonical_file: str
    timestamp: str
    transforms_applied: list[TransformRule] = field(default_factory=list)
    rows_before: int = 0
    rows_after: int = 0
    rows_dropped: int = 0
    drop_reasons: list[dict] = field(default_factory=list)
    sample_issues: list[dict] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    content_hash_raw: str = ""
    content_hash_canonical: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert TransformRule objects to dicts
        data["transforms_applied"] = [asdict(t) for t in self.transforms_applied]
        return data


class FileNormalizer:
    """
    Normalizes uploaded files to a canonical format.
    
    Transformations:
    - Encoding: Convert to UTF-8
    - Headers: Strip whitespace, remove special chars
    - Quotes: Strip surrounding quotes from values
    - Separators: Detect and standardize
    - Types: Basic type inference
    - Empty rows: Remove completely empty rows
    """
    
    # Standard canonical format
    CANONICAL_ENCODING = "utf-8"
    CANONICAL_SEPARATOR = ","
    CANONICAL_QUOTING = 1  # csv.QUOTE_MINIMAL
    
    # Detection thresholds
    MAX_SAMPLE_ISSUES = 10
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.raw_dir = self.base_path / "raw"
        self.canonical_dir = self.base_path / "canonical"
        self.audit_dir = self.base_path / "audit"
        
        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.canonical_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize(
        self, 
        doc_id: str, 
        source_path: Path,
        original_filename: str
    ) -> tuple[Path, NormalizationAudit]:
        """
        Normalize a file to canonical format.
        
        Args:
            doc_id: Document ID
            source_path: Path to the uploaded file
            original_filename: Original filename for reference
            
        Returns:
            (canonical_path, audit_log)
        """
        # Initialize audit
        audit = NormalizationAudit(
            doc_id=doc_id,
            raw_file="",
            canonical_file="",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # 1. Copy to raw (preserve original)
        raw_path = self._save_raw(doc_id, source_path, original_filename)
        audit.raw_file = str(raw_path.relative_to(self.base_path))
        audit.content_hash_raw = self._compute_hash(raw_path)
        
        # 2. Detect file type and load
        suffix = source_path.suffix.lower()
        
        if suffix == ".csv":
            df, encoding_used = self._load_csv_with_detection(raw_path, audit)
        elif suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(raw_path)
            audit.transforms_applied.append(TransformRule(
                rule="excel_load",
                details={"format": suffix}
            ))
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        audit.rows_before = len(df)
        
        # 3. Check if normalization needed
        if self._is_already_canonical(df, audit):
            # Just copy to canonical without changes
            canonical_path = self._save_canonical(doc_id, df, original_filename)
            audit.canonical_file = str(canonical_path.relative_to(self.base_path))
            audit.content_hash_canonical = self._compute_hash(canonical_path)
            audit.skipped = True
            audit.rows_after = len(df)
            self._save_audit(doc_id, audit)
            return canonical_path, audit
        
        # 4. Apply transformations
        df = self._clean_headers(df, audit)
        df = self._strip_quotes(df, audit)
        df = self._remove_empty_rows(df, audit)
        df = self._standardize_nulls(df, audit)
        
        audit.rows_after = len(df)
        audit.rows_dropped = audit.rows_before - audit.rows_after
        
        # 5. Save canonical
        canonical_path = self._save_canonical(doc_id, df, original_filename)
        audit.canonical_file = str(canonical_path.relative_to(self.base_path))
        audit.content_hash_canonical = self._compute_hash(canonical_path)
        
        # 6. Save audit log
        self._save_audit(doc_id, audit)
        
        logger.info(
            f"Normalized {original_filename}: "
            f"{audit.rows_before} → {audit.rows_after} rows, "
            f"{len(audit.transforms_applied)} transforms"
        )
        
        return canonical_path, audit
    
    def _save_raw(self, doc_id: str, source_path: Path, filename: str) -> Path:
        """Save original file to raw directory."""
        raw_path = self.raw_dir / f"{doc_id}_{filename}"
        
        # Copy file
        with open(source_path, "rb") as src:
            with open(raw_path, "wb") as dst:
                dst.write(src.read())
        
        return raw_path
    
    def _save_canonical(self, doc_id: str, df: pd.DataFrame, filename: str) -> Path:
        """Save normalized DataFrame to canonical directory."""
        # Always save as CSV for consistency
        base_name = Path(filename).stem
        canonical_path = self.canonical_dir / f"{doc_id}_{base_name}.csv"
        
        df.to_csv(
            canonical_path,
            index=False,
            encoding=self.CANONICAL_ENCODING,
            sep=self.CANONICAL_SEPARATOR
        )
        
        return canonical_path
    
    def _save_audit(self, doc_id: str, audit: NormalizationAudit):
        """Save audit log to JSON."""
        audit_path = self.audit_dir / f"{doc_id}_transform.json"
        
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _compute_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of file."""
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _load_csv_with_detection(
        self, 
        path: Path, 
        audit: NormalizationAudit
    ) -> tuple[pd.DataFrame, str]:
        """
        Load CSV with robust auto-detection.
        
        Detects:
        - Encoding (UTF-8, latin-1, etc.)
        - Separator (comma, semicolon, tab, pipe)
        - Quote character (" or ')
        - Escape sequences
        
        Falls back to tolerant mode with bad line skipping.
        """
        import csv
        
        # 1. Read raw bytes to detect encoding and format
        with open(path, "rb") as f:
            raw_bytes = f.read(8192)  # Sample first 8KB
        
        # 2. Detect encoding
        encoding = self._detect_encoding(raw_bytes)
        if encoding != "utf-8":
            audit.transforms_applied.append(TransformRule(
                rule="encoding",
                details={"from": encoding, "to": "utf-8"}
            ))
        
        # 3. Decode sample for format detection
        try:
            sample_text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            sample_text = raw_bytes.decode("latin-1")
            encoding = "latin-1"
        
        # 4. Auto-detect CSV dialect (separator, quotechar)
        detected = self._detect_csv_dialect(sample_text)
        
        if detected["separator"] != ",":
            audit.transforms_applied.append(TransformRule(
                rule="separator_normalize",
                details={"from": detected["separator"], "to": ","}
            ))
        
        if detected["quotechar"] != '"':
            audit.transforms_applied.append(TransformRule(
                rule="quotechar_normalize", 
                details={"from": detected["quotechar"], "to": '"'}
            ))
        
        # 5. Try loading with detected settings
        try:
            df = pd.read_csv(
                path,
                encoding=encoding,
                sep=detected["separator"],
                quotechar=detected["quotechar"],
                doublequote=True,
                escapechar=detected.get("escapechar"),
                on_bad_lines="warn"  # Log but don't fail
            )
            return df, encoding
            
        except Exception as first_error:
            logger.warning(f"First CSV parse attempt failed: {first_error}")
            
            # 6. Fallback: Skip bad lines with detailed logging
            bad_lines = []
            
            def bad_line_handler(bad_line):
                if len(bad_lines) < 20:  # Limit samples
                    bad_lines.append(str(bad_line)[:100])
                return None
            
            try:
                df = pd.read_csv(
                    path,
                    encoding=encoding,
                    sep=detected["separator"],
                    quotechar=detected["quotechar"],
                    on_bad_lines="skip",
                    engine="python"  # More tolerant
                )
                
                if bad_lines:
                    audit.transforms_applied.append(TransformRule(
                        rule="skip_bad_lines",
                        details={
                            "count": len(bad_lines),
                            "samples": bad_lines[:5]
                        }
                    ))
                    audit.sample_issues.extend([
                        {"issue": "bad_line", "sample": line} for line in bad_lines[:3]
                    ])
                
                return df, encoding
                
            except Exception as e:
                logger.error(f"CSV parse completely failed: {e}")
                raise ValueError(f"Could not parse CSV file: {e}")
    
    def _detect_encoding(self, raw_bytes: bytes) -> str:
        """Detect file encoding from raw bytes."""
        # Check for BOM
        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            return "utf-8-sig"
        if raw_bytes.startswith(b'\xff\xfe'):
            return "utf-16-le"
        if raw_bytes.startswith(b'\xfe\xff'):
            return "utf-16-be"
        
        # Try UTF-8 first
        try:
            raw_bytes.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass
        
        # Try common encodings
        for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
            try:
                raw_bytes.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        
        return "latin-1"  # Final fallback
    
    def _detect_csv_dialect(self, sample_text: str) -> dict:
        """
        Auto-detect CSV format from sample text.
        
        Returns:
            {separator, quotechar, escapechar, has_header}
        """
        import csv
        
        # Count potential separators in first few lines
        lines = sample_text.split("\n")[:10]
        first_line = lines[0] if lines else ""
        
        separators = {
            ",": first_line.count(","),
            ";": first_line.count(";"),
            "\t": first_line.count("\t"),
            "|": first_line.count("|"),
        }
        
        # Pick separator with most occurrences (and consistent across lines)
        best_sep = ","
        best_count = 0
        for sep, count in separators.items():
            if count > best_count:
                # Verify consistency in other lines
                if len(lines) > 1:
                    other_counts = [line.count(sep) for line in lines[1:5] if line.strip()]
                    if other_counts and abs(count - (sum(other_counts)/len(other_counts))) < 2:
                        best_sep = sep
                        best_count = count
                else:
                    best_sep = sep
                    best_count = count
        
        # Detect quote character
        double_quotes = sample_text.count('"')
        single_quotes = sample_text.count("'")
        
        # Look for patterns like "value" or 'value'
        double_pattern = sample_text.count(',"') + sample_text.count('",') + sample_text.count('"' + best_sep)
        single_pattern = sample_text.count(",'") + sample_text.count("',") + sample_text.count("'" + best_sep)
        
        if single_pattern > double_pattern and single_quotes > double_quotes:
            quotechar = "'"
        else:
            quotechar = '"'
        
        # Detect escape character (rare, usually None)
        escapechar = None
        if "\\" + quotechar in sample_text:
            escapechar = "\\"
        
        logger.debug(f"Detected CSV: sep={repr(best_sep)}, quote={repr(quotechar)}, escape={repr(escapechar)}")
        
        return {
            "separator": best_sep,
            "quotechar": quotechar,
            "escapechar": escapechar,
            "detected_columns": best_count + 1 if best_count > 0 else None
        }
    
    def _is_already_canonical(self, df: pd.DataFrame, audit: NormalizationAudit) -> bool:
        """Check if DataFrame is already in canonical format."""
        issues = []
        
        # Check headers
        for col in df.columns:
            if col != col.strip():
                issues.append(f"header_whitespace:{col}")
            if re.search(r'[^\w\s]', str(col)):
                pass  # Allow special chars in headers for now
        
        # Check for quoted values (sample first 100 rows)
        sample = df.head(100)
        for col in df.columns:
            if df[col].dtype == "object":
                vals = sample[col].dropna().head(10)
                for val in vals:
                    if isinstance(val, str) and (val.startswith("'") or val.startswith('"')):
                        issues.append(f"quoted_value:{col}")
                        break
        
        if not issues:
            audit.skip_reason = "File already in canonical format"
            return True
        
        return False
    
    def _clean_headers(self, df: pd.DataFrame, audit: NormalizationAudit) -> pd.DataFrame:
        """Clean column headers."""
        changes = {}
        new_columns = []
        
        for col in df.columns:
            new_col = col.strip()
            # Remove leading/trailing special chars but keep internal ones
            new_col = new_col.strip("_- ")
            
            if new_col != col:
                changes[col] = new_col
            
            new_columns.append(new_col)
        
        if changes:
            df.columns = new_columns
            audit.transforms_applied.append(TransformRule(
                rule="header_clean",
                details={"changes": changes}
            ))
        
        return df
    
    def _strip_quotes(self, df: pd.DataFrame, audit: NormalizationAudit) -> pd.DataFrame:
        """Strip surrounding quotes from string values."""
        affected_columns = []
        affected_rows = 0
        
        for col in df.columns:
            if df[col].dtype != "object":
                continue
            
            # Count affected values
            mask = df[col].apply(
                lambda x: isinstance(x, str) and (
                    (x.startswith("'") and x.endswith("'")) or
                    (x.startswith('"') and x.endswith('"'))
                )
            )
            
            col_affected = mask.sum()
            if col_affected > 0:
                affected_columns.append(col)
                affected_rows += col_affected
                
                # Apply strip
                df[col] = df[col].apply(
                    lambda x: x.strip("'\"") if isinstance(x, str) else x
                )
                
                # Sample issues
                if len(audit.sample_issues) < self.MAX_SAMPLE_ISSUES:
                    sample_vals = df.loc[mask.head(2).index, col].tolist()
                    for val in sample_vals[:2]:
                        audit.sample_issues.append({
                            "column": col,
                            "issue": "stripped_quotes",
                            "sample": str(val)[:50]
                        })
        
        if affected_columns:
            audit.transforms_applied.append(TransformRule(
                rule="quote_strip",
                details={
                    "columns": affected_columns,
                    "affected_rows": affected_rows
                }
            ))
        
        return df
    
    def _remove_empty_rows(self, df: pd.DataFrame, audit: NormalizationAudit) -> pd.DataFrame:
        """Remove completely empty rows."""
        original_len = len(df)
        df = df.dropna(how="all")
        removed = original_len - len(df)
        
        if removed > 0:
            audit.transforms_applied.append(TransformRule(
                rule="remove_empty_rows",
                details={"rows_removed": removed}
            ))
            audit.drop_reasons.append({
                "reason": "empty_row",
                "count": removed
            })
        
        return df
    
    def _standardize_nulls(self, df: pd.DataFrame, audit: NormalizationAudit) -> pd.DataFrame:
        """Standardize null representations."""
        null_values = ["", "null", "NULL", "None", "N/A", "n/a", "#N/A", "-"]
        affected = 0
        
        for col in df.columns:
            if df[col].dtype != "object":
                continue
            
            mask = df[col].isin(null_values)
            col_affected = mask.sum()
            if col_affected > 0:
                affected += col_affected
                df.loc[mask, col] = None
        
        if affected > 0:
            audit.transforms_applied.append(TransformRule(
                rule="standardize_nulls",
                details={
                    "patterns": null_values,
                    "affected_cells": affected
                }
            ))
        
        return df
    
    def get_canonical_path(self, doc_id: str) -> Optional[Path]:
        """Get the canonical file path for a document."""
        matches = list(self.canonical_dir.glob(f"{doc_id}_*"))
        return matches[0] if matches else None
    
    def get_audit(self, doc_id: str) -> Optional[dict]:
        """Get the audit log for a document."""
        audit_path = self.audit_dir / f"{doc_id}_transform.json"
        if audit_path.exists():
            with open(audit_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


# Singleton instance
_normalizer: Optional[FileNormalizer] = None

def get_file_normalizer() -> FileNormalizer:
    """Get the global FileNormalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = FileNormalizer()
    return _normalizer
