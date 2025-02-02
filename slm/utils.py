import importlib
import inspect
import sys
from logging import Filter
from pprint import pformat
from rest_framework.serializers import Serializer
from django.conf import settings


PROTOCOL = getattr(settings, 'SLM_HTTP_PROTOCOL', None)


def set_protocol(request):
    global PROTOCOL
    if not PROTOCOL:
        PROTOCOL = 'https' if request.is_secure() else 'http'


def get_protocol():
    global PROTOCOL
    if PROTOCOL is not None:
        return PROTOCOL
    return (
        'https'
        if getattr(settings, 'SECURE_SSL_REDIRECT', False) else
        'http'
    )


def build_absolute_url(path, request=None):
    if path.startswith('mailto:'):
        return path
    if request:
        return request.build_absolute_uri(path)
    return f'{get_url()}/{path.lstrip("/")}'


def get_url():
    from django.contrib.sites.models import Site
    return f'{get_protocol()}://{Site.objects.get_current().domain}'


def from_email():
    from django.contrib.sites.models import Site
    return getattr(
        settings,
        'DEFAULT_FROM_EMAIL',
        f'noreply@{Site.objects.get_current().domain}'
    )


def clear_caches():
    from slm.models import Site
    from slm.models import User
    User.is_moderator.cache_clear()
    Site.is_moderator.cache_clear()


class SquelchStackTraces(Filter):

    def filter(self, record):
        record.exc_info = None
        return super().filter(record)


def to_bool(bool_str):
    if bool_str is None:
        return None
    if isinstance(bool_str, str):
        return not bool_str.lower() in ['0', 'no', 'false']
    return bool(bool_str)


def to_snake_case(string):
    snake = string
    if string:
        snake = string[0].lower()
        new = False
        for char in string[1:]:
            if char == ' ':
                new = True
            elif char.isupper() or new:
                snake += f'_{char.lower()}'
                new = False
            elif char.isalnum():
                snake += char
    return snake


def date_to_str(date_obj):
    if date_obj:
        return f'{date_obj.year}-{date_obj.month:02}-{date_obj.day:02}'
    return ''


def http_accepts(accepted_types, mimetype):
    if '*/*' in accepted_types:
        return True
    if mimetype in accepted_types:
        return True
    typ, sub_type = mimetype.split('/')
    if f'{typ}/*' in accepted_types:
        return True
    if f'*/{sub_type}' in accepted_types:
        return True
    return False


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        '''
        elif len(args) > 0:
            config = { }
            for idx, arg in enumerate(args):
                config[idx] = arg
            raise ValueError( self.__class__.__name__ + ' can only be initialized with a configuration once!', config )
        '''

        return cls._instances[cls]

    @classmethod
    def is_instantiated(cls, typ):
        return typ in cls._instances

    @classmethod
    def destroy(cls, typ):
        if typ in cls._instances:
            del cls._instances[typ]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    pass
