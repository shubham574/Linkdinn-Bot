import json
from typing import Any

from google import genai
from google.genai import types
from tavily import TavilyClient

from app.agents.base import FactCheckResult, ResearchPackage, Researcher, Writer, Rewriter, FactChecker
from app.config import Settings


class GeminiResearcher:
    def __init__(self, settings: Settings):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"
        self.categories = settings.categories

    def discover(self, target_date: str, previous_topics: list[str]) -> list[dict[str, Any]]:
        topics = []
        if self.tavily:
            # Query Tavily for latest AI/Tech news
            try:
                response = self.tavily.search(query=f"Latest developments in AI and tech {target_date}", search_depth="basic")
                for res in response.get("results", []):
                    topics.append({
                        "title": res["title"],
                        "url": res["url"],
                        "snippet": res["content"]
                    })
            except Exception as e:
                print(f"Tavily search failed: {e}")
        
        # Fallback to Gemini if Tavily fails or is missing
        if not topics:
            prompt = (
                f"Suggest 5 trending topics for a LinkedIn post on {target_date} in tech/AI. "
                f"Exclude these previous topics: {previous_topics}"
            )
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "snippet": {"type": "STRING"}
                            }
                        }
                    }
                )
            )
            topics = json.loads(resp.text)
        return topics
        
    def deep_research(self, topic: dict[str, Any]) -> ResearchPackage:
        prompt = (
            f"Research this topic and provide a structured package for a LinkedIn post:\n"
            f"Title: {topic.get('title')}\n"
            f"Context: {topic.get('snippet')}"
        )
        
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "topic": {"type": "STRING"},
                        "why_relevant": {"type": "STRING"},
                        "summary": {"type": "STRING"},
                        "facts": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "developer_implications": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "possible_angles": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["topic", "why_relevant", "summary", "facts", "developer_implications", "possible_angles"]
                }
            )
        )
        data = json.loads(resp.text)
        data["sources"] = []
        if "url" in topic:
            data["sources"].append({"title": topic.get("title"), "url": topic.get("url")})
        return ResearchPackage(**data)


class GeminiWriter:
    def __init__(self, settings: Settings):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"

    def write(self, state: dict[str, Any]) -> str:
        topic = state.get("selected_topic", {}).get("title", "")
        summary = state.get("research_summary", "")
        facts = state.get("research_results", [{}])[0].get("facts", [])
        previous_posts = state.get("relevant_previous_posts", [])
        
        prompt = (
            f"Write a professional LinkedIn post about this topic: {topic}\n\n"
            f"Summary: {summary}\n"
            f"Facts: {facts}\n\n"
        )
        
        if previous_posts:
            prompt += f"Avoid repeating content from these previous posts:\n{previous_posts}\n\n"
            
        prompt += "Make it engaging, use a professional tone, and include actionable insights."
        
        resp = self.client.models.generate_content(model=self.model, contents=prompt)
        return resp.text


class GeminiRewriter:
    def __init__(self, settings: Settings):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"

    def rewrite(self, state: dict[str, Any]) -> str:
        current = state.get("revised_post") or state.get("draft_post") or ""
        feedback = state.get("review_result", {}).get("rewrite_instructions", [])
        prompt = (
            f"Rewrite this LinkedIn post based on the following feedback.\n\n"
            f"Current Post:\n{current}\n\n"
            f"Feedback:\n{feedback}\n\n"
            "Make sure to incorporate all feedback and improve the post accordingly."
        )
        resp = self.client.models.generate_content(model=self.model, contents=prompt)
        return resp.text


class GeminiFactChecker:
    def __init__(self, settings: Settings):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-2.5-flash"

    def check(self, post: str, sources: list[dict[str, Any]], state: dict[str, Any]) -> FactCheckResult:
        prompt = (
            f"Fact check this post against the given sources. Be very lenient. As long as there are no blatant "
            f"contradictions or severely harmful hallucinations, set 'passed' to true. Return JSON.\n\n"
            f"Post:\n{post}\n\n"
            f"Sources:\n{sources}"
        )
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "passed": {"type": "BOOLEAN"},
                        "issues": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "verified_claims": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "unsupported_claims": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["passed", "issues", "verified_claims", "unsupported_claims"]
                }
            )
        )
        data = json.loads(resp.text)
        return FactCheckResult(**data)
