import json
from typing import Any
from google import genai
from google.genai import types

from app.agents.base import PostRater, PostRating, TopicSelection, TopicSelector
from app.config import Settings


class LayaTopicSelector:
    """Fallback Laya topic selector using Gemini due to install constraints."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"
        
    def select(self, candidates: list[dict[str, Any]], previous_topics: list[str]) -> TopicSelection:
        valid = [c for c in candidates if c.get("title") not in previous_topics]
        if not valid:
            return TopicSelection(selected=None, rejected=candidates)
            
        prompt = f"Select the best topic from these candidates: {valid}\nReturn a JSON object with 'selected_index' (integer)."
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={"type": "OBJECT", "properties": {"selected_index": {"type": "INTEGER"}}}
            )
        )
        try:
            data = json.loads(resp.text)
            idx = data.get("selected_index", 0)
            if idx >= len(valid): idx = 0
            selected = valid.pop(idx)
            return TopicSelection(selected=selected, rejected=valid)
        except Exception:
            return TopicSelection(selected=valid[0], rejected=valid[1:])


class LayaPostRater:
    """Fallback Laya post rater using Gemini due to install constraints."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"
        
    def rate(self, post: str, state: dict[str, Any]) -> PostRating:
        prompt = f"Rate this post on various metrics from 0-100. Return JSON matching the schema.\n\nPost:\n{post}"
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "human_naturalness": {"type": "INTEGER"},
                        "generic_ai_language": {"type": "INTEGER"},
                        "personal_voice": {"type": "INTEGER"},
                        "specificity": {"type": "INTEGER"},
                        "originality": {"type": "INTEGER"},
                        "usefulness": {"type": "INTEGER"},
                        "readability": {"type": "INTEGER"},
                        "factual_confidence": {"type": "INTEGER"},
                        "fabricated_personal_claim_prob": {"type": "NUMBER"},
                        "problems": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "rewrite_instructions": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": [
                        "human_naturalness", "generic_ai_language", "personal_voice", "specificity", 
                        "originality", "usefulness", "readability", "factual_confidence", 
                        "fabricated_personal_claim_prob", "problems", "rewrite_instructions"
                    ]
                }
            )
        )
        data = json.loads(resp.text)
        return PostRating(**data)
