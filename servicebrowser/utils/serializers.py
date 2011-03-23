import re

def serialize( format, queryset ):
    if format == "poxml":
        return poxml( queryset )
    else:
        raise

def poxml( queryset ):
    
    # -- Write XML
    xml = u"<objects>"
    
    try:
        m = queryset.model
    except:
        m = queryset[0]
    
    for object in queryset:
    
        # -- Create Element
        xml = xml + u"<element>"
        xml = xml + u"<type>%s</type>" % m._meta.verbose_name
    
        # -- Normal Fields
        #for field in model._meta.local_fields:
        for field in m._meta.local_fields:

            value = getattr( object, field.name )

            # -- Clean Up Text Strings
            if type(value).__name__ == 'unicode':
                value = remove_html_tags( value )
                value = value.replace( "<", "" )
                value = value.replace( ">", "" )
            elif type(value).__name__ == 'FieldFile':
                value = unicode( value )
            else :
                value = str( value )

            xml = xml + u"<%s>" % field.name
            xml = xml + value
            xml = xml + u"</%s>" % field.name

        # -- Many-to-Many Field
        for field in m._meta.local_many_to_many:
            
            related = u""
                
            for r in getattr( object, field.name ).all():
                if related == "":
                    related += str(r.id)
                else:
                    related += "," + str(r.id)

            # -- Write Out Packet
            xml = xml + u"<%s>%s</%s>" % ( field.name, related, field.name  )

        xml = xml + u"</element>"

    xml = xml +  "</objects>"
    
    return xml
    
def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)