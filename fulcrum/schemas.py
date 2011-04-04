"""
Copyright (c) 2009 James Harrison Fisher <jameshfisher@gmail.com>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import json

from django.http import HttpResponse

from django.db.models.fields import (AutoField, CharField, FloatField, 
SlugField, EmailField, IntegerField, BooleanField, DateField, DateTimeField )

from xml.dom import getDOMImplementation
impl = getDOMImplementation()

class Schema:
    """
    An abstract class representing a schema for a particular model.
    Initiate it passing the model class to it as the only argument.
    """
    
    def __init__(self, model, documentation=True):
        """
        """
        self.model = model
        
        self.documentation = documentation
        
        from settings import LANGUAGE_CODE
        self.language = LANGUAGE_CODE
        
        self._prepare()
    
    def _prepare(self):
        """
        If the Schema instance needs to prepare stuff before it's ready to
        output the schema in one of various ways, it should do it here.
        
        Example: creation of an XML DOM instance before using toxml() or
        toprettyxml().
        
        This should take into account self.documentation, but not self.pretty.
        """
        pass
    
    def text(self, pretty=True):
        """
        Print the schema text.
        
        This should be aware of self.pretty.
        """
        raise NotImplementedError
    
    def __str__(self):
        return self.text()
    def __unicode__(self):
        return self.text()
        

class XMLSchema(Schema):
    """
    This class is ABSTRACT.  It is not a schema language -- it is NOT the
    W3C XML Schema language -- it just factors out the commonalities of
    XML-based schemas.
    """
    
    def text(self, pretty=True):
        # the following is a horrible, horrible hack.  If anyone can tell me why this isn't prepended, I would be glad.
        if pretty:
            return '<?xml version="1.0" encoding="UTF-8" ?>' + self.root.toprettyxml(encoding="utf-8")
        return '<?xml version="1.0" encoding="UTF-8" ?>' + self.root.toxml(encoding="utf-8")
    
    
class XSDSchema(XMLSchema):
    """
    For more information, try:
    * http://www.w3.org/TR/xmlschema-2/
    """

    def _prepare(self):
        """
        From a Django model class, create an XML Schema Document.
        """
        
        doc = impl.createDocument('http://www.w3.org/2001/XMLSchema', 'xsd:schema', impl.createDocumentType('','',''))
        root = doc.documentElement
        root.setAttribute("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
        
        # Create annotation for this model
        annotation = doc.createElement("xsd:annotation")
        annotation_documentation = doc.createElement("xsd:documentation")
        annotation_documentation.setAttribute("xml:lang", self.language)
        annotation_documentation.appendChild(doc.createTextNode("Schema for the '%s' model." % unicode(self.model._meta.verbose_name)))
        annotation.appendChild(annotation_documentation)
        root.appendChild(annotation)
    
        def field_to_xsd(field):
            """
            Private function to convert a Model field to its XSD representation.
            """
            el = doc.createElement("xsd:element")
            el.setAttribute("name", field.name)
            
            cls = field.__class__
            
            if cls == AutoField:
                el.setAttribute('type', 'int')
            elif cls == CharField:
                el.setAttribute('type', 'string')
                el.setAttribute('maxLength', unicode(field.max_length))
            elif cls == FloatField:
                el.setAttribute('type', 'float')
            elif cls == SlugField:
                el.setAttribute('type', 'string')
                # ...
            elif cls == EmailField:
                el.setAttribute('type', 'string')
                # ...
            elif cls == FloatField:
                el.setAttribute('type', 'float')
            elif cls == IntegerField:
                el.setAttribute('type', 'int')
            elif cls == BooleanField:
                el.setAttribute('type', 'boolean')
            elif cls == DateField:
                el.setAttribute('type', 'date')
            elif cls == DateTimeField:
                el.setAttribute('type', 'dateTime')
            
            help_text = unicode(field.help_text)
            if help_text:
                annot = doc.createElement("xsd:annotation")
                documentation = doc.createElement("xsd:documentation")
                documentation.appendChild(doc.createTextNode(help_text))
                annot.appendChild(documentation)
                el.appendChild(annot)
            
            return el
        
        for field in self.model._meta.fields:
            root.appendChild(field_to_xsd(field))
        
        self.root = root	# Prepare for printing
        

class JSONSchema(Schema):
    """
    http://json-schema.org/
    """
    
    def _prepare(self):
        data = {}
        data["description"] = unicode(self.model._meta.verbose_name)
        data["type"] = "object"
        
        properties = {}
        for field in self.model._meta.fields:
            info = {}
            
            cls = field.__class__
            
            if cls == AutoField:
                info["type"] = "integer"
            elif cls == CharField:
                info["type"] = "string"
                info["maxLength"] = field.max_length
            elif cls == FloatField:
                info["type"] = "number"
            elif cls == SlugField:
                info["type"] = "string"
            elif cls == EmailField:
                info["type"] = "string"
            elif cls == IntegerField:
                info["type"] = "integer"
            elif cls == BooleanField:
                info["type"] = "boolean"
            elif cls == DateField:
                info["type"] = "string"
                info["format"] = "date"
            elif cls == DateTimeField:
                info["type"] = "string"
                info["format"] = "date-time"
            
            properties[field.name] = info
        
        data["properties"] = properties
        
        self.data = data
        
    def text(self, pretty=True):
        if pretty == True:
            return json.dumps(self.data, sort_keys=True, indent=4)
        else:
            return json.dumps(self.data)
    

def get_schema(model, format='json', pretty=True):
    try:
        cls, content_type = map[format]
    except KeyError:
        return 'The format you specified, {0}, corresponds to no known schema type.'.format(format)
    return cls(model).text(pretty=pretty)
    
    
def get_schema_view(model, format, pretty=True):
    
    try:
        cls, content_type = map[format]
    except KeyError:
        return 'The format you specified, {0}, corresponds to no known schema type.'.format(format)
    return HttpResponse(cls(model).text(pretty=pretty), content_type)

map = {
    'xsd': (XSDSchema, 'application/xml'),
    'json': (JSONSchema, 'application/json')
}
