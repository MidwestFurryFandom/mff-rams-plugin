"""Add tax number column for marketplace apps

Revision ID: f08f4606351c
Revises: 0f7426266803
Create Date: 2019-08-27 23:57:55.936896

"""


# revision identifiers, used by Alembic.
revision = 'f08f4606351c'
down_revision = '0f7426266803'
branch_labels = None
depends_on = '9e721eb0b45c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


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
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    if 'artist_marketplace_application' not in tables:
        op.add_column('marketplace_application', sa.Column('tax_number', sa.Unicode(), server_default='', nullable=False))


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    if 'artist_marketplace_application' not in tables:
        op.drop_column('marketplace_application', 'tax_number')
