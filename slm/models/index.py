"""
The Site Log models contain edit histories and a tree-like structure that
make complex queries (potentially) very slow. To remedy this the best and
really only option is to denormalize the data. All searchable site log fields
should be defined and indexed here.

Think of this record as a Materialized View that's defined in code to make
it RDBMS independent.

Denormalization introduces the potential for data inconsistency. If updates are
published and a corresponding SiteIndex is not created, search results will be
incorrect. This will not however break editing or site log serialization. In
the context of the rest of the software - this table should be treated as
a read-only index.

Extensions... todo
"""
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import F, OuterRef, Q, Subquery, Value
from django.db.models.functions import (
    Now,
    Cast,
    LPad,
    Concat,
    ExtractYear,
    ExtractMonth,
    Substr,
    Lower,
    ExtractDay
)
from django.utils.timezone import now
from django_enum import EnumField
from slm.defines import (
    FrequencyStandardType,
    ISOCountry,
    RinexVersion,
    SiteLogFormat,
    SLMFileType,
    GeodesyMLVersion
)
from slm.models.data import DataAvailability
from slm.models.system import (
    Antenna,
    Radome,
    Receiver,
    SatelliteSystem,
    SiteFile,
)


class SiteIndexManager(models.Manager):

    def add_index(self, site):
        existing = self.filter(site=site, begin=site.last_publish).first()
        if existing:
            return existing

        self.close_index(site)

        location = site.sitelocation_set.current(published=True)
        identification = site.siteidentification_set.current(published=True)
        antenna = site.siteantenna_set.current(published=True).filter(
            removed__isnull=True
        ).order_by('-installed').first()
        receiver = site.sitereceiver_set.current(published=True).filter(
            removed__isnull=True
        ).order_by('-installed').first()
        frequency = site.sitefrequencystandard_set.current(
            published=True
        ).filter(
            effective_end__isnull=True
        ).order_by('-effective_start').first()
        more_info = site.sitemoreinformation_set.current(published=True)

        new_index = self.create(
            site=site,
            begin=site.last_publish,
            end=None,
            latitude=location.latitude / 10000 if location else None,
            longitude=location.longitude / 10000 if location else None,
            elevation=location.elevation if location else None,
            city=location.city if location else '',
            country=location.country if location else '',
            antenna=antenna.antenna_type if antenna else None,
            radome=antenna.radome_type if antenna else None,
            receiver=receiver.receiver_type if receiver else None,
            serial_number=receiver.serial_number if receiver else '',
            firmware=receiver.firmware if receiver else '',
            frequency_standard=frequency.standard_type if frequency else None,
            domes_number=(
                identification.iers_domes_number if identification else None
            ),
            data_center=more_info.primary
        )
        if receiver:
            new_index.satellite_system.set(receiver.satellite_system.all())

        for log_format in SiteLogFormat:
            if log_format in {SiteLogFormat.JSON}:
                continue  # todo - remove
            ArchivedSiteLog.objects.from_site(site=site, log_format=log_format)

        return new_index

    def close_index(self, site):
        last = self.filter(site=site).filter(
            Q(begin__lte=site.last_publish) &
            Q(end__isnull=True) | Q(end__gt=site.last_publish)
        ).first()
        if last:
            last.end = site.last_publish
            last.save()

    def insert_index(self, begin, **kwargs):
        """
        Insert a new index into an existing index deck (i.e. between existing
        indexes).
        """
        next_index = self.get_queryset().filter(
            site=kwargs['site'],
            begin__gt=begin
        ).order_by('begin').first()
        prev_index = self.get_queryset().filter(
            site=kwargs['site'],
            begin__lt=begin
        ).order_by('-begin').first()
        kwargs.setdefault('end', next_index.begin if next_index else None)
        if prev_index:
            prev_index.end = begin
            prev_index.save()
        return self.create(begin=begin, **kwargs)


class SiteIndexQuerySet(models.QuerySet):

    def at_epoch(self, epoch=None):
        if epoch is None:
            epoch = now()
        return self.filter(
            Q(begin__lte=epoch) & (Q(end__gt=epoch) | Q(end__isnull=True))
        )

    def public(self):
        return self.filter(site__agencies__public=True)

    def availability(self):
        last_data_avail = DataAvailability.objects.filter(
            site=OuterRef('pk')
        ).order_by('-last')
        return self.annotate(
            last_data_time=Subquery(last_data_avail.values('last')[:1]),
            last_data=Now() - F('last_data_time'),
            last_rinex2=Subquery(
                last_data_avail.filter(
                    RinexVersion(2).major_q()
                ).values('last')[:1]),
            last_rinex3=Subquery(
                last_data_avail.filter(
                    RinexVersion(3).major_q()
                ).values('last')[:1]),
            last_rinex4=Subquery(
                last_data_avail.filter(
                    RinexVersion(4).major_q()
                ).values('last')[:1])
        )

    def annotate_filenames(
        self,
        name_len=None,
        field_name='filename',
        lower_case=False
    ):
        """
        Add the log names (w/o) extension as a property called filename to
        each site.

        :param name_len: If given a number, the filename will start with only
            the first name_len characters of the site name.
        :param field_name: Change the name of the annotated field.
        :param lower_case: Filenames will be lowercase if true.
        :return: A queryset with the filename annotation added.
        """
        name_str = F('site__name')
        if name_len:
            name_str = Cast(
                Substr('site__name', 1, length=name_len), models.CharField()
            )

        if lower_case:
            name_str = Lower(name_str)

        return self.annotate(
            **{
                field_name: Concat(
                    name_str,
                    Value('_'),
                    Cast(ExtractYear('begin'), models.CharField()),
                    LPad(
                        Cast(ExtractMonth('begin'), models.CharField()),
                        2,
                        fill_text=Value('0')
                    ),
                    LPad(
                        Cast(ExtractDay('begin'), models.CharField()),
                        2,
                        fill_text=Value('0')
                    )
                )
            }
        )


class SiteIndex(models.Model):

    site = models.ForeignKey(
        'slm.Site',
        on_delete=models.CASCADE,
        null=False,
        related_name='indexes'
    )

    # the point in time at which this record begins being valid
    begin = models.DateTimeField(null=False, db_index=True)

    # the point in time at which this record stops being valid
    end = models.DateTimeField(null=True, db_index=True)

    latitude = models.FloatField(db_index=True, null=True)
    longitude = models.FloatField(db_index=True, null=True)
    elevation = models.FloatField(db_index=True, null=True)

    city = models.CharField(
        default='',
        db_index=True,
        max_length=100,
        blank=True
    )
    country = EnumField(
        ISOCountry,
        null=True,
        db_index=True,
        max_length=255,
        strict=False
    )

    antenna = models.ForeignKey(Antenna, on_delete=models.PROTECT, null=True)
    radome = models.ForeignKey(Radome, on_delete=models.PROTECT, null=True)
    receiver = models.ForeignKey(Receiver, on_delete=models.PROTECT, null=True)

    serial_number = models.CharField(
        db_index=True,
        max_length=100,
        blank=True,
        default=''
    )
    firmware = models.CharField(
        db_index=True,
        max_length=100,
        blank=True,
        default=''
    )

    frequency_standard = EnumField(
        FrequencyStandardType,
        null=True,
        db_index=True,
        strict=False,
        max_length=100
    )

    domes_number = models.CharField(
        db_index=True,
        max_length=100,
        blank=True,
        default=''
    )

    satellite_system = models.ManyToManyField(SatelliteSystem)

    data_center = models.CharField(
        db_index=True,
        max_length=100,
        blank=True,
        default=''
    )

    objects = SiteIndexManager.from_queryset(SiteIndexQuerySet)()

    class Meta:
        ordering = ('-begin',)
        index_together = (('begin', 'end'), ('site', 'begin', 'end'),)
        unique_together = (('site', 'begin'), ('site', 'end'))


class ArchivedSiteLogManager(models.Manager):
    """
    This manager is responsible for mediating access to serialized site logs.
    Most frequently it will be fetching logs that match the given criteria from
    disk, but it might also generate a log from the edit stack if an archived
    file does not exist.
    """

    def from_index(self, index, log_format):
        from slm.api.serializers import SiteLogSerializer
        if index:
            file = index.files.filter(log_format=log_format).first()
            if file:
                return file
            return self.model.objects.create(
                site=index.site,
                log_format=log_format,
                index=index,
                timestamp=index.begin,
                mimetype=log_format.mimetype,
                file_type=SLMFileType.SITE_LOG,
                name=index.site.get_filename(
                    log_format=log_format,
                    epoch=index.begin
                ),
                file=ContentFile(
                    SiteLogSerializer(
                        instance=index.site,
                        epoch=index.begin
                    ).format(log_format).encode('utf-8'),
                    name=index.site.get_filename(
                        log_format=log_format,
                        epoch=index.begin
                    )
                )
            )
        return None

    def from_site(self, site, log_format=SiteLogFormat.LEGACY, epoch=None):
        index = SiteIndex.objects.filter(
            site=site
        ).at_epoch(epoch=epoch).first()
        if index:
            return self.from_index(index, log_format=log_format)
        return None


class ArchivedSiteLogQuerySet(models.QuerySet):

    def annotate_filenames(
        self,
        name_len=None,
        field_name='filename',
        lower_case=False
    ):
        """
        Add the log names (w/o) extension as a property called filename to
        each site.

        :param name_len: If given a number, the filename will start with only
            the first name_len characters of the site name.
        :param field_name: Change the name of the annotated field.
        :param lower_case: Filenames will be lowercase if true.
        :return: A queryset with the filename annotation added.
        """
        name_str = F('site__name')
        if name_len:
            name_str = Cast(
                Substr('site__name', 1, length=name_len), models.CharField()
            )

        if lower_case:
            name_str = Lower(name_str)

        return self.annotate(
            **{
                field_name: Concat(
                    name_str,
                    Value('_'),
                    Cast(ExtractYear('index__begin'), models.CharField()),
                    LPad(
                        Cast(ExtractMonth('index__begin'), models.CharField()),
                        2,
                        fill_text=Value('0')
                    ),
                    LPad(
                        Cast(ExtractDay('index__begin'), models.CharField()),
                        2,
                        fill_text=Value('0')
                    )
                )
            }
        )


class ArchivedSiteLog(SiteFile):

    SUB_DIRECTORY = 'archive'

    index = models.ForeignKey(
        SiteIndex,
        on_delete=models.CASCADE,
        related_name='files'
    )

    name = models.CharField(max_length=50)

    objects = ArchivedSiteLogManager.from_queryset(ArchivedSiteLogQuerySet)()

    class Meta:
        unique_together = ('index', 'log_format')
