"""Update ModelUsage: merge x_time and call_count into time_series_json with Beijing timezone

Revision ID: 8abcfd647a0a
Revises: e43c4c7bd8c2
Create Date: 2026-01-05 20:56:29.435320

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from datetime import timedelta


# revision identifiers, used by Alembic.
revision: str = '8abcfd647a0a'
down_revision: Union[str, Sequence[str], None] = 'e43c4c7bd8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new column as nullable first
    op.add_column('model_usage', sa.Column('time_series_json', sa.String(), nullable=True))

    # Migrate existing data from x_time_json to time_series_json
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id, x_time_json FROM model_usage"))

    for row in result:
        row_id, x_time_json = row
        if x_time_json:
            try:
                x_times = json.loads(x_time_json)
                # Create time series with Beijing timezone (UTC+8)
                time_series = []
                for time_str in x_times:
                    # Parse "2026-01-05 20:00" and add Beijing timezone (+08:00)
                    time_series.append({
                        "time": f"{time_str}+08:00",
                        "call_count": None
                    })
                connection.execute(
                    sa.text("UPDATE model_usage SET time_series_json = :ts WHERE id = :id"),
                    {"ts": json.dumps(time_series), "id": row_id}
                )
            except Exception:
                # If parsing fails, set empty JSON array
                connection.execute(
                    sa.text("UPDATE model_usage SET time_series_json = '[]' WHERE id = :id"),
                    {"id": row_id}
                )
        else:
            # Set empty JSON array if no existing data
            connection.execute(
                sa.text("UPDATE model_usage SET time_series_json = '[]' WHERE id = :id"),
                {"id": row_id}
            )

    # Now make the column non-nullable and drop the old one
    op.alter_column('model_usage', 'time_series_json', nullable=False)
    op.drop_column('model_usage', 'x_time_json')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back x_time_json column (nullable for migration)
    op.add_column('model_usage', sa.Column('x_time_json', sa.VARCHAR(), autoincrement=False, nullable=True))

    # Migrate data back (extract times from time_series_json)
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id, time_series_json FROM model_usage"))

    for row in result:
        row_id, ts_json = row
        if ts_json:
            try:
                time_series = json.loads(ts_json)
                # Extract just the times (remove timezone part for storage)
                x_times = [t["time"].split("+")[0] if "+" in str(t["time"]) else str(t["time"]) for t in time_series]
                connection.execute(
                    sa.text("UPDATE model_usage SET x_time_json = :xt WHERE id = :id"),
                    {"xt": json.dumps(x_times), "id": row_id}
                )
            except Exception:
                pass

    # Make x_time_json non-nullable and drop time_series_json
    op.alter_column('model_usage', 'x_time_json', nullable=False)
    op.drop_column('model_usage', 'time_series_json')
