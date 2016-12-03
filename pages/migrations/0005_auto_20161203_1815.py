# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-12-03 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0004_auto_20161203_1815'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='slug',
            field=models.SlugField(default='', help_text='This is used to build the URL for this page', max_length=150, verbose_name='slug'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='page',
            name='title',
            field=models.CharField(default='', help_text='This title is also used for navigation menu items.', max_length=200, verbose_name='title'),
            preserve_default=False,
        ),
    ]
