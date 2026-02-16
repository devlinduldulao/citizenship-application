"""Add citizenship application tables

Revision ID: 7b6619f3c1d2
Revises: fe56fa70289e
Create Date: 2026-02-16 20:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b6619f3c1d2"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "citizenship_application",
        sa.Column("applicant_full_name", sa.String(length=255), nullable=False),
        sa.Column("applicant_nationality", sa.String(length=128), nullable=False),
        sa.Column("applicant_birth_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recommendation_summary", sa.String(length=2000), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "application_document",
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ocr_text", sa.String(), nullable=True),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("processing_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["citizenship_application.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("application_document")
    op.drop_table("citizenship_application")
