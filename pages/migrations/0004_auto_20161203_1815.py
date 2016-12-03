# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-12-03 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0003_page_uuid'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='page',
            options={'get_latest_by': 'publication_date', 'ordering': ['tree_id', 'lft'], 'permissions': [('can_freeze', 'Can freeze page'), ('can_publish', 'Can publish page'), ('can_manage_ru', 'Manage Russian')], 'verbose_name': 'page', 'verbose_name_plural': 'pages'},
        ),
        migrations.AddField(
            model_name='page',
            name='cached_url',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=255, verbose_name='Cached URL'),
        ),
        migrations.AlterField(
            model_name='page',
            name='sites',
            field=models.ManyToManyField(default=[2], help_text='The site(s) the page is accessible at.', to='sites.Site', verbose_name='sites'),
        ),
    ]