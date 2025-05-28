"""create whatsapp mapping table

Revision ID: 001
Revises: 
Create Date: 2024-03-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'whatsappmapping',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('whatsapp_number', sa.String(), nullable=False),
        sa.Column('flexge_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('whatsappmapping') 