from django import http
from django.core import serializers
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseServerError, HttpResponseForbidden
from servicebrowser.datastructures import EasyModel
from servicebrowser.sites import DatabrowsePlugin
from servicebrowser.utils import serializers as sbserializers
from django.shortcuts import render_to_response
from django.template import RequestContext
import urlparse

from django.forms import ModelForm


class ObjectDetailPlugin( DatabrowsePlugin ):
    
    """
    Defines a view for a specific object
    """
    def model_view( self, request, model_databrowse, url, extension ):
        
        #  -- If the object ID wasn't provided, redirect to the model page, which is one level up.
        if url is None:
            return http.HttpResponseRedirect( urlparse.urljoin(request.path, '../') )
        
        # -- Assign
        easy_model  = EasyModel( model_databrowse.site, model_databrowse.model )
        
        # -- If POST, save
        if( request.method == "POST" ):
            
            if request.user.is_authenticated():

                if extension == "json" or extension == "xml":
    
                    # -- Try to get Data
                    try:
                        data = unicode( request.POST[ 'data' ] ).encode( 'utf-8' )
                    except:
                        return HttpResponseBadRequest()
                        
                    # -- Deserialize Data and Save
                    try:
                        for obj in serializers.deserialize( extension, data ):
                            obj.save()
                    except:
                        return HttpResponseServerError()
    
                else:
    
                    # -- Create Form
                    class ObjectForm( ModelForm ):
                        class Meta:
                            model = easy_model.model
                    
                    # -- Get and Populate Form Reference
                    try:
                        form    = ObjectForm
                        object  = form( request.POST, instance = easy_model.obj_by_pk( url ) )
                    except:
                        return HttpResponseBadRequest()
    
                    # -- Save Form or Throw 500 Server Error
                    try:
                        object.save()
                    except:
                        return HttpResponseServerError()
                        
            else:
                return HttpResponseForbidden()
        

        # -- Switch on Extension
        if extension == "json":
            data = serializers.serialize( "json", [ easy_model.obj_by_pk( url ) ] )
            return http.HttpResponse( data, "application/json" )
        elif extension == "xml":
            data = serializers.serialize( "xml", [ easy_model.obj_by_pk( url ) ] )
            return http.HttpResponse( data, "text/xml" )
        elif extension == "poxml":
            data = sbserializers.serialize( "poxml", [ easy_model.obj_by_pk( url ) ] )
            return http.HttpResponse( data, "text/xml" )
        else:
            obj = easy_model.object_by_pk(url)
            data = serializers.serialize( "json", [ easy_model.obj_by_pk( url ) ] )
            return render_to_response( 'servicebrowser/object_detail.html', {'object': obj, 'root_url': model_databrowse.site.root_url, 'data': data}, context_instance = RequestContext(request) )