import os

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.humanize.templatetags.humanize import ordinal
from django.core.exceptions import ValidationError
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from openwisp_utils.base import TimeStampedEditableModel

from .storage import OverwriteStorage


@python_2_unicode_compatible
class Location(TimeStampedEditableModel):
    name = models.CharField(_('name'), max_length=75)
    address = models.CharField(_('address'), db_index=True,
                               max_length=256, blank=True)
    geometry = models.GeometryField(_('geometry'), blank=True, null=True)

    def __str__(self):
        return self.name


def _get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    return '{0}.{1}'.format(instance.id, ext)


@python_2_unicode_compatible
class FloorPlan(TimeStampedEditableModel):
    location = models.ForeignKey('django_loci.Location')
    floor = models.SmallIntegerField(_('floor'))
    image = models.ImageField(_('image'),
                              upload_to=_get_file_path,
                              storage=OverwriteStorage(),
                              help_text=_('floor plan image'))

    class Meta:
        unique_together = ('location', 'floor')

    def __str__(self):
        return '{0} {1} {2}'.format(self.location.name,
                                    ordinal(self.floor),
                                    _('floor'))

    def delete(self, *args, **kwargs):
        path = self.image.file.name
        super(FloorPlan, self).delete(*args, **kwargs)
        os.remove(path)


class ObjectLocation(TimeStampedEditableModel):
    LOCATION_TYPES = (
        ('outdoor', _('Outdoor')),
        ('indoor', _('Indoor')),
        ('mobile', _('Mobile')),
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=36, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    type = models.CharField(choices=LOCATION_TYPES, max_length=8)
    location = models.ForeignKey('django_loci.Location', models.PROTECT,
                                 blank=True, null=True)
    floorplan = models.ForeignKey('django_loci.Floorplan', models.PROTECT,
                                  blank=True, null=True)
    indoor = models.CharField(_('indoor position'), max_length=64,
                              blank=True, null=True)

    class Meta:
        unique_together = ('content_type', 'object_id')

    def _clean_indoor_location(self):
        # skip validation if the instance does not
        # have a floorplan assigned to it yet
        if self.type != 'indoor' or not self.floorplan:
            return
        if self.location != self.floorplan.location:
            raise ValidationError(_('Invalid floorplan (belongs to a different location)'))

    def clean(self):
        self._clean_indoor_location()

    def delete(self, *args, **kwargs):
        delete_location = False
        if self.type == 'mobile':
            delete_location = True
            location = self.location
        super(ObjectLocation, self).delete(*args, **kwargs)
        if delete_location:
            location.delete()
