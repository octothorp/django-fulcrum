from setuptools import setup, find_packages

setup(
    name                = 'servicebrowser',
    version             = '0.1.8',
    description         = 'Data browser and basic REST interface for Django.',
    author              = 'Kieran Lynn',
    author_email        = 'kieran@octothorpstudio.com',
    license             = 'Closed Source',
    url                 = 'http://pocms.potiondesign.com/packages/servicebrowser/',
    packages            = find_packages(),
    include_package_data = True,
    zip_safe            = False
)