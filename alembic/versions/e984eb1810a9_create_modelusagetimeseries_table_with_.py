"""Create ModelUsageTimeSeries table with FK, drop time_series_json

Revision ID: e984eb1810a9
Revises: 8abcfd647a0a
Create Date: 2026-01-05 21:03:23.505298

"""
from typing import Sequence, Union
import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


# revision identifiers, used by Alembic.
revision: str = 'e984eb1810a9'
down_revision: Union[str, Sequence[str], None] = '8abcfd647a0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get database URL from environment
    import os
    database_url = os.getenv("DATABASE_URL", "postgresql://ilya:7254885@localhost:5432/zquota")
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "postgresql://")

    # Create the new table
    op.create_table('model_usage_time_series',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('model_usage_id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('call_count', sa.Integer(), nullable=True),
    sa.Column('tokens_usage', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['model_usage_id'], ['model_usage.id'], name='fk_model_usage_time_series_model_usage'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create index on foreign key for better query performance
    op.create_index('ix_model_usage_time_series_model_usage_id', 'model_usage_time_series', ['model_usage_id'])
    op.create_index('ix_model_usage_time_series_time', 'model_usage_time_series', ['time'])

    # Migrate existing data from time_series_json to the new table
    connection = op.get_bind()
    Session = sessionmaker(bind=connection)
    session = Session()

    try:
        # Get all model_usage records with time_series_json
        result = connection.execute(sa.text("SELECT id, time_series_json FROM model_usage WHERE time_series_json IS NOT NULL"))

        for row in result:
            row_id, ts_json = row
            if ts_json:
                try:
                    time_series = json.loads(ts_json)
                    for point in time_series:
                        # Parse the time from ISO format
                        time_str = point.get("time", "")
                        if time_str:
                            # Convert ISO string to datetime
                            if "T" in time_str:
                                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                            else:
                                dt = datetime.fromisoformat(time_str)

                            connection.execute(
                                sa.text("""
                                    INSERT INTO model_usage_time_series (model_usage_id, time, call_count, tokens_usage, created_at)
                                    VALUES (:model_usage_id, :time, :call_count, :tokens_usage, NOW())
                                """),
                                {
                                    "model_usage_id": row_id,
                                    "time": dt,
                                    "call_count": point.get("call_count"),
                                    "tokens_usage": point.get("tokens_usage"),
                                }
                            )
                except Exception as e:
                    print(f"Warning: Failed to migrate time_series_json for row {row_id}: {e}")

        session.commit()
    finally:
        session.close()

    # Now drop the old column
    op.drop_column('model_usage', 'time_series_json')


def downgrade() -> None:
    """Downgrade schema."""
    import os
    database_url = os.getenv("DATABASE_URL", "postgresql://ilya:7254885@localhost:5432/zquota")
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "postgresql://")

    # Add back the old column (nullable first)
    op.add_column('model_usage', sa.Column('time_series_json', sa.VARCHAR(), autoincrement=False, nullable=True))

    # Migrate data back from model_usage_time_series to time_series_json
    connection = op.get_bind()
    Session = sessionmaker(bind=connection)
    session = Session()

    try:
        # Group by model_usage_id and build JSON arrays
        result = connection.execute(sa.text("""
            SELECT model_usage_id
            FROM model_usage_time_series
            GROUP BY model_usage_id
        """))

        for (model_usage_id,) in result:
            # Get all time series for this model_usage
            series_result = connection.execute(sa.text("""
                SELECT time, call_count, tokens_usage
                FROM model_usage_time_series
                WHERE model_usage_id = :mu_id
                ORDER BY time
            """), {"mu_id": model_usage_id})

            time_series = []
            for row in series_result:
                time, call_count, tokens_usage = row
                time_series.append({
                    "time": time.isoformat(),
                    "call_count": call_count,
                    "tokens_usage": tokens_usage,
                })

            connection.execute(
                sa.text("UPDATE model_usage SET time_series_json = :ts WHERE id = :id"),
                {"ts": json.dumps(time_series), "id": model_usage_id}
            )

        session.commit()
    finally:
        session.close()

    # Make the column non-nullable
    op.alter_column('model_usage', 'time_series_json', nullable=False)

    # Drop the new table
    op.drop_index('ix_model_usage_time_series_time')
    op.drop_index('ix_model_usage_time_series_model_usage_id')
    op.drop_table('model_usage_time_series')
