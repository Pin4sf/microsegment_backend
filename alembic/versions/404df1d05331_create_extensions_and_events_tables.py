"""create_extensions_and_events_tables

Revision ID: 404df1d05331
Revises: de0a04cd2e5f
Create Date: 2025-05-20 18:09:11.483174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '404df1d05331'
down_revision: Union[str, None] = 'de0a04cd2e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('extensions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('shopify_extension_id', sa.String(), nullable=True),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='inactive'),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id'),
        sa.UniqueConstraint('shopify_extension_id')
    )
    op.create_index(op.f('ix_extensions_account_id'), 'extensions', ['account_id'], unique=True)
    op.create_index(op.f('ix_extensions_shop_id'), 'extensions', ['shop_id'], unique=False)
    op.create_index(op.f('ix_extensions_shopify_extension_id'), 'extensions', ['shopify_extension_id'], unique=True)

    op.create_table('events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('event_name', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['extensions.account_id'], ),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_account_id'), 'events', ['account_id'], unique=False)
    op.create_index(op.f('ix_events_event_name'), 'events', ['event_name'], unique=False)
    op.create_index(op.f('ix_events_received_at'), 'events', ['received_at'], unique=False)
    op.create_index(op.f('ix_events_shop_id'), 'events', ['shop_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_events_shop_id'), table_name='events')
    op.drop_index(op.f('ix_events_received_at'), table_name='events')
    op.drop_index(op.f('ix_events_event_name'), table_name='events')
    op.drop_index(op.f('ix_events_account_id'), table_name='events')
    op.drop_table('events')

    op.drop_index(op.f('ix_extensions_shopify_extension_id'), table_name='extensions')
    op.drop_index(op.f('ix_extensions_shop_id'), table_name='extensions')
    op.drop_index(op.f('ix_extensions_account_id'), table_name='extensions')
    op.drop_table('extensions')
