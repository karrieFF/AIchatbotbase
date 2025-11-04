# migrations/versions/xxxx_create_messages_table.py
from alembic import op #alembic is a database migrations tool. It can help know the update information of the database
import sqlalchemy as sa #SQLAlchemy is the Python SQL toolkit that lets you work with the database using python code instead of SQL
from sqlalchemy.dialects import postgresql

revision = "xxxx"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("session_id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_messages_session", "messages", ["session_id"])
    op.create_index("idx_messages_user", "messages", ["user_id"])
    op.create_index("idx_messages_created_at", "messages", ["created_at"])

def downgrade():
    op.drop_table("messages")