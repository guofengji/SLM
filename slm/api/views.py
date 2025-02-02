from django.http import FileResponse
from django.utils.translation import gettext as _
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from rest_framework import mixins, viewsets, renderers
from slm.models import ArchivedSiteLog, SiteIndex
from slm.defines import SiteLogFormat
from slm.api.filter import SLMDateTimeFilter, InitialValueFilterSet
from datetime import datetime


class LegacyRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """
    media_type = SiteLogFormat.LEGACY.mimetype
    format = SiteLogFormat.LEGACY


class GeodesyMLRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to GeodesyML format.
    """
    media_type = SiteLogFormat.GEODESY_ML.mimetype
    format = SiteLogFormat.GEODESY_ML


class JSONRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to GeodesyML format.
    """
    media_type = SiteLogFormat.JSON.mimetype
    format = SiteLogFormat.JSON


class BaseSiteLogDownloadViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    renderer_classes = [LegacyRenderer, GeodesyMLRenderer]

    site = None

    lookup_field = 'site__name'
    lookup_url_kwarg = 'site'

    queryset = SiteIndex.objects.all()

    class SiteIndexFilter(InitialValueFilterSet):

        epoch = SLMDateTimeFilter(
            method='at_epoch',
            initial=lambda: datetime.now(),
            help_text=_(
                'Get the log that was active at this given date or datetime.'
            )
        )

        name_len = filters.NumberFilter(
            method='noop',
            help_text=_(
                'The number of characters to include in the filename from the '
                'start of the 9 character site name.'
            )
        )

        lower_case = filters.BooleanFilter(
            method='noop',
            help_text=_('If true filename will be lowercase.')
        )

        def at_epoch(self, queryset, name, value):
            return queryset.filter(
                Q(begin__lte=value) &
                (Q(end__isnull=True) | Q(end__gt=value))
            )

        def noop(self, queryset, **_):
            return queryset

        class Meta:
            model = SiteIndex
            fields = ['name_len', 'epoch', 'lower_case']

    filter_backends = (DjangoFilterBackend,)
    filterset_class = SiteIndexFilter

    def get_format_suffix(self, **kwargs):
        return SiteLogFormat(super().get_format_suffix(**kwargs))

    def retrieve(self, request, *args, **kwargs):
        """
        Download the site log rendered in the specified format - preferencing
        the HTTP_ACCEPTS header over the format parameter. In most cases
        from_site will fetch the archived log from disk, but if a format that
        was not previously rendered is requested from_site might first create
        a new ArchivedSiteLog. If no index is found and allow_unpublished is
        true a new site log will be rendered from the current HEAD state.

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        index = self.get_object()
        return FileResponse(
            ArchivedSiteLog.objects.from_index(
                index=index,
                log_format=request.accepted_renderer.format
            ).file,
            filename=index.site.get_filename(
                log_format=request.accepted_renderer.format,
                epoch=index.begin,
                name_len=request.GET.get('name_len', 9),
                lower_case=request.GET.get('lower_case', False)
            )
        )
