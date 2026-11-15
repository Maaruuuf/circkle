"""Import every model here so SQLAlchemy relationships resolve and Alembic sees them."""

from app.modules.auth.models import AuthToken, RefreshToken  # noqa: F401
from app.modules.comments.models import Comment  # noqa: F401
from app.modules.media.models import Media  # noqa: F401
from app.modules.posts.models import Post  # noqa: F401
from app.modules.reactions.models import Reaction  # noqa: F401
from app.modules.users.models import Follow, User  # noqa: F401
