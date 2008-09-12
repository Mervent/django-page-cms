from django import template
from ..pages.models import Language, Content, Page, has_page_permission, has_page_add_permission
register = template.Library()

@register.inclusion_tag('menu.html', takes_context=True)
def show_menu(context, page, url='/'):
    children = page.get_children_cached()
    request = context['request']
    if 'current_page' in context:
        current_page = context['current_page']
    return locals()

@register.inclusion_tag('sub_menu.html', takes_context=True)
def show_sub_menu(context, page, url='/'):
    root = page.get_root()
    children = root.get_children_cached()
    request = context['request']
    if 'current_page' in context:
        current_page = context['current_page']
    return locals()
    
@register.inclusion_tag('pages/admin_menu.html', takes_context=True)
def show_admin_menu(context, page, url='/admin/pages/page/', level=None):
    children = page.get_children_cached()
    request = context['request']
    has_permission = has_page_permission(request, page)
    if has_permission:
        if level is None:
            level = 0
        else:
            level = level+2
    return locals()

@register.filter
def has_permission(page, request):
    return has_page_permission(request, page)

@register.inclusion_tag('pages/content.html', takes_context=True)
def show_content(context, page, content_type):
    l = Language.get_from_request(context['request'])
    request = context['request']
    c = Content.get_content(page, l, content_type, True)
    if c:
        return {'content':c}
    return {'content':''}

def do_placeholder(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, page, name, widget = token.split_contents()
    except ValueError:
        msg = '%r tag requires three arguments' % token.contents[0]
        raise template.TemplateSyntaxError(msg)
    return PlaceholderNode(page, name, widget)


class PlaceholderNode(template.Node):

    def __init__(self, name, page, widget):
        self.page = page
        self.name = name
        self.widget = widget

    def render(self, context):
        if not 'request' in context or not self.page in context:
            return ''
        l = Language.get_from_request(context['request'])
        request = context['request']
        c = Content.get_content(context[self.page], l, self.name, True)
        if c:
            return c
        
    def __repr__(self):
        return "<Placeholder Node: %s>" % self.name

register.tag('placeholder', do_placeholder)
