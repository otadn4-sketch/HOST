"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    from app.models import entities  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.db import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
