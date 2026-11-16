"""Sign-in emails are stored in lower case

Owner@x.com and owner@x.com were two different accounts. Existing emails
are lower-cased (refusing to run if that would merge two accounts) and a
check keeps them that way.

Revision ID: a1c2e3f4b5d6
Revises: f2a3b4c5d6e7
Create Date: 2026-11-16
"""
from alembic import op


revision = 'a1c2e3f4b5d6'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    clashes = bind.exec_driver_sql("""
        SELECT lower(trim(email)), count(*) FROM "user"
        GROUP BY lower(trim(email)) HAVING count(*) > 1
    """).fetchall()
    if clashes:
        raise RuntimeError(
            "These sign-in emails belong to more than one user once case is ignored: "
            + ", ".join(row[0] for row in clashes)
            + ". Change or remove the extra accounts first, then run the upgrade again.")
    op.execute('UPDATE "user" SET email = lower(trim(email)) WHERE email <> lower(trim(email))')
    op.create_check_constraint('ck_user_email_lower', 'user', 'email = lower(email)')


def downgrade():
    op.drop_constraint('ck_user_email_lower', 'user', type_='check')
