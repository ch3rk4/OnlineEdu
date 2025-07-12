# Generated migration for notification tracking
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0004_remove_subscription_unique_user_course_subscription_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='last_notification_sent',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Время последнего уведомления',
                help_text='Когда в последний раз отправлялись уведомления подписчикам о обновлении курса'
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='notification_enabled',
            field=models.BooleanField(
                default=True,
                verbose_name='Уведомления включены',
                help_text='Разрешать ли отправку уведомлений при обновлении курса'
            ),
        ),
    ]