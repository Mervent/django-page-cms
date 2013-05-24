# -*- coding: utf-8 -*-
"""Django haystack `SearchIndex` module."""
from pages.models import Page
from pages import settings

from haystack.indexes import SearchIndex, CharField, DateTimeField, Indexable


if settings.PAGE_REAL_TIME_SEARCH:
    class RealTimePageIndex(SearchIndex):
        """Search index for pages content."""
        text = CharField(document=True, use_template=True)
        title = CharField(model_attr='title')
        url = CharField(model_attr='get_absolute_url')
        publication_date = DateTimeField(model_attr='publication_date')

        def index_queryset(self, using=None):
            """ Haystack 2.0 requires this method now """
            return self.get_model().objects.published()

        def get_queryset(self):
            """Used when the entire index for model is updated."""
            return Page.objects.published()

        def get_model(self):
            Page

else:
    class PageIndex(SearchIndex, Indexable):
        """Search index for pages content."""
        text = CharField(document=True, use_template=True)
        title = CharField(model_attr='title')
        url = CharField(model_attr='get_absolute_url')
        publication_date = DateTimeField(model_attr='publication_date')

        def get_queryset(self):
            """Used when the entire index for model is updated."""
            return Page.objects.published()

        def get_model(self):
            Page

