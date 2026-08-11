"""Update social media field

Revision ID: c05aa8f9fd4c
Revises: 3bf0accd7df9
Create Date: 2026-07-29 21:18:04.085791

"""


# revision identifiers, used by Alembic.
revision = 'c05aa8f9fd4c'
down_revision = '3bf0accd7df9'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


try:
    is_sqlite = op.get_context().dialect.name == 'sqlite'
except Exception:
    is_sqlite = False

if is_sqlite:
    op.get_context().connection.execute('PRAGMA foreign_keys=ON;')
    utcnow_server_default = "(datetime('now', 'utc'))"
else:
    utcnow_server_default = "timezone('utc', current_timestamp)"

def sqlite_column_reflect_listener(inspector, table, column_info):
    """Adds parenthesis around SQLite datetime defaults for utcnow."""
    if column_info['default'] == "datetime('now', 'utc')":
        column_info['default'] = utcnow_server_default

sqlite_reflect_kwargs = {
    'listeners': [('column_reflect', sqlite_column_reflect_listener)]
}

# ===========================================================================
# HOWTO: Handle alter statements in SQLite
#
# def upgrade():
#     if is_sqlite:
#         with op.batch_alter_table('table_name', reflect_kwargs=sqlite_reflect_kwargs) as batch_op:
#             batch_op.alter_column('column_name', type_=sa.Unicode(), server_default='', nullable=False)
#     else:
#         op.alter_column('table_name', 'column_name', type_=sa.Unicode(), server_default='', nullable=False)
#
# ===========================================================================


def upgrade():
    op.drop_column('group', 'social_media')
    op.add_column('group', sa.Column('social_media', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))
    op.drop_column('group', 'table_photo_content_type')
    op.drop_column('group', 'table_photo_filename')


def downgrade():
    op.add_column('group', sa.Column('table_photo_filename', sa.VARCHAR(), server_default=sa.text("''::character varying"), autoincrement=False, nullable=False))
    op.add_column('group', sa.Column('table_photo_content_type', sa.VARCHAR(), server_default=sa.text("''::character varying"), autoincrement=False, nullable=False))
    op.drop_column('group', 'social_media')
    op.add_column('group', sa.Column('social_media', sa.VARCHAR(), server_default=sa.text("''::character varying"), autoincrement=False, nullable=False))
