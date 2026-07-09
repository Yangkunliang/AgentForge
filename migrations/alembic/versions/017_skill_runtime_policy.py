"""Add skill runtime manifest and permission fields

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("manifest_hash", sa.String(64), nullable=True))
    op.add_column("skills", sa.Column("permissions", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("skills", sa.Column("runtime_spec", sa.JSON(), nullable=True, server_default="{}"))
    op.add_column("skills", sa.Column("audit_level", sa.String(20), nullable=False, server_default="standard"))
    op.create_index("ix_skills_manifest_hash", "skills", ["manifest_hash"])

    op.add_column("skill_installs", sa.Column("manifest_hash", sa.String(64), nullable=True))
    op.add_column("skill_installs", sa.Column("permissions", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("skill_installs", sa.Column("risk_level", sa.String(20), nullable=True))
    op.add_column("skill_installs", sa.Column("preview", sa.JSON(), nullable=True, server_default="{}"))
    op.create_index("ix_skill_installs_manifest_hash", "skill_installs", ["manifest_hash"])


def downgrade() -> None:
    op.drop_index("ix_skill_installs_manifest_hash", table_name="skill_installs")
    op.drop_column("skill_installs", "preview")
    op.drop_column("skill_installs", "risk_level")
    op.drop_column("skill_installs", "permissions")
    op.drop_column("skill_installs", "manifest_hash")

    op.drop_index("ix_skills_manifest_hash", table_name="skills")
    op.drop_column("skills", "audit_level")
    op.drop_column("skills", "runtime_spec")
    op.drop_column("skills", "permissions")
    op.drop_column("skills", "manifest_hash")
