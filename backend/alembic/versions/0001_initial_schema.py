"""Create the auditable document analysis schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

from app.models import analysis, document  # noqa: F401
from app.models.base import Base


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())