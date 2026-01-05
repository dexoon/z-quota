"""Update created_at columns to TIMESTAMP WITH TIME ZONE

Revision ID: 2267c9dcb21c
Revises: e984eb1810a9
Create Date: 2026-01-05 21:17:32.154259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2267c9dcb21c'
down_revision: Union[str, Sequence[str], None] = 'e984eb1810a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update created_at columns to TIMESTAMP WITH TIME ZONE
    op.alter_column(
        'model_usage',
        'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
    )
    op.alter_column(
        'model_usage_time_series',
        'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
    )
    op.alter_column(
        'tool_usage',
        'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
    )
    op.alter_column(
        'quota_limit',
        'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert created_at columns to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column(
        'model_usage',
        'created_at',
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
    )
    op.alter_column(
        'model_usage_time_series',
        'created_at',
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
    )
    op.alter_column(
        'tool_usage',
        'created_at',
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
    )
    op.alter_column(
        'quota_limit',
        'created_at',
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
    )
