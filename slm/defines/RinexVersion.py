from datetime import date

from django_enum import IntegerChoices
from enum_properties import p, s


class RinexVersion(IntegerChoices, s('major'), s('text'), p('published')):

    # Minor version not known

    #      Name    Label     Major Text           Published
    v2    = 2,   'RINEX 2',    2,  '2', date(year=1993, month=4, day=1)
    v3    = 3,   'RINEX 3',    3,  '3', date(year=2007, month=11, day=28)
    v4    = 4,   'RINEX 4',    4,  '4', date(year=2021, month=12, day=1)
    ###############################################################

    v2_11 = 211, 'RINEX 2.11', 2, '2.11', date(year=2012, month=6, day=26)
    v3_00 = 300, 'RINEX 3.00', 3, '3.00', date(year=2007, month=11, day=28)
    v3_01 = 301, 'RINEX 3.01', 3, '3.01', date(year=2009, month=6, day=22)
    v3_02 = 302, 'RINEX 3.02', 3, '3.02', date(year=2013, month=4, day=13)
    v3_03 = 303, 'RINEX 3.03', 3, '3.03', date(year=2017, month=1, day=25)
    v3_04 = 304, 'RINEX 3.04', 3, '3.04', date(year=2018, month=11, day=23)
    v3_05 = 305, 'RINEX 3.05', 3, '3.05', date(year=2020, month=12, day=1)
    v4_00 = 400, 'RINEX 4.00', 4, '4.00', date(year=2021, month=12, day=1)

    def major_q(self, field_name='rinex_version'):
        from django.db.models import Q
        return Q(**{
            f'{field_name}__in': [
                rv.value for rv in RinexVersion if rv.major == self.major
            ]})

    def __str__(self):
        return str(self.label)
