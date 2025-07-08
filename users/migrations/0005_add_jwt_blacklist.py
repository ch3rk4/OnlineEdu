# Generated migration for JWT token blacklist
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_add_stripe_fields'),
        ('token_blacklist', '0001_initial'),  # Зависимость от приложения token_blacklist
    ]

    operations = [
        # Эта миграция просто обеспечивает правильный порядок миграций
        # Фактические таблицы создаются приложением token_blacklist
    ]