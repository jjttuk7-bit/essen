"""Accept Word documents as a source type.

Revision ID: 0003_docx_source_type
Revises: 0002_render_config_history
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_docx_source_type"
down_revision: str | None = "0002_render_config_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_NAME = "sourcetype"
VALUE = "docx"


def upgrade() -> None:
    # SQLite stores the enum as VARCHAR, so only Postgres needs the type altered.
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{VALUE}'")


def downgrade() -> None:
    """Postgres cannot drop an enum value while rows may reference it.

    Reversing would mean rebuilding the type and rewriting every column that uses it,
    which risks more than the value costs to leave in place.
    """
