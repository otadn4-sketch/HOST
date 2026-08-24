"""manual logging and phase tables

Revision ID: 002_manual_logging
Revises: 001_initial
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa

revision = "002_manual_logging"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    from app.models import entities  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    op.drop_table("faran_sync_records")
    op.drop_table("document_scrub_jobs")
    op.drop_table("share_links")
    op.drop_table("meeting_logs")
    op.drop_table("interaction_transactions")
    op.drop_table("external_recipients")
