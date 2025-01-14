from rest_framework.serializers import DateTimeField
from dateutil import parser
from django.utils import timezone
from datetime import timezone, datetime, date, time
from django.conf import settings
from django.utils.translation import gettext as _


class SLMDateTimeField(DateTimeField):

    default_error_messages = {
        'invalid': _(
            'Unable to interpret datetime, please use format: {format}.'
        ),
        'parse': _(
            'Please use format: {format}: {error}'
        )
    }

    """
    A much more lenient datetime field that uses dateutil to parse. This field
    differs from the vanilla DRF DateTimeField in several ways:
    
    1) dateutil.parser is used to parse incoming strings. This is very lenient.
    2) Values that are just dates default to default_time if it is set, and
        fail otherwise.
    3) The timezone is set to UTC unless otherwise given.
    
    :param default_time: Use this time for incoming values that are just dates.
        defaults to midnight.
    :param default_timezone: This is the output timezone - defaults to UTC.
    :param kwargs: kwargs for DRF base classes.
    """

    default_time = time(hour=0, minute=0, second=0)

    def __init__(
            self,
            default_time=default_time,
            default_timezone=timezone.utc,
            **kwargs
    ):
        self.default_time = default_time
        super().__init__(default_timezone=default_timezone, **kwargs)

    def default_timezone(self):
        return timezone.utc if settings.USE_TZ else None

    def to_internal_value(self, value):

        if isinstance(value, date) and not isinstance(value, datetime):
            # assume midnight
            if not self.default_time:
                self.fail('date')
            value = datetime.combine(value, self.default_time)

        if isinstance(value, datetime):
            return self.enforce_timezone(value)

        try:
            parsed = parser.parse(value)
            if parsed is not None:
                return self.enforce_timezone(parsed)
        except parser.ParserError as pe:
            self.fail('parse', format='CCYY-MM-DDThh:mmZ', error=str(pe))
        except (ValueError, TypeError):
            pass

        self.fail('invalid', format='CCYY-MM-DDThh:mmZ')
