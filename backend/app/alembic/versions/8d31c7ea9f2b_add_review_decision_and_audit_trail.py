"""Add review decision fields and audit trail table

Revision ID: 8d31c7ea9f2b
Revises: 2a0f4e5d9b3c
Create Date: 2026-02-16 21:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8d31c7ea9f2b"
down_revision = "2a0f4e5d9b3c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "citizenship_application",
        sa.Column("final_decision", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "citizenship_application",
        sa.Column("final_decision_reason", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "citizenship_application",
        sa.Column("final_decision_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "citizenship_application",
        sa.Column("final_decision_by_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_citizenship_application_final_decision_by_id_user",
        "citizenship_application",
        "user",
        ["final_decision_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "application_audit_event",
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["citizenship_application.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("application_audit_event")

    op.drop_constraint(
        "fk_citizenship_application_final_decision_by_id_user",
        "citizenship_application",
        type_="foreignkey",
    )
    op.drop_column("citizenship_application", "final_decision_by_id")
    op.drop_column("citizenship_application", "final_decision_at")
    op.drop_column("citizenship_application", "final_decision_reason")
    op.drop_column("citizenship_application", "final_decision")
