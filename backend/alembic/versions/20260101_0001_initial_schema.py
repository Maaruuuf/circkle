"""initial schema: users, auth tokens, media, posts, comments, reactions, follows

Revision ID: 0001
Revises:
Create Date: 2026-01-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("bio", sa.String(length=300), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("google_sub", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.CheckConstraint("username = lower(username)", name=op.f("ck_users_username_lowercase")),
        sa.CheckConstraint("role IN ('user', 'admin')", name=op.f("ck_users_role_valid")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        sa.UniqueConstraint("google_sub", name=op.f("uq_users_google_sub")),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False)

    op.create_table(
        "auth_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('email_verify', 'password_reset')", name=op.f("ck_auth_tokens_purpose_valid")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_tokens_token_hash")),
    )
    op.create_index(op.f("ix_auth_tokens_user_id"), "auth_tokens", ["user_id"], unique=False)

    op.create_table(
        "media",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_media_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media")),
        sa.UniqueConstraint("key", name=op.f("uq_media_key")),
    )
    op.create_index(op.f("ix_media_owner_id"), "media", ["owner_id"], unique=False)

    op.create_table(
        "posts",
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("media_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "media_id IS NOT NULL OR (content IS NOT NULL AND length(btrim(content)) > 0)",
            name=op.f("ck_posts_has_content_or_media"),
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_posts_author_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["media_id"], ["media.id"], name=op.f("fk_posts_media_id_media"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
    )
    op.create_index("ix_posts_author_id_created_at_id", "posts", ["author_id", "created_at", "id"], unique=False)
    op.create_index("ix_posts_created_at_id", "posts", ["created_at", "id"], unique=False)

    op.create_table(
        "comments",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_comments_author_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], name=op.f("fk_comments_post_id_posts"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(op.f("ix_comments_author_id"), "comments", ["author_id"], unique=False)
    op.create_index("ix_comments_post_id_created_at_id", "comments", ["post_id", "created_at", "id"], unique=False)

    op.create_table(
        "reactions",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "type IN ('like', 'love', 'haha', 'wow', 'sad')", name=op.f("ck_reactions_type_valid")
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], name=op.f("fk_reactions_post_id_posts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_reactions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("post_id", "user_id", name=op.f("pk_reactions")),
    )

    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Uuid(), nullable=False),
        sa.Column("followee_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("follower_id <> followee_id", name=op.f("ck_follows_no_self_follow")),
        sa.ForeignKeyConstraint(
            ["followee_id"], ["users.id"], name=op.f("fk_follows_followee_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["follower_id"], ["users.id"], name=op.f("fk_follows_follower_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("follower_id", "followee_id", name=op.f("pk_follows")),
    )
    op.create_index("ix_follows_followee_id_created_at", "follows", ["followee_id", "created_at"], unique=False)
    op.create_index("ix_follows_follower_id_created_at", "follows", ["follower_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("follows")
    op.drop_table("reactions")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("media")
    op.drop_table("auth_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
