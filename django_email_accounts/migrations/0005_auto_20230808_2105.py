# Generated by Django 3.2.19 on 2023-08-08 21:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_email_accounts', '0004_auto_20230731_2032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useremail',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
