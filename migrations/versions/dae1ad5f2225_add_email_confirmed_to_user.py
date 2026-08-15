"""add email_confirmed to user

Revision ID: dae1ad5f2225
Revises: 75659bc20840
Create Date: 2026-08-14 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dae1ad5f2225'
down_revision = '75659bc20840'
branch_labels = None
depends_on = None


def upgrade():
    # server_default backfills existing rows (grandfathered in as confirmed).
    # Left in place afterward: harmless, since every INSERT from the ORM
    # passes the column explicitly via the model's Python-side default.
    op.add_column('user', sa.Column('email_confirmed', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column('user', 'email_confirmed')
