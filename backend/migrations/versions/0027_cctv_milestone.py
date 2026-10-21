"""Milestone XProtect (CCTV): inventaris hardware (NVR/interconnect) dan kamera hasil tarikan RESTful API.

Revision ID: 0027
Revises: 0026
"""
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS cctv_hardware (
        id varchar(40) PRIMARY KEY, name varchar(200) NOT NULL, address varchar(300), host varchar(120), model varchar(80), enabled boolean NOT NULL DEFAULT true,
        recorder varchar(120), cameras integer NOT NULL DEFAULT 0, cameras_enabled integer NOT NULL DEFAULT 0, modified_at timestamp, fetched_at timestamp NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE IF NOT EXISTS cctv_camera (
        id varchar(40) PRIMARY KEY, name varchar(300) NOT NULL, location varchar(160), ip varchar(45), channel integer, hardware_id varchar(40), hardware varchar(200),
        enabled boolean NOT NULL DEFAULT true, recording boolean NOT NULL DEFAULT false, fps varchar(10), modified_at timestamp, fetched_at timestamp NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cctv_camera_hw ON cctv_camera (hardware_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cctv_camera_ip ON cctv_camera (ip)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS cctv_camera")
    op.execute("DROP TABLE IF EXISTS cctv_hardware")
