from django.shortcuts import render_to_response
from django.template import RequestContext
    
def test_js(request):
    return render_to_response('test_js.html', {}, RequestContext(request))
