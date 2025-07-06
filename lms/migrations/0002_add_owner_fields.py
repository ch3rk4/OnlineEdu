# Generated migration for adding owner fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lms', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='owner',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='courses',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Владелец'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='lesson',
            name='owner',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='lessons',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Владелец'
            ),
            preserve_default=False,
        ),
    ]