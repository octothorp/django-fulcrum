from django import http
from django.core import serializers
from servicebrowser.utils import serializers as sbserializers
from django.http import Http404, HttpResponse
from servicebrowser.datastructures import EasyModel
from servicebrowser.sites import DatabrowsePlugin
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
import urlparse

class ModelDetailPlugin(DatabrowsePlugin):
    
    """
    Lists all of the records in the table for that model
    """
    def model_view( self, request, model_databrowse, url, extension ):
        
        # -- Get Request into the Easy Model
        easy_model      = EasyModel( model_databrowse.site, model_databrowse.model )
        
        # -- Import Plugins
        html_snippets   = mark_safe(u'\n'.join([p.model_index_html(request, model_databrowse.model, model_databrowse.site) for p in model_databrowse.plugins.values()]))

        # -- Switch on Extension
        if extension == "json":
            data = serializers.serialize( "json", easy_model.unformatted_query_set() )
            return http.HttpResponse( data, "application/json" )
        elif extension == "xml":
            data = serializers.serialize( "xml", easy_model.unformatted_query_set() )
            return http.HttpResponse( data, "text/xml" )
        elif extension == "poxml":
            data = sbserializers.serialize( "poxml", easy_model.unformatted_query_set() )
            return http.HttpResponse( data, "text/xml" )
        else:
            return render_to_response('servicebrowser/model_detail.html', {
                'model'         : easy_model,
                'root_url'      : model_databrowse.site.root_url,
                'plugin_html'   : html_snippets,
            })