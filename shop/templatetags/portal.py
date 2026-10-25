from django import template
from django.utils.translation import get_language, gettext

register = template.Library()


@register.filter
def localize(value):
    """Translate resolved content, including nullable fields and their fallbacks."""
    if value is None:
        return ''
    # Arabic sample names are the canonical stored values. Django makes English
    # the fallback catalogue for Arabic, so keep Arabic text as-is in Arabic UI.
    if get_language() == 'ar' and any('\u0600' <= char <= '\u06ff' for char in str(value)):
        return str(value)
    return gettext(str(value))

COURSE_IMAGES = {
    'Web Development': 'html5', 'Python Programming': 'python',
    'Artificial Intelligence': 'tensorflow', 'Data Science': 'pandas',
    'Database': 'postgresql', 'React Development': 'react',
    'UI/UX Design': 'figma', 'Cybersecurity': 'shield-lock',
}


@register.simple_tag
def course_image(activity):
    """Local, licensed subject artwork; unknown categories use the portal mark."""
    if 'robot' in activity.title.casefold():
        icon = 'robot'
    else:
        icon = COURSE_IMAGES.get(activity.category.name)
    return f'shop/images/courses/{icon}.svg' if icon else 'shop/images/learning-mark.svg'
