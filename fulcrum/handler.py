from utils import rc
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db.models import ForeignKey, ManyToManyField
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseBadRequest
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
        return dict([ (str(k), dct.getlist(k)) for k in dct.keys() ])
    
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
        
        log.debug('request.POST" {0}'.format(request.POST))
        #dct = request.POST
        #attrs = dict([ (str(k), dct.getlist(k)) for k in dct.keys() ])
        attrs = self.flatten_dict(request.POST)
        log.debug('PRE attrs" {0}'.format(attrs))
        for k in attrs.keys():
            if len(attrs[k]) == 1:
                attrs[k] = attrs[k][0]
        
        log.debug('PRE PRE attrs" {0}'.format(attrs))
        
        m2mobjs = {}
        for f in self.model._meta.local_fields + self.model._meta.many_to_many:
            
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
                        return HttpResponseBadRequest(error_msg)
                elif type(f) == ManyToManyField:
                    log.debug('ManyToMany field...')
                    try:
                        m2mobjs[f.name] = f.rel.to.objects.filter(pk__in=attrs[f.name])
                        log.debug('-- m2m len: {0}'.format(len(m2mobjs[f.name])))
                        log.debug('-- attrs len: {0}'.format(len(attrs[f.name])))
                                  
                        if len(m2mobjs[f.name]) != len(attrs[f.name]):
                            error_msg = 'ObjectDoesNotExist: A ManyToMany primary_key value failed to return an object.'
                            log.debug(error_msg)
                            return HttpResponseBadRequest(error_msg)
                        log.debug('-- m2mobjs: {0}'.format(m2mobjs[f.name]))
                        del attrs[f.name] # passing this into model(**attrs) throws an error
                    except ObjectDoesNotExist, e:
                        error_msg = 'ObjectDoesNotExist: {0}'.format(e)
                        log.debug(error_msg)
                        return HttpResponseBadRequest(error_msg)
            elif required and f.name not in attrs:
                error_msg = 'Required field {0} not found.'.format(f.name)
                log.debug(error_msg)
                return HttpResponseBadRequest(error_msg)
        
        log.debug('POST attrs" {0}'.format(attrs))
        
        try:
            inst = self.model.objects.get(**attrs)
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            
            # instantiate model and validate
            inst = self.model(**attrs)
            try:
                inst.full_clean()
            except ValidationError, e:
                error_msg = str(e)
                log.debug(error_msg)
                return HttpResponseBadRequest(error_msg)
            inst.save()
            
            # add M2M related field objs
            if len(m2mobjs):
                for k, v in m2mobjs.items():
                    log.debug('k:v = {0}:{1}'.format(k, v))
                    f = getattr(inst, k)
                    for val in v:
                        try:
                            f.add(val)
                            inst.save()
                        except:
                            error_msg = 'Error adding {0} to {1} {2} field'.format(val, inst, f)
                            log.debug(error_msg)
                            return HttpResponseBadRequest(error_msg)
            
            try:
                # validate once more...
                inst.full_clean()
            except ValidationError, e:
                error_msg = str(e)
                log.debug(error_msg)
                return HttpResponseBadRequest(error_msg)
            
            return inst
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
        
    
    
class DefaultAnonymousHandler(DefaultHandler):
    is_anonymous = True
    allowed_methods = ('GET',)


class BaseArbitraryHandler(object):
    
    __metaclass__ = HandlerMetaClass
    
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    anonymous = is_anonymous = False
    exclude = ( 'id', )
    fields =  ( )
    
    def read(self, request, *args, **kwargs):
        return 'You must implement read method in your custom handler'
    
    def create(self, request, *args, **kwargs):
        return 'You must implement create method in your custom handler'
    
    def update(self, request, *args, **kwargs):
        return 'You must implement update method in your custom handler'
    
    def delete(self, request, *args, **kwargs):
        return 'You must implement delete method in your custom handler'
    
class BaseAnonymouseArbitraryHandler(BaseArbitraryHandler):
    is_anonymous = True
    allowed_methods = ('GET')
