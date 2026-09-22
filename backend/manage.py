#!/usr/bin/env python
"""
Standard management entry point.

    python manage.py run                          # dev server
    python manage.py db init / migrate / upgrade   # Flask-Migrate (Alembic)
    python manage.py create-admin                  # bootstrap the first admin
    python manage.py list-pending                  # moderation queue, CLI-side
    python manage.py grant-premium user@example.com

This works because app.cli is Flask's own click Group — calling it runs
the full set of built-in + extension + custom commands with the app
context already handled, so nothing here needs FLASK_APP set separately.
"""

from apps import create_app

app = create_app()

if __name__ == "__main__":
    app.cli()
