"""Change ton_balance from Float to Numeric(10,4)

Revision ID: 002
Revises: 001
Create Date: 2026-01-16 18:51:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade ton_balance from Float to Numeric(10, 4)
    """
    # Change column type from Float to Numeric(10, 4)
    # USING clause ensures safe conversion of existing data
    op.alter_column(
        'users',
        'ton_balance',
        type_=sa.Numeric(precision=10, scale=4),
        existing_type=sa.Float(),
        existing_nullable=True,
        postgresql_using='ton_balance::numeric(10,4)'
    )


def downgrade():
    """
    Downgrade ton_balance from Numeric(10, 4) back to Float
    """
    # Change column type back from Numeric to Float
    op.alter_column(
        'users',
        'ton_balance',
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=10, scale=4),
        existing_nullable=True,
        postgresql_using='ton_balance::double precision'
    )
