"""Initialize or update the configured production database once.

Run this locally with DATABASE_URL and SECRET_KEY set to the same values used
by Vercel. Demo users and their well-known passwords are intentionally omitted.
"""

import os


if not any(os.environ.get(name) for name in ('DATABASE_URL', 'POSTGRES_URL', 'NILEDB_URL')):
    raise SystemExit('Set DATABASE_URL, POSTGRES_URL, or NILEDB_URL before running this command.')

from app import User, app, db, init_db


init_db(seed_demo_users=False)

admin_email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
admin_password = os.environ.get('ADMIN_PASSWORD', '')
admin_username = os.environ.get('ADMIN_USERNAME', 'admin').strip() or 'admin'

if admin_email or admin_password:
    if not admin_email or len(admin_password) < 12:
        raise SystemExit(
            'To create the first administrator, set ADMIN_EMAIL and an '
            'ADMIN_PASSWORD containing at least 12 characters.'
        )
    with app.app_context():
        admin = User.query.filter_by(email=admin_email).first()
        if admin is None:
            admin = User(
                username=admin_username,
                email=admin_email,
                first_name='Admin',
                last_name='User',
                is_admin=True,
                is_super_admin=True,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
        else:
            admin.is_admin = True
            admin.is_super_admin = True
            admin.set_password(admin_password)
        db.session.commit()
        print(f'Production administrator configured: {admin_email}')
else:
    print('Schema initialized. No administrator created; ADMIN_EMAIL and ADMIN_PASSWORD were not set.')
