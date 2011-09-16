"""
These classes are light wrappers around Django's database API that provide
convenience functionality and permalink functions for the databrowse app.
"""

from django.db import models
from django.utils import formats
from django.utils.text import capfirst
from django.utils.encoding import smart_unicode, smart_str, iri_to_uri
from django.utils.safestring import mark_safe
from django.db.models.query import QuerySet
from django.db.models import CharField, ForeignKey, ManyToManyField
from fulcrum import log

EMPTY_VALUE = '(None)'
DISPLAY_SIZE = 100

class EasyModel(object):
    def __init__(self, resource, model):
        self.resource = resource
        self.model = model
        self.verbose_name = model._meta.verbose_name
        self.verbose_name_plural = model._meta.verbose_name_plural

    def __repr__(self):
        return '<EasyModel for %s>' % smart_str(self.model._meta.object_name)

    def objects(self, **kwargs):
        return self.get_query_set().filter(**kwargs)

    def get_query_set(self):
        easy_qs = self.model._default_manager.get_query_set()._clone(klass=EasyQuerySet)
        easy_qs._easymodel = self
        return easy_qs

    def object_by_pk(self, pk):
        return EasyInstance(self, self.model._default_manager.get(pk=pk))

    def sample_objects(self):
        for obj in self.model._default_manager.all()[:3]:
            yield EasyInstance(self, obj)

    def field(self, name):
        try:
            f = self.model._meta.get_field(name)
        except models.FieldDoesNotExist:
            return None
        return EasyField(self, f)

    def fields(self):
        return [EasyField(self, f) for f in (self.model._meta.fields + self.model._meta.many_to_many)]

class EasyField(object):
    def __init__(self, easy_model, field):
        self.model, self.field = easy_model, field
        self.name = self.field.name
        self.type = self.get_type()
        self.max_length = self.field.max_length
        self.description = self.get_description()
        self.null = self.field.null
        self.blank = self.field.blank

    def __repr__(self):
        return smart_str(u'<EasyField for %s.%s>' % (self.model.model._meta.object_name, self.field.verbose_name))
    
    def get_type(self):
        if type(self.field) == ForeignKey or type(self.field) == ManyToManyField:
            f_field = self.model.model._meta.get_field_by_name(self.field.name)
            resource = self.model.resource.site.get_resource_by_model(f_field[0].rel.to)
            if resource is None or resource.name not in self.model.resource.site.get_resource_list():
                return [(f_field[0].rel.to.__name__, None)]
            else:
                return [(f_field[0].rel.to.__name__, '%s/api' % resource.name)]
        else:
            return [(self.field.get_internal_type(), None)]
    
    def get_description(self):
        if type(self.field) == ForeignKey or type(self.field) == ManyToManyField:
            f_field = self.model.model._meta.get_field_by_name(self.field.name)
            if len(f_field[0].rel.to.__doc__):
                return f_field[0].rel.to.__doc__
            else:
                return 'No description available'
        elif type(self.field) == CharField:
            if self.max_length > 1:
                return 'String (up to %s characters)' % self.max_length
            return 'String (up to %s character)' % self.max_length
        else:
            return self.field.description
        
    def has_choices(self):
        return len(self.field.choices) > 0

    def choices(self):
        for value, label in self.field.choices:
            yield EasyChoice(self.model, self, value, label)
            

class EasyChoice(object):
    def __init__(self, easy_model, field, value, label):
        self.model, self.field = easy_model, field
        self.value, self.label = value, label

    def __repr__(self):
        return smart_str(u'<EasyChoice for %s.%s>' % (self.model.model._meta.object_name, self.field))

class EasyInstance(object):
    def __init__(self, easy_model, instance):
        self.model, self.instance = easy_model, instance

    def __repr__(self):
        return smart_str(u'<EasyInstance for %s (%s)>' % (self.model.model._meta.object_name, self.instance._get_pk_val()))

    def __unicode__(self):
        val = smart_unicode(self.instance)
        if len(val) > DISPLAY_SIZE:
            return val[:DISPLAY_SIZE] + u'...'
        return val

    def __str__(self):
        return self.__unicode__().encode('utf-8')
        
    def url(self):
        return mark_safe('%s/%s' % (self.model.resource.name, self.pk()))

    def pk(self):
        return self.instance._get_pk_val()

    def fields(self):
        """
        Generator that yields EasyInstanceFields for each field in this
        EasyInstance's model.
        """
        for f in self.model.model._meta.fields + self.model.model._meta.many_to_many:
            yield EasyInstanceField(self.model, self, f)

    def related_objects(self):
        """
        Generator that yields dictionaries of all models that have this
        EasyInstance's model as a ForeignKey or ManyToManyField, along with
        lists of related objects.
        """
        for rel_object in self.model.model._meta.get_all_related_objects() + self.model.model._meta.get_all_related_many_to_many_objects():
            resource = self.model.resource.site.get_resource_by_model(rel_object.model)
            if resource is None or resource.name not in self.model.resource.site.get_resource_list():
                continue
            em = EasyModel(resource, rel_object.model)
            yield {
                'model': em,
                'related_field': rel_object.field.verbose_name,
                'object_list': [EasyInstance(em, i) for i in getattr(self.instance, rel_object.get_accessor_name()).all()],
            }

class EasyInstanceField(object):
    def __init__(self, easy_model, instance, field):
        self.model, self.field, self.instance = easy_model, field, instance
        self.raw_value = getattr(instance.instance, field.name)

    def __repr__(self):
        return smart_str(u'<EasyInstanceField for %s.%s>' % (self.model.model._meta.object_name, self.field.name))

    def values(self):
        """
        Returns a list of values for this field for this instance. It's a list
        so we can accomodate many-to-many fields.
        """
        # This import is deliberately inside the function because it causes
        # some settings to be imported, and we don't want to do that at the
        # module level.
        if self.field.rel:
            if isinstance(self.field.rel, models.ManyToOneRel):
                objs = getattr(self.instance.instance, self.field.name)
            elif isinstance(self.field.rel, models.ManyToManyRel): # ManyToManyRel
                return list(getattr(self.instance.instance, self.field.name).all())
        elif self.field.choices:
            objs = dict(self.field.choices).get(self.raw_value, EMPTY_VALUE)
        elif isinstance(self.field, models.DateField) or isinstance(self.field, models.TimeField):
            if self.raw_value:
                if isinstance(self.field, models.DateTimeField):
                    objs = capfirst(formats.date_format(self.raw_value, 'DATETIME_FORMAT'))
                elif isinstance(self.field, models.TimeField):
                    objs = capfirst(formats.time_format(self.raw_value, 'TIME_FORMAT'))
                else:
                    objs = capfirst(formats.date_format(self.raw_value, 'DATE_FORMAT'))
            else:
                objs = EMPTY_VALUE
        elif isinstance(self.field, models.BooleanField) or isinstance(self.field, models.NullBooleanField):
            objs = {True: 'Yes', False: 'No', None: 'Unknown'}[self.raw_value]
        else:
            objs = self.raw_value
        return [objs]

    def urls(self):
        "Returns a list of (value, URL) tuples."
        
        if self.field.rel:
            resource = self.model.resource.site.get_resource_by_model(self.field.rel.to)
            
            if resource and resource.name in self.model.resource.site.get_resource_list():
                lst = []
                for value in self.values():
                    url = mark_safe('%s/%s' % (resource.name, iri_to_uri(value._get_pk_val())))
                    lst.append((smart_unicode(value), url))
            else:
                lst = [(value, None) for value in self.values()]
        elif self.field.choices:
            lst = []
            for value in self.values():
                # TODO: create a fields page to handle long lists of field choices
                url = None
                lst.append((value, url))
        elif isinstance(self.field, models.URLField):
            val = self.values()[0]
            lst = [(val, iri_to_uri(val))]
        else:
            lst = [(self.values()[0], None)]
        return lst

class EasyQuerySet(QuerySet):
    """
    When creating (or cloning to) an `EasyQuerySet`, make sure to set the
    `_easymodel` variable to the related `EasyModel`.
    """
    def iterator(self, *args, **kwargs):
        for obj in super(EasyQuerySet, self).iterator(*args, **kwargs):
            yield EasyInstance(self._easymodel, obj)

    def _clone(self, *args, **kwargs):
        c = super(EasyQuerySet, self)._clone(*args, **kwargs)
        c._easymodel = self._easymodel
        return c
