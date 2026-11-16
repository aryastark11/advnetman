import os
import glob
from typing import List, Dict, Any

RUNBOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runbooks")

def get_matching_runbooks(query_text: str) -> List[Dict[str, str]]:
    """Retrieve runbook excerpts matching incident category, device, or symptoms."""
    if not os.path.exists(RUNBOOKS_DIR):
        return []

    tokens = [t.lower() for t in query_text.replace("-", " ").replace("_", " ").split() if len(t) > 2]
    matched_runbooks = []

    for file_path in glob.glob(os.path.join(RUNBOOKS_DIR, "*.md")):
        fname = os.path.basename(file_path).lower()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Score relevance based on keyword match in filename or content
            score = 0
            for t in tokens:
                if t in fname:
                    score += 5
                if t in content.lower():
                    score += 1

            if score > 0:
                matched_runbooks.append({
                    "title": os.path.basename(file_path),
                    "score": score,
                    "content": content[:1500]
                })
        except Exception:
            continue

    matched_runbooks.sort(key=lambda x: x["score"], reverse=True)
    return matched_runbooks[:2]
