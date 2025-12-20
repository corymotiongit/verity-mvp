raise RuntimeError(
    "LEGACY CODE IS FROZEN - This file has been moved to legacy_frozen/ and must not be imported. "
    "Use the new v2 API with tool-based architecture instead. See /src/verity/core/ for new implementation."
)

# The code below is preserved for reference only and will never execute
# ============================================================================

import logging
from typing import List, Dict, Any, Optional

from verity.core.gemini import generate_with_store

logger = logging.getLogger(__name__)

DOC_QA_SYSTEM_PROMPT = """You are DocQA, a specialized assistant for answering questions based ONLY on provided documents.
Rules:
1. Answer ONLY using the information from the File Search tool.
2. If the answer is not in the documents, say "No encontré información sobre eso en los documentos."
3. Do not invent information.
4. Keep your answer concise and direct.
"""

class DocQAAgent:
    """
    Agent responsible for Semantic Search over unstructured documents (PDFs, Text).
    Strictly wraps Gemini File Search.
    """
    
    async def answer(self, query: str, store_name: str, category_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate answer using File Search.
        """
        try:
            # Build prompts
            full_prompt = f"{DOC_QA_SYSTEM_PROMPT}\n\nUser Question: {query}"
            
            if category_filter:
                full_prompt += f"\n\nContext: Only search in documents of category '{category_filter}'."
            
            result = generate_with_store(
                prompt=full_prompt,
                store_name=store_name,
                metadata_filter={"category": category_filter} if category_filter else None
            )
            
            return {
                "answer": result.get("text", ""),
                "sources": result.get("sources", []),
                "grounded": result.get("grounded", False)
            }
            
        except Exception as e:
            logger.error(f"DocQA failed: {e}")
            raise
