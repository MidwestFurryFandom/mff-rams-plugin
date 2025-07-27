"""Add dealer fields for 2025

Revision ID: 57e9f219b8db
Revises: 9bc0f579039c
Create Date: 2025-05-05 02:36:57.339240

"""


# revision identifiers, used by Alembic.
revision = '57e9f219b8db'
down_revision = '9bc0f579039c'
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
    op.add_column('group', sa.Column('adult_content', sa.Integer(), server_default='0', nullable=False))
    op.add_column('group', sa.Column('agreed_to_dealer_policies', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('agreed_to_ip_policy', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('art_show_intent', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('at_con_standby', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('at_con_standby_text', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('display_height', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('ip_concerns', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('ip_issues', sa.Integer(), server_default='0', nullable=False))
    op.add_column('group', sa.Column('mff_alumni', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('other_concerns', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('other_cons', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('shipping_boxes', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('social_media', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('socials_checked', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('table_photo_filename', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('table_photo_content_type', sa.Unicode(), server_default='', nullable=False))
    op.add_column('group', sa.Column('table_seen', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('group', sa.Column('vehicle_access', sa.Boolean(), server_default='False', nullable=False))


def downgrade():
    op.drop_column('group', 'vehicle_access')
    op.drop_column('group', 'table_seen')
    op.drop_column('group', 'table_photo_filename')
    op.drop_column('group', 'table_photo_content_type')
    op.drop_column('group', 'socials_checked')
    op.drop_column('group', 'social_media')
    op.drop_column('group', 'shipping_boxes')
    op.drop_column('group', 'other_cons')
    op.drop_column('group', 'other_concerns')
    op.drop_column('group', 'mff_alumni')
    op.drop_column('group', 'ip_issues')
    op.drop_column('group', 'ip_concerns')
    op.drop_column('group', 'display_height')
    op.drop_column('group', 'at_con_standby_text')
    op.drop_column('group', 'at_con_standby')
    op.drop_column('group', 'art_show_intent')
    op.drop_column('group', 'agreed_to_ip_policy')
    op.drop_column('group', 'agreed_to_dealer_policies')
    op.drop_column('group', 'adult_content')
    op.drop_constraint(op.f('fk_attendee_creator_id_attendee'), 'attendee', type_='foreignkey')
    op.create_foreign_key('fk_attendee_creator_id_attendee', 'attendee', 'attendee', ['creator_id'], ['id'])
