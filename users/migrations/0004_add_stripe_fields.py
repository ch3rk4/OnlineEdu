# Generated migration for Stripe integration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Ожидает оплаты'),
                    ('processing', 'Обрабатывается'),
                    ('completed', 'Завершен'),
                    ('failed', 'Ошибка'),
                    ('cancelled', 'Отменен'),
                    ('refunded', 'Возвращен'),
                ],
                default='pending',
                max_length=20,
                verbose_name='Статус платежа'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='stripe_product_id',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='ID продукта в Stripe'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='stripe_price_id',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='ID цены в Stripe'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='stripe_session_id',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='ID сессии в Stripe'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='stripe_checkout_url',
            field=models.URLField(
                blank=True,
                null=True,
                verbose_name='Ссылка на оплату Stripe'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='description',
            field=models.TextField(
                blank=True,
                verbose_name='Описание платежа'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                verbose_name='Дата обновления'
            ),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('cash', 'Наличные'),
                    ('transfer', 'Перевод на счет'),
                    ('stripe', 'Stripe (банковская карта)'),
                ],
                max_length=10,
                verbose_name='Способ оплаты'
            ),
        ),
    ]