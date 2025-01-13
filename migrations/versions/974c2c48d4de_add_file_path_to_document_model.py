"""Add file_path to Document model

Revision ID: 974c2c48d4de
Revises: f2ad1fb7dd31
Create Date: 2024-03-19 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '974c2c48d4de'
down_revision = 'f2ad1fb7dd31'
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary nullable column
    op.add_column('document', sa.Column('file_path', sa.String(255), nullable=True))
    
    # Create a reference to the document table
    document_table = table('document',
        column('id', sa.Integer),
        column('filename', sa.String),
        column('file_path', sa.String)
    )
    
    # Update existing records to set file_path based on filename
    op.execute(
        document_table.update().values(
            file_path=document_table.c.filename
        )
    )
    
    # Make the column non-nullable
    op.alter_column('document', 'file_path',
        existing_type=sa.String(255),
        nullable=False
    )


def downgrade():
    op.drop_column('document', 'file_path')
