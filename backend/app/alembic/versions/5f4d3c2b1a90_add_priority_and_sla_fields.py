"""Add priority and SLA fields to citizenship application

Revision ID: 5f4d3c2b1a90
Revises: 8d31c7ea9f2b
Create Date: 2026-02-16 22:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5f4d3c2b1a90"
down_revision = "8d31c7ea9f2b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "citizenship_application",
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "citizenship_application",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("citizenship_application", "sla_due_at")
    op.drop_column("citizenship_application", "priority_score")
