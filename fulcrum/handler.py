from utils import rc
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db.models import ForeignKey, ManyToManyField
from django.contrib.auth.models import User

from sandbox.blog.models import Blogpost
import schemas

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
        
        if not self.has_model():
            return rc.NOT_IMPLEMENTED
        
        attrs = self.flatten_dict(request.POST)
        #print 'attrs {0}'.format(attrs)
        
        missing_fields = []
        
        #print 'model fields:'
        for field in self.model._meta.fields + self.model._meta.many_to_many:
            #print '-- {0}:{1} required {2}'.format(field.name, type(field).__name__, field.blank==False)
            
            req = field.blank == False
            typ = type(field)
            
            if req:
                if type(field) == ForeignKey or type(field) == ManyToManyField:
                    
                    # TODO: get the object and set it explicitly
                    
                    '''
                    f_field = self.model._meta.get_field_by_name(field.name)
                    
                    if f_field[0].rel.to == User:
                        #print 'field name: {0}'.format(field.name)
                        if field.name not in attrs.keys():
                            #print 'adding user...'
                            attrs[field.name] = request.user
                        else:
                            #print 'user exists...'
                    else:
                        # TODO: how to handle other model types?
                        pass
                        '''
                else:
                    #print 'checking against attrs...'
                    if field.name not in attrs.keys() or attrs[field.name] == '':
                        #print 'appending to missing_fields'
                        #missing_fields.append((field.name, type(field).__name__))
                        pass
        
        #print 'missing_fields: {0}'.format(missing_fields)
        
        '''if len(missing_fields) > 0:
            resp = rc.BAD_REQUEST
            resp.write('\nThe following fields are required:')
            for field, typ in missing_fields:
                resp.write('\n-- {0}:{1}'.format(field, typ))
            return resp
        '''
        
        try:
            inst = self.model.objects.get(**attrs)
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            inst = self.model(**attrs)
            try:
                inst.full_clean()
            except ValidationError, e:
                #print 'Model validation error: {0}'.format(e)
                pass
            inst.save()
            return inst
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
        
    
    
class DefaultAnonymousHandler(AnonymousBaseHandler):
    pass
