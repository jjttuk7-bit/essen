"""Add immutable render configuration history.

Revision ID: 0002_render_config_history
Revises: 0001_initial_schema
"""

from collections import defaultdict
from collections.abc import Sequence
import hashlib

from alembic import op
import sqlalchemy as sa

revision: str = "0002_render_config_history"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("rendered_outputs")}
    if "audience" not in columns:
        op.add_column("rendered_outputs", sa.Column("audience", sa.String(length=128), nullable=True))
    if "max_words" not in columns:
        op.add_column("rendered_outputs", sa.Column("max_words", sa.Integer(), nullable=True))
    if "render_config_hash" not in columns:
        op.add_column("rendered_outputs", sa.Column("render_config_hash", sa.String(length=64), nullable=False, server_default="legacy"))

    rows = bind.execute(sa.text("SELECT id, analysis_run_id, output_type FROM rendered_outputs ORDER BY created_at, id")).mappings()
    versions: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        key = (row["analysis_run_id"], row["output_type"])
        versions[key] += 1
        bind.execute(sa.text("UPDATE rendered_outputs SET render_config_hash = :hash, version = :version WHERE id = :id"), {"hash": hashlib.sha256(f"legacy:{row['id']}".encode()).hexdigest(), "version": versions[key], "id": row["id"]})

    unique_names = {constraint["name"] for constraint in inspector.get_unique_constraints("rendered_outputs")}
    missing = []
    if "uq_outputs_render_config" not in unique_names:
        missing.append(("uq_outputs_render_config", ["analysis_run_id", "output_type", "render_config_hash"]))
    if "uq_outputs_version" not in unique_names:
        missing.append(("uq_outputs_version", ["analysis_run_id", "output_type", "version"]))
    if missing:
        with op.batch_alter_table("rendered_outputs") as batch:
            for name, fields in missing:
                batch.create_unique_constraint(name, fields)


def downgrade() -> None:
    with op.batch_alter_table("rendered_outputs") as batch:
        batch.drop_constraint("uq_outputs_version", type_="unique")
        batch.drop_constraint("uq_outputs_render_config", type_="unique")
        batch.drop_column("render_config_hash")
        batch.drop_column("max_words")
        batch.drop_column("audience")
