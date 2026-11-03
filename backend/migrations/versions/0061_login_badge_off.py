"""The login page shows one product name (TERA): the ITOC Portal badge is switched off.

Revision ID: 0061
Revises: 0060
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb), label = 'Optional badge next to the organisation line on the login page (empty = none)' WHERE key = 'ui.login_badge' AND value = CAST(:o AS jsonb)"),
                          {"v": json.dumps(""), "o": json.dumps("ITOC Portal")})


def downgrade():
    pass
