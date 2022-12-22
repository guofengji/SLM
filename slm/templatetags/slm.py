import os
from datetime import date, datetime, timezone
from enum import Enum
from html import unescape

from django import template
from django.conf import settings
from django.utils.translation import gettext as _
from slm.utils import to_snake_case, build_absolute_url

register = template.Library()


@register.filter(name='section_name')
def section_name(form):
    return form.section_name()


@register.filter(name='to_snake')
def to_snake(string):
    return to_snake_case(string)


@register.filter(name='arg')
def arg(arg1, arg2):
    if isinstance(arg1, list):
        return arg1 + [arg2]
    return [arg1, arg2]


@register.filter(name='to_id')
def to_id(arg1, arg2):
    if not isinstance(arg1, list):
        arg1 = [arg1]
    return '-'.join([to_snake_case(str(arg)) for arg in arg1 + [arg2] if arg])


@register.filter(name='key_value')
def key_value(dictionary, key):
    return dictionary.get(key, None)


@register.filter(name='value_filter')
def value_filter(value):
    if value is None:
        return _('empty')
    str_val = str(value)
    if str_val is None or value == '':
        return _('empty')
    return str_val


@register.filter(name='strip_ms')
def strip_ms(timestamp):
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    return ':'.join(timestamp.split(':')[0:2])


@register.filter(name='help_text')
def help_text(model, field):
    return model._meta.get_field(field).help_text


@register.filter(name='simple_utc')
def simple_utc(datetime_field):
    """
    Return a datetime string in UTC, in the format YYYY-MM-DD HH:MM

    :param datetime_field: A datetime object
    :return: formatted datetime string
    """
    if datetime_field:
        if isinstance(datetime_field, date):
            return datetime_field.strftime('%Y-%m-%d')
        return datetime_field.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')
    return ''


@register.filter(name='iso_utc')
def iso_utc(datetime_field):
    if datetime_field:
        return datetime_field.astimezone(
            timezone.utc
        ).strftime('%Y-%m-%dT%H:%MZ')
    return ''


@register.filter(name='iso_utc_full')
def iso_utc_full(datetime_field):
    if datetime_field:
        return datetime_field.astimezone(
            timezone.utc
        ).strftime('%Y-%m-%dT%H:%M:%SZ')
    return ''


@register.filter(name='multi_line')
def multi_line(text):
    if text:
        limit = 49
        lines = [line.rstrip() for line in text.split('\n')]
        limited = []
        for line in lines:
            while len(line) > limit:
                mark = limit

                # only chop on white space if we can
                for ridx, char in enumerate(reversed(line[0:limit])):
                    if not char.strip():
                        mark = limit - ridx
                        break

                limited.append(unescape(line[0:mark]))
                line = line[mark:]
            limited.append(unescape(line))
        return f'\n{" "*30}: '.join([line for line in limited if line.strip()])
    return ''


@register.filter(name='iso6709')
def iso6709(lat_lng, padding):
    if lat_lng:
        number = f'{lat_lng:.2f}'
        integer, dec = number.split('.') if '.' in number else (number, None)
        iso_frmt = f"{abs(int(integer)):0{int(padding)}}{'.' if dec else ''}{dec}"
        return f'{"+" if float(lat_lng) > 0 else "-"}{iso_frmt}'
    return ''


@register.filter(name='epsg7912')
def epsg7912(lat_lng, prec=10):
    if lat_lng:
        return precision(lat_lng/10000, prec)
    return ''


@register.filter(name='precision')
def precision(number, precision):
    if number not in {None, ''}:
        return f'{number:.{precision}f}'.rstrip('0').rstrip('.')
    return ''


@register.filter(name='precision_full')
def precision_full(alt, precision):
    if alt not in {None, ''}:
        return f'{alt:.{precision}f}'
    return ''


@register.filter(name='pos')
def pos(number):
    if number not in {None, ''}:
        if float(number) > 0:
            return f'+{number}'
        return number
    return ''


@register.filter(name='none2empty')
def none2empty(number, suffix=''):
    if number is None:
        return ''
    return f'{number}{suffix}'


@register.filter(name='enum_str')
def enum_str(value):
    if value is None:
        return ''
    if isinstance(value, Enum):
        return value.label
    return value


@register.filter(name='satellite_str')
def satellite_str(satellite_systems):
    if satellite_systems:
        return '+'.join([system.name for system in satellite_systems.all()])
    return ''


@register.filter(name='inspect')
def inspect(obj):
    from pprint import pprint
    pprint(dir(obj))


@register.filter(name='get_key')
def get_key(obj, key):
    return obj.get(key)


@register.filter(name='merge')
def merge(obj1, obj2):
    return obj1.merge(obj2)


@register.filter(name='antenna_radome')
def antenna_radome(antenna):
    spacing = max(abs(16-len(antenna.antenna_type.model)), 1)
    radome = 'NONE'
    if hasattr(antenna, 'radome_type'):
        radome = antenna.radome_type.model
    return f'{antenna.antenna_type.model}{" " * spacing}{radome}'


@register.filter(name='antenna_codelist')
def antenna_radome(antenna):
    radome = 'NONE'
    if hasattr(antenna, 'radome_type'):
        radome = antenna.radome_type.model
    return f'{antenna.antenna_type.model} {radome}'


@register.filter(name='rpad_space')
def rpad_space(text, length):
    return f'{text}{" " * (int(length) - len(str(text)))}'


@register.filter(name='file_icon')
def file_icon(file):
    subtype = ''
    if file:
        subtype = getattr(
            file,
            'mimetype',
            file if isinstance(file, str) else ''
        ).split('/')[-1]
    return getattr(
        settings,
        'SLM_FILE_ICONS',
        {}
    ).get(
        subtype,
        'bi bi-file-earmark'
    )


@register.filter(name='file_lines')
def file_lines(file):
    if file and os.path.exists(file.file.path):
        return file.file.open().read().decode().split('\n')
    return ['']


@register.filter(name='finding_class')
def finding_class(findings, line_number):
    # in json keys can't be integers and our findings context might be integers
    # or strings if its gone through a json cycle so we try both
    if findings:
        return {
            'E': 'slm-parse-error',
            'W': 'slm-parse-warning',
            'I': 'slm-parse-ignore'
        }.get(
            findings.get(
                str(line_number),
                findings.get(
                    int(line_number), [''])
            )[0]
        )
    return ''


@register.filter(name='finding_content')
def finding_content(findings, line_number):
    if findings:
        return findings.get(
            str(line_number),
            findings.get(int(line_number), [None, ''])
        )[1]
    return ''


@register.filter(name='finding_title')
def finding_title(findings, line_number):
    if findings:
        return {
            'E': 'Error',
            'W': 'Warning',
            'I': 'Ignored'
        }.get(
            findings.get(
                str(line_number),
                findings.get(int(line_number), [''])
            )[0]
        )
    return ''


@register.filter(name='split_rows')
def split_rows(iterable, row_length):
    rows = []
    row = []
    for idx, item in enumerate(iterable):
        row.append(item)
        if idx+1 % row_length == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


@register.filter(name='absolute_url')
def absolute_url(path, request=None):
    return build_absolute_url(path, request=request)


@register.filter(name='contact')
def contact(agency, ctype):
    return {
        field: getattr(agency, f'{ctype}_{field}')
        for field in [
            'name', 'phone1', 'phone2', 'fax', 'email'
        ] if getattr(agency, f'{ctype}_{field}')
    }


@register.filter(name="format_temp_stab")
def format_temp_stab(temp, temp_stab):
    temp = precision(temp, 1)
    temp_stab = precision(temp_stab, 1)
    if temp and temp_stab:
        return f'{temp} +/- {temp_stab} C'
    elif temp:
        return f'{temp} C'
    elif temp_stab:
        return f'+/- {temp_stab} C'
    return ''
