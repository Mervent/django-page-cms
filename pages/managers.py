# -*- coding: utf-8 -*-
"""Django page CMS ``managers``."""
from pages import settings
from pages.cache import cache
from pages.utils import normalize_url, get_now
from pages.phttp import get_slug

from django.db import models
from django.db.models import Q
from django.db.models import Avg, Max, Min, Count
from django.conf import settings as global_settings

from mptt.managers import TreeManager


class PageManager(TreeManager):
    """
    Page manager provide several filters to obtain pages :class:`QuerySet`
    that respect the page attributes and project settings.
    """

    if settings.PAGE_HIDE_SITES:
        def get_query_set(self):
            """Restrict operations to pages on the current site."""
            return super(PageManager, self).get_query_set().filter(
                sites=global_settings.SITE_ID)

    def on_site(self, site_id=None):
        """Return a :class:`QuerySet` of pages that are published on the site
        defined by the ``SITE_ID`` setting.

        :param site_id: specify the id of the site object to filter with.
        """
        if settings.PAGE_USE_SITE_ID:
            if not site_id:
                site_id = global_settings.SITE_ID
            return self.filter(sites=site_id)
        return self.all()

    def root(self):
        """Return a :class:`QuerySet` of pages without parent."""
        return self.on_site().filter(parent__isnull=True)

    def navigation(self):
        """Creates a :class:`QuerySet` of the published root pages."""
        return self.on_site().filter(
            status=self.model.PUBLISHED).filter(parent__isnull=True)

    def hidden(self):
        """Creates a :class:`QuerySet` of the hidden pages."""
        return self.on_site().filter(status=self.model.HIDDEN)

    def filter_published(self, queryset):
        """Filter the given pages :class:`QuerySet` to obtain only published
        page."""
        if settings.PAGE_USE_SITE_ID:
            queryset = queryset.filter(sites=global_settings.SITE_ID)

        queryset = queryset.filter(status=self.model.PUBLISHED)

        if settings.PAGE_SHOW_START_DATE:
            queryset = queryset.filter(publication_date__lte=get_now())

        if settings.PAGE_SHOW_END_DATE:
            queryset = queryset.filter(
                Q(publication_end_date__gt=get_now()) |
                Q(publication_end_date__isnull=True)
            )

        return queryset

    def published(self):
        """Creates a :class:`QuerySet` of published
        :class:`Page <pages.models.Page>`."""
        return self.filter_published(self)

    def drafts(self):
        """Creates a :class:`QuerySet` of drafts using the page's
        :attr:`Page.publication_date`."""
        pub = self.on_site().filter(status=self.model.DRAFT)
        if settings.PAGE_SHOW_START_DATE:
            pub = pub.filter(publication_date__gte=get_now())
        return pub

    def expired(self):
        """Creates a :class:`QuerySet` of expired using the page's
        :attr:`Page.publication_end_date`."""
        return self.on_site().filter(
            publication_end_date__lte=get_now())

    def from_path(self, complete_path, lang, exclude_drafts=True):
        """Return a :class:`Page <pages.models.Page>` according to
        the page's path."""

        # just return the root page
        if complete_path == '':
            root_pages = self.root()
            if root_pages:
                return root_pages[0]
            else:
                return None

        stripped = complete_path.strip('/')

        try:
            return self.on_site().get(cached_url='/%s' % stripped if stripped else '/')
        except self.model.DoesNotExist:
            return None

    def from_slug(self, slug):
        return self.on_site().filter(slug=slug)


class ContentManager(models.Manager):
    """:class:`Content <pages.models.Content>` manager methods"""

    PAGE_CONTENT_DICT_KEY = "page_content_dict_%d_%s_%d"

    def set_or_create_content(self, page, language, ctype, body):
        """Set or create a :class:`Content <pages.models.Content>` for a
        particular page and language.

        :param page: the concerned page object.
        :param language: the wanted language.
        :param ctype: the content type.
        :param body: the content of the Content object.
        """
        try:
            content = self.filter(page=page, language=language,
                                  type=ctype).latest('creation_date')
            content.body = body
        except self.model.DoesNotExist:
            content = self.model(page=page, language=language, body=body,
                                 type=ctype)
        content.save()
        return content

    def create_content_if_changed(self, page, language, ctype, body):
        """Create a :class:`Content <pages.models.Content>` for a particular
        page and language only if the content has changed from the last
        time.

        :param page: the concerned page object.
        :param language: the wanted language.
        :param ctype: the content type.
        :param body: the content of the Content object.
        """
        try:
            content = self.filter(page=page, language=language,
                                  type=ctype).latest('creation_date')
            if content.body == body:
                return content
        except self.model.DoesNotExist:
            pass
        content = self.create(page=page, language=language, body=body,
                type=ctype)

        # Delete old revisions
        if settings.PAGE_CONTENT_REVISION_DEPTH:
            oldest_content = self.filter(page=page, language=language,
                type=ctype).order_by('-creation_date')[settings.PAGE_CONTENT_REVISION_DEPTH:]
            for c in oldest_content:
                c.delete()

        return content

    def get_content_object(self, page, language, ctype):
        """Gets the latest published :class:`Content <pages.models.Content>`
        for a particular page, language and placeholder type."""
        params = {
            'language': language,
            'type': ctype,
            'page': page
        }
        if page.freeze_date:
            params['creation_date__lte'] = page.freeze_date
        return self.filter(**params).latest()

    def get_content(self, page, language, ctype, language_fallback=False):
        """Gets the latest content string for a particular page, language and
        placeholder.

        :param page: the concerned page object.
        :param language: the wanted language.
        :param ctype: the content type.
        :param language_fallback: fallback to another language if ``True``.
        """
        if " " in ctype:
            raise ValueError("Ctype cannot contain spaces.")
        if not language:
            language = settings.PAGE_DEFAULT_LANGUAGE
        # TODO: Remove that dirty hacking
        if ctype == 'title':
            return page.title
        elif ctype == 'slug':
            return page.slug

        frozen = int(bool(page.freeze_date))
        key = self.PAGE_CONTENT_DICT_KEY % (page.id, ctype, frozen)

        # Spaces do not work with memcache
        key = key.replace(' ', '-')

        if page._content_dict is None:
            page._content_dict = dict()
        if page._content_dict.get(key, None):
            content_dict = page._content_dict.get(key)
        else:
            content_dict = cache.get(key)

        # fill a dict object for each language, that will create
        # P * L queries.
        # L == number of language, P == number of placeholder in the page.
        # Once generated the result is cached.
        if not content_dict:
            content_dict = {}
            for lang in settings.PAGE_LANGUAGES:
                try:
                    content = self.get_content_object(page, lang[0], ctype)
                    content_dict[lang[0]] = content.body
                except self.model.DoesNotExist:
                    content_dict[lang[0]] = ''
            page._content_dict[key] = content_dict
            cache.set(key, content_dict)

        if language in content_dict and content_dict[language]:
            return content_dict[language]

        if language_fallback:
            for lang in settings.PAGE_LANGUAGES:
                if lang[0] in content_dict and content_dict[lang[0]]:
                    return content_dict[lang[0]]
        return ''

    def get_content_slug_by_slug(self, slug):
        """
        Dummy method while migrating to new design
        TODO: Remove me and fix tests
        """
        from pages.models import Page
        page = Page.objects.on_site().filter(slug=slug).first()
        return page and self.model(page=page)

        content = self.filter(type='slug', body=slug)
        if settings.PAGE_USE_SITE_ID:
            content = content.filter(page__sites__id=global_settings.SITE_ID)
        try:
            content = content.latest('creation_date')
        except self.model.DoesNotExist:
            return None
        else:
            return content

    def get_page_ids_by_slug(self, slug):
        """Return all page's id matching the given slug.
        This function also returns pages that have an old slug
        that match.

        :param slug: the wanted slug.
        """
        ids = self.filter(type='slug', body=slug).values('page_id').annotate(
            max_creation_date=Max('creation_date')
        )
        return [content['page_id'] for content in ids]


class PageAliasManager(models.Manager):
    """:class:`PageAlias <pages.models.PageAlias>` manager."""

    def from_path(self, request, path, lang):
        """
        Resolve a request to an alias. returns a
        :class:`PageAlias <pages.models.PageAlias>` if the url matches
        no page at all. The aliasing system supports plain
        aliases (``/foo/bar``) as well as aliases containing GET parameters
        (like ``index.php?page=foo``).

        :param request: the request object
        :param path: the complete path to the page
        :param lang: not used
        """
        from pages.models import PageAlias

        url = normalize_url(path)
        # §1: try with complete query string
        query = request.META.get('QUERY_STRING')
        if query:
            url = url + '?' + query
        try:
            alias = PageAlias.objects.get(url=url)
            return alias
        except PageAlias.DoesNotExist:
            pass
        # §2: try with path only
        url = normalize_url(path)
        try:
            alias = PageAlias.objects.get(url=url)
            return alias
        except PageAlias.DoesNotExist:
            pass
        # §3: not alias found, we give up
        return None
