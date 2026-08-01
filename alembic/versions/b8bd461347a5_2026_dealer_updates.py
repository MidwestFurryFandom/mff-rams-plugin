"""2026 Dealer updates

Revision ID: b8bd461347a5
Revises: c05aa8f9fd4c
Create Date: 2026-08-01 12:19:40.100947

"""


# revision identifiers, used by Alembic.
revision = 'b8bd461347a5'
down_revision = 'c05aa8f9fd4c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



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
    op.add_column('group', sa.Column('additional_website', sa.VARCHAR(), server_default=sa.text("''::character varying"), nullable=False))
    op.add_column('group', sa.Column('flexible_tables', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('suite_tables', sa.Integer(), server_default='0', nullable=False))
    op.drop_column('group', 'at_con_standby_text')
    op.drop_column('group', 'at_con_standby')


def downgrade():
    op.add_column('group', sa.Column('at_con_standby', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('group', sa.Column('at_con_standby_text', sa.VARCHAR(), server_default=sa.text("''::character varying"), autoincrement=False, nullable=False))
    op.drop_column('group', 'suite_tables')
    op.drop_column('group', 'flexible_tables')
    op.drop_column('group', 'additional_website')
