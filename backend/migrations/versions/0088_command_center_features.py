"""Add tables for Major Incidents (War Room), Incident Timeline, Scheduled Reports, and Incidents menu.

Revision ID: 0088
Revises: 0087
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "major_incident",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="sev2"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("site", sa.String(120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("commander", sa.String(120), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(60), nullable=False, server_default="system"),
    )
    op.create_index("ix_major_incident_status", "major_incident", ["status"])

    op.create_table(
        "incident_update",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("major_incident.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="update"),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_index("ix_incident_update_inc", "incident_update", ["incident_id", "at"])

    op.create_table(
        "report_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(140), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="daily"),
        sa.Column("run_time", sa.String(10), nullable=False, server_default="08:00"),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("report_kind", sa.String(40), nullable=False, server_default="shift_summary"),
        sa.Column("fmt", sa.String(16), nullable=False, server_default="text"),
        sa.Column("site", sa.String(120), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="webhook"),
        sa.Column("recipients", sa.Text(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_status", sa.String(220), nullable=True),
    )

    conn = op.get_bind()
    # Register Major Incidents sub-menu under Personnel (alongside Handover)
    conn.execute(
        sa.text(
            """INSERT INTO module (key, label, parent, icon, sort, enabled, filters, note, why)
               VALUES ('incidents', 'Incidents', 'jadwal', 'alert', 62, true, CAST(:f AS jsonb),
                       'Major incident war room and cross-shift timeline.', '')
               ON CONFLICT (key) DO NOTHING"""
        ),
        {"f": '{"p":0,"s":0,"l":1,"c":0}'},
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM module WHERE key = 'incidents'"))
    op.drop_table("report_schedule")
    op.drop_index("ix_incident_update_inc", table_name="incident_update")
    op.drop_table("incident_update")
    op.drop_index("ix_major_incident_status", table_name="major_incident")
    op.drop_table("major_incident")
