from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class AssistantAction:
    id: str
    label: str


@dataclass
class RecommendParams:
    rec_type: str = "general"       # general | album | artist | track
    genre_filter: Optional[str] = None
    similar_to: Optional[str] = None
    limit: int = 5
    custom_prompt: Optional[str] = None
    from_library_only: bool = False


@dataclass
class ShareResult:
    url: str
    id: str
    item_count: int
    found_name: str
    share_type: str
    used_flexible_search: bool = False


@dataclass
class AssistantResponse:
    text: str
    actions: list = field(default_factory=list)   # list[AssistantAction]
    recommendations: list = field(default_factory=list)  # list[Recommendation], for session state
    parse_mode: str = "html"
    success: bool = True

    @classmethod
    def error(cls, text: str) -> "AssistantResponse":
        return cls(text=text, success=False)
