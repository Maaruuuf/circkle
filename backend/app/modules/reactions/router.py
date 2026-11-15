import uuid

from fastapi import APIRouter, Depends

from app.core.rate_limit import RateLimit
from app.db.session import DbSession
from app.modules.auth.dependencies import CurrentUser, OptionalUser
from app.modules.reactions.schemas import ReactionSummary, SetReactionRequest
from app.modules.reactions.service import ReactionService

# Mounted under /posts by the posts router: /posts/{post_id}/reaction
router = APIRouter(tags=["reactions"])


@router.get("/{post_id}/reactions", response_model=ReactionSummary)
async def read_reactions(
    post_id: uuid.UUID, viewer: OptionalUser, session: DbSession
) -> ReactionSummary:
    return await ReactionService(session).summary(post_id, viewer)


@router.put(
    "/{post_id}/reaction",
    response_model=ReactionSummary,
    dependencies=[Depends(RateLimit("reaction", 120, 60, per="user"))],
)
async def set_reaction(
    post_id: uuid.UUID,
    payload: SetReactionRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> ReactionSummary:
    """Add your reaction, or change it if you already reacted."""
    return await ReactionService(session).set_reaction(post_id, current_user, payload.type.value)


@router.delete("/{post_id}/reaction", response_model=ReactionSummary)
async def remove_reaction(
    post_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> ReactionSummary:
    return await ReactionService(session).remove_reaction(post_id, current_user)
