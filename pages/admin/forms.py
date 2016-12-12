# -*- coding: utf-8 -*-
"""Page CMS forms"""
from django import forms
from pages.utils import slugify
from django.utils.translation import ugettext_lazy as _

from pages import settings
from pages.models import Page

from pages.urlconf_registry import get_choices
from pages.widgets import LanguageChoiceWidget

error_dict = {
    'another_page_error': _('Another page with this slug already exists'),
    'sibling_position_error': _('A sibling with this slug already exists at the targeted position'),
    'child_error': _('A child with this slug already exists at the targeted position'),
    'sibling_error': _('A sibling with this slug already exists'),
    'sibling_root_error': _('A sibling with this slug already exists at the root level'),
}

def make_form(model_, placeholders):

    # a new form is needed every single time as some
    # initial data are bound
    class PageForm(forms.ModelForm):
        """Form for page creation"""

        def __init__(self, *args, **kwargs):
            super(PageForm, self).__init__(*args, **kwargs)
            for p in placeholders:
                if not self.fields[p.ctype]:
                    self.fields[p.ctype] = forms.TextField()

        target = forms.IntegerField(required=False, widget=forms.HiddenInput)
        position = forms.CharField(required=False, widget=forms.HiddenInput)

        class Meta:
            model = model_
            exclude = ('author', 'last_modification_date', 'parent')

        title = forms.CharField(
            label=_('Title'),
            widget=forms.TextInput(),
        )
        slug = forms.CharField(
            label=_('Slug'),
            widget=forms.TextInput(),
            help_text=_('The slug will be used to create the page URL, it must be unique among the other pages of the same level.')
        )

        language = forms.ChoiceField(
            label=_('Language'),
            choices=settings.PAGE_LANGUAGES,
            widget=LanguageChoiceWidget()
        )
        template = forms.ChoiceField(
            required=False,
            label=_('Template'),
            choices=settings.get_page_templates(),
        )
        delegate_to = forms.ChoiceField(
            required=False,
            label=_('Delegate to application'),
            choices=get_choices(),
        )
        freeze_date = forms.DateTimeField(
            required=False,
            label=_('Freeze'),
            help_text=_("Don't publish any content after this date. Format is 'Y-m-d H:M:S'")
            # those make tests fail miserably
            #widget=widgets.AdminSplitDateTime()
            #widget=widgets.AdminTimeWidget()
        )

        def clean_slug(self):
            slug = slugify(self.cleaned_data['slug'])
            target = self.data.get('target', None)
            position = self.data.get('position', None)

            parent = None
            if self.instance.id:
                parent = Page.objects.get(id=self.instance.id).parent
            elif target:
                parent = Page.objects.get(id=target)

            new_url = Page.build_complete_slug(parent, slug)

            if Page.objects.from_complete_slug(complete_slug=new_url).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This URL is already taken by another active page.')
            return slug

    return PageForm
