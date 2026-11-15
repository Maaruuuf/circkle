import uuid

from pydantic import BaseModel, ConfigDict

from app.modules.reactions.models import ReactionType


class SetReactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ReactionType


class ReactionSummary(BaseModel):
    post_id: uuid.UUID
    reaction_count: int
    my_reaction: str | None
    # Breakdown, e.g. {"like": 3, "love": 1}
    by_type: dict[str, int]
