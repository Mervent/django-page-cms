# -*- coding: utf-8 -*-
"""Django page CMS functionnal tests suite module."""
from pages.models import Page, Content, PageAlias
from pages.tests.testcase import TestCase

import django
from django.conf import settings
from django.core.urlresolvers import reverse
from pages.utils import get_now
from pages.phttp import get_request_mock
from pages.views import details
import datetime

add_url = reverse("admin:pages_page_add")
changelist_url = reverse("admin:pages_page_changelist")

class FunctionnalTestCase(TestCase):
    """Django page CMS functionnal tests suite class."""

    def test_add_page(self):
        """Test that the add admin page could be displayed via the
        admin"""
        c = self.get_admin_client()

        response = c.get(add_url)
        self.assertEqual(response.status_code, 200)

    def test_create_page(self):
        """Test that a page can be created via the admin."""
        c = self.get_admin_client()

        page_data = self.get_new_page_data()
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.from_slug(page_data['slug']).first()
        self.assertEqual(page.title(), page_data['title'])
        self.assertEqual(page.slug, page_data['slug'])
        self.assertNotEqual(page.last_modification_date, None)

    def test_create_page_should_not_create_slug_content(self):
        c = self.get_admin_client()

        page_data = self.get_new_page_data()
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.get(slug=page_data['slug'])
        with self.assertRaises(Content.DoesNotExist):
            Content.objects.get(page=page, type='slug', language='en-us')

    def test_slug_shound_not_be_converted_to_lowercase(self):
        c = self.get_admin_client()

        page_data = self.get_new_page_data()
        page_data['slug'] = 'UPPER SLUG'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.get(id=1)
        self.assertEqual(page.slug, 'UPPER-SLUG')

    def test_delete_page(self):
        """Create a page, then delete it."""
        c = self.get_admin_client()
        page_data = self.get_new_page_data()
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.from_slug(page_data['slug']).first()
        pageCount = Page.objects.count()
        page.delete()
        self.assertEqual(Page.objects.count(), pageCount - 1)

    def test_slug_collision(self):
        """Test a slug collision."""

        c = self.get_admin_client()

        page_data = self.get_new_page_data()
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)  # Page created
        response = c.post(add_url, page_data)
        self.assertContains(response, 'This URL is already taken')
        self.assertEqual(Page.objects.count(), 1)

        page1 = Page.objects.from_slug(page_data['slug']).first()
        page_data['position'] = 'first-child'
        page_data['target'] = page1.id
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(Page.objects.count(), 2)


    def test_details_view(self):
        """Test the details view basics."""

        c = self.get_admin_client()

        response = c.get(self.get_page_url())
        self.assertEqual(response.status_code, 404)

        page_data = self.get_new_page_data()
        page_data['status'] = Page.DRAFT
        response = c.post(add_url, page_data)

        response = c.get(self.get_page_url())
        self.assertEqual(response.status_code, 200)

        page_data = self.get_new_page_data()
        page_data['status'] = Page.PUBLISHED
        page_data['slug'] = 'test-page-2'
        page_data['template'] = 'pages/examples/index.html'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        response = c.get(self.get_page_url('test-page-2'))
        self.assertEqual(response.status_code, 200)

    def test_edit_page(self):
        """Test that a page can edited via the admin."""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        response = c.post(reverse('admin:pages_page_add'), page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.all()[0]
        response = c.get(reverse("admin:pages_page_change", args=[page.id]))
        self.assertEqual(response.status_code, 200)
        page_data['title'] = 'changed title'
        page_data['body'] = 'changed body'
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.get(id=page.id)
        self.assertEqual(page.title(), 'changed title')
        body = Content.objects.get_content(page, 'en-us', 'body')
        self.assertEqual(body, 'changed body')

    def test_site_framework(self):
        """Test the site framework, and test if it's possible to
        disable it."""

        from pages import settings as pages_settings

        # it's not possible to enforce PAGE_USE_SITE_ID in the tests
        if not pages_settings.PAGE_USE_SITE_ID:
            #TODO: use unittest.skip skip when 2.7
            return

        # this is necessary to make the test pass
        setattr(settings, "SITE_ID", 2)

        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data["sites"] = [2]
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.get(slug=page_data['slug'])
        self.assertEqual(page.sites.count(), 1)
        self.assertEqual(page.sites.all()[0].id, 2)

        page_data = self.get_new_page_data()
        page_data["sites"] = [3]
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        # we cannot get a slug that doesn't exist
        content = Page.objects.from_slug("this doesn't exist").first()
        self.assertEqual(content, None)
        with self.assertRaises(Page.DoesNotExist):
            Page.objects.get(slug="this doesn't exist")

        # we cannot get the data posted on another site
        content = Page.objects.from_slug(page_data['slug']).first()
        self.assertEqual(content, None)
        with self.assertRaises(Page.DoesNotExist):
            Page.objects.get(slug='slug')

        setattr(settings, "SITE_ID", 3)
        page = Page.objects.get(slug=page_data['slug'])
        self.assertEqual(page.sites.count(), 1)
        self.assertEqual(page.sites.all()[0].id, 3)

        # with param
        self.assertEqual(Page.objects.on_site(2).count(), 1)
        self.assertEqual(Page.objects.on_site(3).count(), 1)

        # without param
        self.assertEqual(Page.objects.on_site().count(), 1)
        setattr(settings, "SITE_ID", 2)
        self.assertEqual(Page.objects.on_site().count(), 1)

        page_data = self.get_new_page_data()
        page_data["sites"] = [2, 3]
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        self.assertEqual(Page.objects.on_site(3).count(), 2)
        self.assertEqual(Page.objects.on_site(2).count(), 2)
        self.assertEqual(Page.objects.on_site().count(), 2)

        setattr(pages_settings, "PAGE_USE_SITE_ID", False)

        # we should get everything
        self.assertEqual(Page.objects.on_site().count(), 3)

        setattr(settings, "SITE_ID", 1)

    def test_languages(self):
        """Test post a page with different languages
        and test that the admin views works correctly."""
        #TODO: Recheck all things
        c = self.get_admin_client()
        user = c.login(username='batiste', password='b')

        # test that the client language setting is used in add page admin
        c.cookies["django_language"] = 'de'
        response = c.get(add_url)

        self.assertContains(response, 'value="de"')
        c.cookies["django_language"] = 'fr-ch'
        response = c.get(add_url)
        self.assertContains(response, 'value="fr-ch"')

        page_data = self.get_new_page_data()
        page_data["title"] = 'english title'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.all()[0]
        self.assertEqual(page.get_languages(), ['en-us'])

        # test the language cache
        self.assertEqual(page.get_languages(), ['en-us'])

        # this test only works in version superior of 1.0.2
        django_version = django.get_version().rsplit()[0].split('.')
        if len(django_version) > 2:
            major, middle = [int(v) for v in django_version[:2]]
        else:
            major, middle = [int(v) for v in django_version]
        if major >= 1 and middle > 0:
            response = c.get(reverse("admin:pages_page_change", args=[page.id]) + '?language=de')
            self.assertContains(response, 'value="de"')

        # add a french version of the same page
        page_data["language"] = 'fr-ch'
        page_data["title"] = 'french title'
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        self.assertRedirects(response, changelist_url)

        # test that the frontend view use the good parameters
        # I cannot find a way of setting the accept-language HTTP
        # header so I used django_language cookie instead
        c = self.get_admin_client()
        c.cookies["django_language"] = 'en-us'
        response = c.get(page.get_url_path())
        self.assertContains(response, 'english title')
        self.assertContains(response, 'lang="en-us"')
        self.assertNotContains(response, 'french title')

        c = self.get_admin_client()
        c.cookies["django_language"] = 'fr-ch'
        response = c.get(page.get_url_path())
        self.assertContains(response, 'french title')
        self.assertContains(response, 'lang="fr-ch"')

        self.assertNotContains(response, 'english title')

        # this should be mapped to the fr-ch content
        c = self.get_admin_client()
        c.cookies["django_language"] = 'fr-fr'
        response = c.get(page.get_url_path())
        self.assertContains(response, 'french title')
        self.assertContains(response, 'lang="fr-ch"')

    def test_revision(self):
        """Test that a page can edited several times."""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        response = c.post(add_url, page_data)
        page = Page.objects.all()[0]

        page_data['body'] = 'changed body'
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        self.assertEqual(Content.objects.get_content(page, 'en-us', 'body'),
            'changed body')

        page_data['body'] = 'changed body 2'
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        page.invalidate()
        self.assertEqual(Content.objects.get_content(page, 'en-us', 'body'),
            'changed body 2')

        response = c.get(page.get_url_path())
        self.assertContains(response, 'changed body 2', 1)

        self.set_setting("PAGE_CONTENT_REVISION", False)

        self.assertEqual(Content.objects.get_content(page, 'en-us', 'body'),
            'changed body 2')

    def test_placeholder(self):
        """
        Test that the placeholder is correctly displayed in
        the admin
        """
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['template'] = 'pages/examples/nice.html'
        response = c.post(add_url, page_data)
        page = Page.objects.all()[0]
        response = c.get(reverse("admin:pages_page_change", args=[page.id]))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'name="right-column"', 1)

    def test_cannot_create_pages_with_same_url(self):
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()

        page_data['slug'] = 'same-slug'
        response = c.post(add_url, page_data)
        # the redirect tell that the page has been create correctly
        self.assertRedirects(response, changelist_url)
        response = c.get(self.get_page_url('same-slug/'))
        self.assertEqual(response.status_code, 200)

        response = c.post(add_url, page_data)
        # we cannot create 2 pages with the same complete_slug
        self.assertEqual(response.status_code, 200)

    def test_directory_slug(self):
        """
        Test diretory slugs
        """
        c = self.get_admin_client()
        c.login(username='batiste', password='b')

        page_data = self.get_new_page_data()
        page_data['title'] = 'parent title'
        page_data['slug'] = 'same-slug'
        response = c.post(add_url, page_data)
        # the redirect tell that the page has been create correctly
        self.assertRedirects(response, changelist_url)
        response = c.get(self.get_page_url('same-slug/'))
        self.assertEqual(response.status_code, 200)

        page = Page.objects.all()[0]

        response = c.post(add_url, page_data)
        # we cannot create 2 root page with the same slug
        # this assert test that the creation fails as wanted
        self.assertEqual(response.status_code, 200)

        page1 = Page.objects.from_slug(page_data['slug']).first()
        self.assertEqual(page1.id, page.id)

        page_data['title'] = 'children title'
        page_data['target'] = page1.id
        page_data['position'] = 'first-child'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        # finaly test that we can get every page according the path
        response = c.get(self.get_page_url('same-slug'))
        self.assertContains(response, "parent title", 3)

        response = c.get(self.get_page_url('same-slug/same-slug'))
        self.assertContains(response, "children title", 3)

    def test_reversion_integration(self):
        from reversion.models import Version
        from pages.templatetags.pages_tags import show_revisions

        language = 'en-us'
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['body'] = 'old content'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.all().first()
        content = Content.objects.get_content_object(page=page, language=language, ctype='body')
        page_data['body'] = 'new content'
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        self.assertRedirects(response, changelist_url)
        versions = Version.objects.get_for_object(content).order_by('id')
        self.assertEqual(len(versions), 2)

        # show_revision should return versions from reversion
        revisions = show_revisions(context=None, page=page, content_type='body', lang=language)
        self.assertIn('old content', str(revisions))
        self.assertIn('new content', str(revisions))

        # get_reversion_content should return content body by reversion_id
        response = c.get(reverse('admin:page-get-reversion-content', args=[page.id, versions[0].id]))
        self.assertContains(response, 'old content')
        response = c.get(reverse('admin:page-get-reversion-content', args=[page.id, versions[1].id]))
        self.assertContains(response, 'new content')


    def test_page_admin_view(self):
        """Test page admin view"""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page-1'
        response = c.post(add_url, page_data)
        page = Page.objects.get(slug='page-1')
        self.assertEqual(page.status, 1)
        change_status_url = reverse("admin:page-change-status", args=[page.id])
        response = c.post(change_status_url , {'status':Page.DRAFT})
        page = Page.objects.get(slug='page-1')
        self.assertEqual(page.status, Page.DRAFT)

        url = reverse("admin:page-modify-content", args=[page.id, "title", "en-us"])
        response = c.post(url, {'content': 'test content'})
        self.assertEqual(page.title(), 'test content')

        # TODO: realy test these methods
        url = reverse("admin:page-traduction", args=[page.id, "en-us"])
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse("admin:page-sub-menu", args=[page.id])
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse("admin:page-delete-content", args=[page.id, "en-us"])
        response = c.get(url)
        self.assertEqual(response.status_code, 302)

    def test_page_alias(self):
        """Test page aliasing system"""

        c = self.get_admin_client()
        c.login(username='batiste', password='b')

        # create some pages
        page_data = self.get_new_page_data()
        page_data['title'] = 'home-page-title'
        page_data['slug'] = 'home-page'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page_data['title'] =  'downloads-page-title'
        page_data['slug'] = 'downloads-page'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        # create aliases for the pages
        page = Page.objects.from_path('home-page', None)
        self.assertTrue(page)
        p = PageAlias(page=page, url='/index.php')
        p.save()

        page = Page.objects.from_path('downloads-page', None)
        self.assertTrue(page)
        p = PageAlias(page=page, url='index.php?page=downloads')
        p.save()

        # now check whether we can retrieve the pages.
        # is the homepage available from is alias
        response = c.get(self.get_page_url('index.php'))
        self.assertRedirects(response, self.get_page_url('home-page'), 301)

        # for the download page, the slug is canonical
        response = c.get(self.get_page_url('downloads-page/'))
        self.assertContains(response, "downloads-page-title", 3)

        # calling via its alias must cause redirect
        response = c.get(self.get_page_url('index.php')+'?page=downloads')
        self.assertRedirects(response,
            self.get_page_url('downloads-page'), 301)

    def test_page_redirect_to(self):
        """Test page redirected to an other page."""

        client = self.get_admin_client()

        # create some pages
        page1 = self.create_new_page(client)
        page2 = self.create_new_page(client)

        page1.redirect_to = page2
        page1.save()

        # now check whether you go to the target page.
        response = client.get(page1.get_url_path())
        self.assertRedirects(response, page2.get_url_path(), 301)

    def test_page_valid_targets(self):
        """Test page valid_targets method"""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'root'
        response = c.post(add_url, page_data)
        root_page = Page.objects.get(slug='root')
        page_data['position'] = 'first-child'
        page_data['target'] = root_page.id
        page_data['slug'] = 'child-1'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)
        c1 = Page.objects.get(slug='child-1')

        root_page = Page.objects.get(slug='root')
        self.assertEqual(len(root_page.valid_targets()), 0)
        self.assertEqual(str(c1.valid_targets()), "[<Page: root>]")

    def test_ajax_language(self):
        """Test that language is working properly"""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        # Activate a language other than settings.LANGUAGE_CODE
        response = c.post('/i18n/setlang/', {'language':'fr-ch' })
        try:
            from django.utils.translation import LANGUAGE_SESSION_KEY
        except ImportError:
            LANGUAGE_SESSION_KEY = 'django_language'
        self.assertEqual(c.session.get(LANGUAGE_SESSION_KEY, False), 'fr-ch')

        # Make sure we're in french
        response = c.get(changelist_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Auteur' in response.content)

        # Create some pages (taken from test_tree_admin_interface)
        page_data = self.get_new_page_data()
        page_data['slug'] = 'root'
        response = c.post(add_url, page_data)

        root_page = Page.objects.from_slug('root').first()
        page_data['position'] = 'first-child'
        page_data['target'] = root_page.id
        page_data['slug'] = 'child-1'
        response = c.post(add_url, page_data)

        child_1 = Page.objects.from_slug('child-1').first()

        page_data['slug'] = 'child-2'
        response = c.post(add_url, page_data)

        child_2 = Page.objects.from_slug('child-2').first()

        self.assertEqual(str(Page.objects.all()),
            "[<Page: root>, <Page: child-2>, <Page: child-1>]")

        """
        The relevant bit, fixed by rev 501: the response issued by a move
        command returns content localized in settings.LANGUAGE_CODE (i.e. 'en´)
        even though the original AJAX request passed in a the correct
        session ID localizing this client as fr-ch

        This is probably because the LocaleMiddleware gets instantiated
        with a couple request_mocks which have no real connection to the
        AJAX request *but* django.utils.translation caches the active
        language on a per thread basis.

        This means that the first "bogus" call to
        LocaleMiddleware.process_request will "kill" the localization
        data for the AJAX request.

        Rev. 501 fixes this by passing in the language code from the original
        request.
        """
        url = reverse("admin:page-move-page", args=[child_1.id])
        response = c.post(url, {'position':'first-child', 'target':root_page.id})

        # Make sure the content response we got was in french
        self.assertTrue(b'Auteur' in response.content)

    def test_move_page_should_rename_page_on_slug_collision(self):
        c = self.get_admin_client()
        c.login(username='batiste', password='b')

        page_data = self.get_new_page_data()
        page_data['slug'] = 'root'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)

        root_page = Page.objects.from_slug('root').first()
        page_data['slug'] = 'page1'
        page_data['position'] = 'first-child'
        page_data['target'] = root_page.id
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)

        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)

        page_move = Page.objects.from_path('page1', lang='en-us')
        url = reverse("admin:page-move-page", args=[page_move.id])
        response = c.post(url, {'position': 'first-child', 'target': root_page.id})
        self.assertEqual(response.status_code, 200)
        page_move.refresh_from_db()
        # By current design '-1/-2/-3/etc' appends to page complete_slug if complete_slug is not unique
        self.assertTrue(page_move.complete_slug.endswith('-1'))

    def test_view_context(self):
        """
        Test that the default view can only return the context
        """
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        # create a page for the example otherwise you will get a Http404 error
        response = c.post(add_url, page_data)
        page1 = Page.objects.get(slug='page1')

        from pages.views import details
        request = get_request_mock()
        context = details(request, path='/page1/', only_context=True)
        self.assertEqual(context['current_page'], page1)

    def test_request_mockup(self):
        request = get_request_mock()
        self.assertEqual(hasattr(request, 'session'), True)

    def test_tree_admin_interface(self):
        """
        Test that moving/creating page in the tree is working properly
        using the admin interface
        """
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'root'

        response = c.post(add_url, page_data)

        root_page = Page.objects.get(slug='root')
        self.assertTrue(root_page.is_first_root())
        page_data['position'] = 'first-child'
        page_data['target'] = root_page.id
        page_data['slug'] = 'child-1'
        response = c.post(add_url, page_data)

        child_1 = Page.objects.get(slug='child-1')
        self.assertFalse(child_1.is_first_root())

        page_data['slug'] = 'child-2'
        response = c.post(add_url, page_data)

        child_2 = Page.objects.get(slug='child-2')

        self.assertEqual(str(Page.objects.all()),
            "[<Page: root>, <Page: child-2>, <Page: child-1>]")
        # move page 1 in the first position
        move_url = reverse("admin:page-move-page", args=[child_1.id])
        response = c.post(move_url,
            {'position':'first-child', 'target':root_page.id})

        self.assertEqual(str(Page.objects.all()),
            "[<Page: root>, <Page: child-1>, <Page: child-2>]")

        # move page 2 in the first position
        move_url = reverse("admin:page-move-page", args=[child_2.id])
        response = c.post(move_url,
            {'position': 'left', 'target': child_1.id})

        self.assertEqual(str(Page.objects.all()),
            "[<Page: root>, <Page: child-2>, <Page: child-1>]")

        # try to create a sibling with the same slug, via first-child
        # should not create and return code 200, instead of 302 redirect
        page_data['target'] = child_2.id
        page_data['position'] = 'first-child'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)

        page_data['target'] = root_page.id
        page_data['position'] = 'first-child'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 200)

        # try to create a sibling via left, right
        # should not create and return code 200, instead of 302 redirect
        page_data['target'] = child_2.id
        page_data['position'] = 'left'
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 200)

        # try to create a second page 2 in root
        del page_data['target']
        del page_data['position']

        # create page without root parent
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 302)

        # cannot create same page twice
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Page.objects.count(), 5)
        # Should not work because we already have sibling at the same level
        response = c.post(add_url, page_data)
        self.assertEqual(response.status_code, 200)

        # try to change the page 2 slug into page 1
        page_data['slug'] = 'child-1'
        response = c.post(reverse("admin:pages_page_change", args=[child_2.id]), page_data)
        self.assertEqual(response.status_code, 200)

        # try to change the page 2 slug into something new
        page_data['slug'] = 'child-3'
        response = c.post(reverse("admin:pages_page_change", args=[child_2.id]), page_data)
        self.assertEqual(response.status_code, 302)


    def test_tree(self):
        """
        Test that the navigation tree works properly with mptt.
        """
        c = self.get_admin_client()
        c.login(username='batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        response = c.post(add_url, page_data)
        page_data['slug'] = 'page2'
        response = c.post(add_url, page_data)
        page_data['slug'] = 'page3'
        response = c.post(add_url, page_data)
        self.assertEqual(str(Page.objects.navigation()),
            "[<Page: page1>, <Page: page2>, <Page: page3>]")

        p1 = Page.objects.get(slug='page1')
        p2 = Page.objects.get(slug='page2')
        p3 = Page.objects.get(slug='page3')

        p2.move_to(p1, 'left')
        p2.save()

        self.assertEqual(str(Page.objects.navigation()),
            "[<Page: page2>, <Page: page1>, <Page: page3>]")

        p3.move_to(p2, 'left')
        p3.save()

        self.assertEqual(str(Page.objects.navigation()),
            "[<Page: page3>, <Page: page2>, <Page: page1>]")

        p1 = Page.objects.get(slug='page1')
        p2 = Page.objects.get(slug='page2')
        p3 = Page.objects.get(slug='page3')

        p3.move_to(p1, 'first-child')
        p2.move_to(p1, 'first-child')

        self.assertEqual(str(Page.objects.navigation()),
            "[<Page: page1>]")

        p3 = Page.objects.get(slug='page3')
        p3.move_to(p1, 'left')

        self.assertEqual(str(Page.objects.navigation()),
            "[<Page: page3>, <Page: page1>]")

    def test_page_redirect_to_url(self):
        """Test page redirected to external url."""

        client = self.get_admin_client()

        page1 = self.create_new_page(client)
        url = 'http://code.google.com/p/django-page-cms/'
        page1.redirect_to_url = url
        page1.save()

        # now check whether we can retrieve the page.
        response = client.get(page1.get_url_path())
        # TODO: Check why it's not working without fetch_redirect_response=False
        self.assertRedirects(response, expected_url=url, status_code=301, fetch_redirect_response=False)


    def test_page_freeze_date(self):
        """Test page freezing feature."""
        c = self.get_admin_client()
        page_data = self.get_new_page_data()
        page_data['title'] = 'before'
        page_data['slug'] = 'before'
        page_data['body'] = 'before'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)
        page = Page.objects.from_path('before', None)
        self.assertEqual(page.freeze_date, None)
        limit = get_now()
        page.freeze_date = limit
        page.save()

        page_data['title'] = 'after'
        page_data['slug'] = 'after'
        page_data['body'] = 'after'
        # this post erase the limit
        response = c.post(reverse("admin:pages_page_change", args=[page.id]), page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.from_path('after', None)
        page.freeze_date = limit
        self.assertEqual(page.get_content(ctype='body', language='en-us'), 'before')
        page.freeze_date = None
        page.save()
        self.assertEqual(page.get_content(ctype='body', language='en-us'), 'after')
        page.freeze_date = limit
        page.save()
        self.assertEqual(page.get_content(ctype='body', language='en-us'), 'before')

    def test_delegate_to(self):
        """Test the view delegate feature."""
        c = self.get_admin_client()
        page_data = self.get_new_page_data()
        page_data['title'] = 'delegate'
        page_data['slug'] = 'delegate'
        response = c.post(add_url, page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.from_path('delegate', None)

        from pages import urlconf_registry as reg
        reg.register_urlconf('test', 'pages.testproj.documents.urls',
            label='test')
        page.delegate_to = 'test'
        page.save()

        response = c.get(self.get_page_url('delegate'))
        self.assertEqual(response.status_code, 200)

        from pages.testproj.documents.models import Document
        doc = Document(title='doc title 1', text='text', page=page)
        doc.save()

        url = self.get_page_url('delegate/doc-%d' % doc.id)
        self.assertTrue(str(doc.id) in url)

        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "doc title 1")
        reg.registry = []

    def test_untranslated(self):
        """Test the untranslated feature in the admin."""
        c = self.get_admin_client()
        page_data = self.get_new_page_data()
        page_data['title'] = 'untranslated'
        page_data['slug'] = 'untranslated'
        unstranslated_string = 'the untranslated string'
        page_data['untrans'] = unstranslated_string
        page_data['template'] = 'pages/tests/untranslated.html'
        response = c.post(add_url + '?language=en-us', page_data)
        self.assertRedirects(response, changelist_url)

        page = Page.objects.from_path('untranslated', None)
        self.assertEqual(
            Content.objects.get_content(page, 'en-us', 'untrans'),
            unstranslated_string
        )

        page_data['untrans'] = ''
        response = c.get(reverse("admin:pages_page_change", args=[page.id]) + '?language=fr-ch')
        self.assertContains(response, unstranslated_string)

    def test_root_page(self):
        """Test that the root page doesn't trigger a 404."""
        c = self.get_admin_client()
        page1 = self.new_page(content={'slug': 'this-is-not-a-404'})
        self.assertEqual(Page.objects.count(), 1)
        page = Page.objects.on_site()[0]
        self.assertTrue(page.is_first_root())

        response = c.get(self.get_page_url())
        self.assertEqual(response.status_code, 200)

    def test_page_with_trailing_slash(self):
        """
        Test that a page is also available with and without a trailing slash.
        """
        # TODO: Fix this, it's not recommended behavior by google.
        # TODO: We should redirect from one page to another
        c = self.get_admin_client()
        page1 = self.new_page(content={'slug': 'root'})
        page2 = self.new_page(content={'slug': 'other'})
        response = c.get(self.get_page_url('other'))
        self.assertEqual(response.status_code, 200)
        response = c.get(self.get_page_url('other/'))
        self.assertEqual(response.status_code, 200)

    def test_page_sitemap(self):
        """
        Test the sitemap class
        """
        c = self.get_admin_client()
        page1 = self.new_page(content={'slug': 'english-slug'})
        page1.save()
        page2 = self.new_page(content={'slug': 'french-slug'})
        page2.save()

        response = c.get('/sitemap.xml')

        self.assertContains(response, 'english-slug')
        self.assertContains(response, 'french-slug')

        # TODO: Do not test multilanguage setup for now
        #response = c.get('/sitemap2.xml')

        #self.assertContains(response, 'english-slug')
        #self.assertContains(response, 'french-slug')

    def test_fileinput_in_admin(self):
        """Test that a page can edited via the admin."""
        c = self.get_admin_client()
        c.login(username='batiste', password='b')

        page = self.new_page(content={'slug': 'just-a-test', 'file':'some file'})
        page.template = 'pages/tests/fileinput.html'
        page.save()

        response = c.get(reverse("admin:pages_page_change", args=[page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'some file')
