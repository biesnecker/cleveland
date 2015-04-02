import os
import sys
from distutils.core import setup

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

if sys.version_info >= (3, 4):
    install_requires = []
else:
    install_requires = ['asyncio']

setup(name='cleveland',
      version='0.1.1',
      author='John Biesnecker',
      author_email='jbiesnecker@gmail.com',
      url='https://github.com/biesnecker/cleveland',
      packages=['cleveland'],
      package_dir={'cleveland': './cleveland'},
      install_requires=install_requires,
      description='Simple asyncio-based actors.',
      license='mit',
      long_description=read('README.txt')
)