from setuptools import setup, find_packages

setup(
    name                = 'fulcrum',
    version             = '0.1.0',
    description         = 'Data browser and basic REST interface for Django.',
    author              = 'Kieran Lynn',
    author_email        = 'kieran@octothorpstudio.com',
    license             = 'Closed Source',
    url                 = 'https://github.com/octothorp/django-fulcrum',
    packages            = find_packages(),
    include_package_data = True,
    zip_safe            = False
)