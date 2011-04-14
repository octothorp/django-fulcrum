from utils import rc
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db.models import ForeignKey, ManyToManyField
from django.contrib.auth.models import User
from django.http import HttpResponse
from fulcrum import log, schemas

typemapper = { }

class HandlerMetaClass(type):
    """
    Metaclass that keeps a registry of class -> handler
    mappings.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        
        if hasattr(new_cls, 'model'):
            typemapper[new_cls] = (new_cls.model, new_cls.is_anonymous)
        
        return new_cls

class BaseHandler(object):
    """
    Basehandler that gives you CRUD for free.
    You are supposed to subclass this for specific
    functionality.
    
    All CRUD methods (`read`/`update`/`create`/`delete`)
    receive a request as the first argument from the
    resource. Use this for checking `request.user`, etc.
    """
    __metaclass__ = HandlerMetaClass
    
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    anonymous = is_anonymous = False
    exclude = ( 'id', )
    fields =  ( )
    
    def flatten_dict(self, dct):
        return dict([ (str(k), dct.get(k)) for k in dct.keys() ])
    
    def has_model(self):
        return hasattr(self, 'model')
    
    def value_from_tuple(tu, name):
        for int_, n in tu:
            if n == name:
                return int_
        return None
    
    def exists(self, **kwargs):
        if not self.has_model():
            raise NotImplementedError
        
        try:
            self.model.objects.get(**kwargs)
            return True
        except self.model.DoesNotExist:
            return False
    
    def read(self, request, *args, **kwargs):
        if not self.has_model():
            return rc.NOT_IMPLEMENTED

        pkfield = self.model._meta.pk.name

        if pkfield in kwargs:
            try:
                return self.model.objects.get(pk=kwargs.get(pkfield))
            except ObjectDoesNotExist:
                return rc.NOT_FOUND
            except MultipleObjectsReturned: # should never happen, since we're using a PK
                return rc.BAD_REQUEST
        else:
            return self.model.objects.filter(*args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        if not self.has_model():
            return rc.NOT_IMPLEMENTED
        
        attrs = self.flatten_dict(request.POST)
        
        try:
            inst = self.model.objects.get(**attrs)
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            inst = self.model(**attrs)
            inst.save()
            return inst
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
    
    def update(self, request, *args, **kwargs):
        # TODO: This doesn't work automatically yet.
        return rc.NOT_IMPLEMENTED
    
    def delete(self, request, *args, **kwargs):
        if not self.has_model():
            raise NotImplementedError

        try:
            inst = self.model.objects.get(*args, **kwargs)

            inst.delete()

            return rc.DELETED
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            return rc.NOT_HERE
        
class AnonymousBaseHandler(BaseHandler):
    """
    Anonymous handler.
    """
    is_anonymous = True
    allowed_methods = ('GET',)

class DefaultHandler(BaseHandler):
    """
    Default handler.
    """
    __metaclass__ = HandlerMetaClass
    
    anonymous = 'DefaultAnonymousHandler'
    
    def __init__(self, model):
        self.model = model
        self.fields = tuple([f.name for f in self.model._meta.fields])
        
    
    def create(self, request, *args, **kwargs):
        """
        Default create implementation. Will only validate if all required fields are supplied.
        Related object fields require a primary_key to an object or list of objects that already
        exist in the database.
        """
        log.debug('create()')
        
        if not self.has_model():
            return rc.NOT_IMPLEMENTED
        
        attrs = self.flatten_dict(request.POST)
        
        for f in self.model._meta.local_fields:
            required = f.blank == False
            if required and f.name in attrs:
                
                if type(f) == ForeignKey:
                    log.debug('ForeignKey field...')
                    try:
                        obj = f.rel.to.objects.get(pk=attrs[f.name])
                        attrs[f.name] = obj
                    except ObjectDoesNotExist, e:
                        error_msg = 'ObjectDoesNotExist: {0}'.format(e)
                        log.debug(error_msg)
                        return HttpResponse(error_msg)
                elif type(f) == ManyToManyField:
                    log.debug('ManyToMany field...')
                    try:
                        objs = f.rel.to.objects.filter(pk=attrs[f.name])
                        attrs[f.name] = objs
                        # TODO: figure out how to set manytomany on a new model
                    except ObjectDoesNotExist, e:
                        error_msg = 'ObjectDoesNotExist: {0}'.format(e)
                        log.debug(error_msg)
                        return HttpResponse(error_msg)
        
        log.debug('POST attrs" {0}'.format(attrs))
        
        try:
            inst = self.model.objects.get(**attrs)
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            inst = self.model(**attrs)
            try:
                inst.full_clean()
            except ValidationError, e:
                error_msg = str(e)
                log.debug(error_msg)
                return HttpResponse(error_msg)
            inst.save()
            return inst
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
        
    
    
class DefaultAnonymousHandler(AnonymousBaseHandler):
    pass
