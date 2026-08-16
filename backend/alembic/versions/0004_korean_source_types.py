"""Accept Korean word-processor documents as source types.

Revision ID: 0004_korean_source_types
Revises: 0003_docx_source_type
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_korean_source_types"
down_revision: str | None = "0003_docx_source_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_NAME = "sourcetype"
VALUES = ("hwp", "hwpx")


def upgrade() -> None:
    # SQLite stores the enum as VARCHAR, so only Postgres needs the type altered.
    if op.get_bind().dialect.name != "postgresql":
        return
    for value in VALUES:
        op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Postgres cannot drop an enum value while rows may reference it.

    Reversing would mean rebuilding the type and rewriting every column that uses it,
    which risks more than the values cost to leave in place.
    """
