"""Add eligibility rule result table

Revision ID: 2a0f4e5d9b3c
Revises: 7b6619f3c1d2
Create Date: 2026-02-16 20:45:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2a0f4e5d9b3c"
down_revision = "7b6619f3c1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "eligibility_rule_result",
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("rationale", sa.String(length=1000), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["citizenship_application.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("eligibility_rule_result")
