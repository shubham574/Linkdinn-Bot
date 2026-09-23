from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/dev.db"

    gemini_api_key: str = ""
    gemini_model: str = ""
    tavily_api_key: str = ""

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_api_version: str = ""

    # Safe defaults: nothing is published unless BOTH are flipped.
    dry_run: bool = True
    auto_publish: bool = False
    max_revisions: int = 3

    rater_approval_threshold: int = 85
    rater_min_personal_voice: int = 50
    rater_min_specificity: int = 60
    rater_min_factual_confidence: int = 80
    rater_max_generic_ai_language: int = 40
    rater_max_fabrication_prob: float = 0.2

    research_categories: str = (
        "AI,Generative AI,LLMs,AI agents,Agentic workflows,Web development,React,"
        "Next.js,Node.js,Backend,APIs,Automation,LangGraph,LangChain,Developer tools,"
        "Cloud,Open source"
    )

    schedule_time: str = "08:00"
    timezone: str = "Asia/Kolkata"

    @property
    def categories(self) -> list[str]:
        return [c.strip() for c in self.research_categories.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
