# Generated by Django 5.1.3 on 2024-11-21 13:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userService', '0008_alter_profile_display_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('from_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='from_friend_set', to='userService.profile')),
                ('to_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_friend_set', to='userService.profile')),
            ],
            options={
                'unique_together': {('from_profile', 'to_profile')},
            },
        ),
    ]
