# -*- coding: utf-8 -*-
"""Django page CMS plugin test suite module."""
from pages.tests.testcase import TestCase
from pages.plugins.jsonexport import utils
from pages.models import Page, Content
import json
from pages.plugins.jsonexport.tests import JSONExportTestCase


class Dummy(JSONExportTestCase):
    pass


class PluginTestCase(TestCase):
    """Django page CMS plugin tests."""

    def test_json_parsing(self):
        """Test page date ordering feature."""
        page1 = self.new_page(slug='p1', title='t1')
        page2 = self.new_page(slug='p2', title='t2')
        Content(page=page1, type='body', body='text', language='en-us').save()
        Content(page=page2, type='body', body='more text', language='en-us').save()
        jsondata = utils.pages_to_json(Page.objects.all())

        self.assertIn("p1", jsondata)
        self.assertIn("t1", jsondata)
        self.assertIn("text", jsondata)
        self.assertIn("p2", jsondata)
        self.assertIn("t2", jsondata)
        self.assertIn("more text", jsondata)
        data = json.loads(jsondata)
        self.assertEqual(len(data['pages']), 2)
