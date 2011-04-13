import os
from django import http
from django.db import models
from django.shortcuts import render_to_response
from django.utils.functional import update_wrapper
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.template import RequestContext
from fulcrum.datastructures import EasyModel
from fulcrum.authentication import NoAuthentication
from fulcrum.handler import DefaultHandler, DefaultAnonymousHandler
from fulcrum.resource import Resource
from fulcrum import log
from exceptions import Exception, KeyError


class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class FulcrumSite(object):
    """
    Default fulcrum site.
    """
    
    def __init__(self, name=None, app_name='fulcrum', authentication=None):
        if name is None: self.name = 'fulcrum'
        else: self.name = name
        self.app_name = app_name
        self.registry = {}
        self.authentication = authentication or NoAuthentication() # default authentication for all resources
    
    
    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        #TODO: implement permissions check
        return True
    
    
    def register(self, model, handler_class=None, name=None, authentication=None, **options):
        """
        Register a resource.
        """
        if handler_class:
            handler = handler_class()
        else:
            if authentication:
                handler = DefaultHandler(model)
            else:
                handler = DefaultAnonymousHandler(model)
        authentication = authentication or self.authentication
        resource = Resource(handler, self, name, authentication)
        
        if resource.name in self.registry:
            raise AlreadyRegistered('The resource {0} is already registered'.format(resource.name))
        self.registry[resource.name] = resource
    
        
    def unregister(self, resource):
        """
        Unregister a resource.
        """
        
        if resource.name not in self.registry:
            raise NotRegistered('The resource {0} has not been registered'.format(resource.name))
        del self.registry[resource.name]
    
    
    def get_resource_list(self):
        return self.registry.keys()
    
    def get_resource_by_model(self, model):
        """
        Get a resource by model.
        """
        for k, v in self.registry.items():
            if model == v.model:
                return v
        return None
    
    
    def fulcrum_view(self, view, cacheable=False):
        """
        Decorator to create a fulcrum view attached to this ``FulcrumSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.
        
        By default, fulcrum_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                return self.login(request)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)
    
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.fulcrum_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)
            
        urlpatterns = patterns('',
            url(r'^$', # root
                wrap(self.index),
                name='fulcrum_index'),
            
            url(r'^(?P<resource_name>\w+)$', # ex: resource_name
                wrap(self.resource_data_format),
                name='fulcrum_resource_data_format'),
            
            url(r'^(?P<resource_name>\w+)/$', # ex: resource_name/
                wrap(self.resource_data_format),
                name='fulcrum_resource_data_format'),
            
            url(r'^(?P<resource_name>\w+)\.(?P<format>\w+)$', # ex: resource_name.json
                wrap(self.resource_data_format),
                name='fulcrum_resource_data_format'),
            
            url(r'^(?P<resource_name>\w+)/api$', # ex: resource_name/api
                wrap(self.resource_api),
                name='fulcrum_resource_api'),
            
            url(r'^(?P<resource_name>\w+)/schema\.(?P<format>\w+)$', # ex: resource_name/schema.json
                wrap(self.resource_schema),
                name='fulcrum_resource_schema'),
            
            url(r'^(?P<resource_name>\w+)/(?P<primary_key>\w+)$', # ex: resource_name/1
                wrap(self.object_data_format),
                name='fulcrum_object_data_format'),
            
            url(r'^(?P<resource_name>\w+)/(?P<primary_key>\w+)\.(?P<format>\w+)$', # ex: resource_name/1.json
                wrap(self.object_data_format),
                name='fulcrum_object_data_format'),
        )
        
        return urlpatterns
    
    
    def urls(self):
        return self.get_urls(), self.app_name, self.name
    urls = property(urls)
    
    
    def index(self, request):
        """
        Renders index page view for fulcrum. Lists all registered resources.
        """
        
        log.debug('index()')
        
        r_list = [ self.registry[key] for key in self.registry.keys() ]
        return render_to_response('fulcrum/homepage.html', { 'resource_list': r_list })
        
    
    def login(self, request):
        return http.HttpResponse('login')
    
        
    def resource_data_format(self, request, resource_name, format='html', *args, **kwargs):
        """
        Resource data
        """
        
        log.debug('resource_data_format(): {0}'.format(format))
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            error_msg = "Sorry, but no resource with the name <span class='loud'>{0}</span> has been registered with Fulcrum.".format(resource_name)
            return render_to_response('fulcrum/404_fulcrum.html',
                                      { 'error_msg': error_msg },
                                      context_instance=RequestContext(request))
        
        return resource(request, emitter_format=format)
    
    
    def resource_api(self, request, resource_name, *args, **kwargs):
        """
        Resource API handler
        """
        
        log.debug('resource_api()')
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            error_msg = "Sorry, but no resource with the name <span class='loud'>{0}</span> has been registered with Fulcrum.".format(resource_name)
            return render_to_response('fulcrum/404_fulcrum.html',
                                      { 'error_msg': error_msg },
                                      context_instance=RequestContext(request))
        
        
        protocol = request.META['SERVER_PROTOCOL'].split('/')[0].lower()
        host = request.META['HTTP_HOST']
        path_info = request.META['PATH_INFO'].lstrip('/').rstrip('/api')
        example_uri = '{0}://{1}/{2}/pk'.format(protocol, host, path_info)
        
        return render_to_response('fulcrum/resource_api.html',
                                  { 'resource': resource, 'example_uri': example_uri },
                                  context_instance=RequestContext(request))
    
        
    def resource_schema(self, request, resource_name, format, *args, **kwargs):
        """
        Resource schema handler
        """
        
        log.debug('resource_schema()')
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            error_msg = "Sorry, but no resource with the name <span class='loud'>{0}</span> has been registered with Fulcrum.".format(resource_name)
            return render_to_response('fulcrum/404_fulcrum.html',
                                      { 'error_msg': error_msg },
                                      context_instance=RequestContext(request))
            #raise http.Http404("This resource has not been registered with fulcrum.")
        
        return resource.get_schema_view(format)
        
    
    def object_data_format(self, request, resource_name, primary_key, format='html', *args, **kwargs):
        """
        Object data
        """
        
        log.debug('object_data_format()')
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            error_msg = "Sorry, but no resource with the name <span class='loud'>{0}</span> has been registered with Fulcrum.".format(resource_name)
            return render_to_response('fulcrum/404_fulcrum.html',
                                      { 'error_msg': error_msg },
                                      context_instance=RequestContext(request))
        
        if format == 'html':
            try:
                object = resource.object_by_pk(primary_key)
            except:
                error_msg = "Sorry, but Fulcrum can't find an object with a primary key of <span class='loud'>{0}</span>.".format(primary_key)
                return render_to_response('fulcrum/404_fulcrum.html',
                                          { 'error_msg': error_msg },
                                          context_instance=RequestContext(request))
            return render_to_response('fulcrum/object_detail.html',
                                      { 'object': object },
                                      context_instance=RequestContext(request))
        else:
            return resource(request, pk=primary_key, emitter_format=format)
            
# Create Fulcrum instance        
site = FulcrumSite()
