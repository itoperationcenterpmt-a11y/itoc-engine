from alembic import context
from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401  (mendaftarkan tabel)

target_metadata = Base.metadata


def run():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    context.configure(url=settings().database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run()
