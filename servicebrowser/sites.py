import os
from django import http
from django.db import models
from servicebrowser.datastructures import EasyModel
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe

class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class DatabrowsePlugin(object):
    
    def urls( self, plugin_name, easy_instance_field ):
        """
        Given an EasyInstanceField object, returns a list of URLs for this
        plugin's views of this object. These URLs should be absolute.

        Returns None if the EasyInstanceField object doesn't get a
        list of plugin-specific URLs.
        """
        return None

    def model_index_html( self, request, model, site ):
        """
        Returns a snippet of HTML to include on the model index page.
        """
        return ''

    def model_view( self, request, model_databrowse, url ):
        """
        Handles main URL routing for a plugin's model-specific pages.
        """
        raise NotImplementedError
    
    def model_save( self, request, model_databrowse, url ):
        """
        Handles main URL routing for a plugin's model-specific pages.
        """
        raise NotImplementedError


class ModelDatabrowse(object):
    
    # -- Plugins to Enable
    plugins         = {}

    def __init__(self, model, site):
        self.model  = model
        self.site   = site

    def root( self, request, url, extension = None ):
        """
        Handles main URL routing for the servicebrowser app.
        `url` is the remainder of the URL -- e.g. 'objects/3'.
        """
        # -- Extract the type of view, and therefore the plugin to use
        if url is None:
            plugin_name = "models"
            rest_of_url = None
        else:
            # -- Get URL Remainder
            try:
                plugin_name, rest_of_url = url.split('/', 1)
            except ValueError: # need more than 1 value to unpack
                plugin_name, rest_of_url = url, None

        # -- Request Plugin to Render View based on URL value at index
        try:
            plugin = self.plugins[plugin_name]
        except KeyError:
            raise http.Http404('A plugin with the requested name does not exist.')

        return plugin.model_view( request, self, rest_of_url, extension )


class DatabrowseSite(object):
    
    def __init__(self):
        self.registry       = {} # model_class -> databrowse_class
        self.root_url       = None

    """
    Registers the given model(s) with the given databrowse site.

    The model(s) should be Model classes, not instances.

    If a databrowse class isn't given, it will use DefaultModelDatabrowse
    (the default databrowse options).

    If a model is already registered, this will raise AlreadyRegistered.
    """
    def register( self, model_or_iterable, databrowse_class=None, config = {}, **options ):
        
        # -- Check if alternate Databrowse Class was Specified
        databrowse_class = databrowse_class or DefaultModelDatabrowse

        # -- Validation
        if issubclass( model_or_iterable, models.Model ):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self.registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)
            
            # -- Register
            self.registry[model] = databrowse_class

    """
    Handles Unregistering Models from the Allowed Registry List
    """
    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if issubclass(model_or_iterable, models.Model):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self.registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self.registry[model]

    """
    Handles main URL routing for the databrowse app.

    `url` is the remainder of the URL -- e.g. 'comments/comment/'.
    """
    def root(self, request, url ):
        
        # -- Split URL to get the Root
        self.root_url = request.path[:len(request.path) - len(url)]
        
        # -- Get Remaining Request
        url = url.rstrip('/')                   # Trim trailing slash, if it exists.

        try:
            ext = str( os.path.splitext(url)[1] ).replace( '.', '' )
            
            if( ext == 'json' or ext == 'xml' or ext == 'poxml' ):
                extension   = ext
                url         = os.path.splitext(url)[0]
            else:
                extension   = None
        except:
            extension = None

        # -- Handle Request
        if url == '':
            return self.index(request)
        elif '/' in url:
            return self.model_page( request, *url.split('/', 2), **{ 'extension': extension} )

        # -- Raise Error if no matching request
        raise http.Http404('The requested databrowse page does not exist.')


    """
    Renders Default Homepage view for the Service Browser
    Passes all of the registered sites in.
    """
    def index(self, request):
        m_list = [ EasyModel(self, m) for m in self.registry.keys() ]
        return render_to_response('servicebrowser/homepage.html', {'model_list': m_list, 'root_url': self.root_url})


    """
    Handles the model-specific functionality of the databrowse site, delegating
    to the appropriate ModelDatabrowse class.

        Potential Functionlity
        - Pagination
        - Expanded Object Fields
        - How to Constrain the Queryset???
        - Different URL handling
        - Serialization Support
    """
    def model_page(self, request, app_label, model_name, rest_of_url=None, extension=None ):
        
        # -- Get the Requested Model
        model = models.get_model( app_label, model_name )

        # -- Check if Model is Empty
        if model is None:
            raise http.Http404("App %r, model %r, not found." % (app_label, model_name))
        
        # -- Verify that the Model is Registered
        try:
            databrowse_class = self.registry[model]
        except KeyError:
            raise http.Http404( "This model exists but has not been registered with databrowse." )
            
        # -- Return the Databrowse Class (likely ModelDatabrowse)
        return databrowse_class(model, self).root( request, rest_of_url, extension )


# -- Self Init Site
site = DatabrowseSite()

# -- Default Model
from servicebrowser.plugins.objects import ObjectDetailPlugin
from servicebrowser.plugins.models import ModelDetailPlugin
from servicebrowser.plugins.fieldchoices import FieldChoicePlugin

class DefaultModelDatabrowse(ModelDatabrowse):
    plugins = { 'models': ModelDetailPlugin(), 'objects': ObjectDetailPlugin(), 'fields': FieldChoicePlugin() }
    #plugins = {'objects': ObjectDetailPlugin(), 'calendars': CalendarPlugin(), 'fields': FieldChoicePlugin()}