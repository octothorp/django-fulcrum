from fulcrum.handler import BaseArbitraryHandler

class CustomHandler(BaseArbitraryHandler):
    
    allowed_methods = ('GET', 'POST')
    
    def read(self, request, *args, **kwargs):
        return {'name': 'CustomHanlder read()', 'data': {'request':request}}