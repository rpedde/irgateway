from setuptools import setup, find_packages

VERSION = '0.1'

setup(description='IR Gateway thing',
      author='ron@pedde.com',
      version=VERSION,
      packages=find_packages(),
      install_requires=[
          'PyYAML',
          'evdev',
          'requests'
      ],
      name='irgateway',
      entry_points = {
          'console_scripts': [
              'irgateway = irgateway.cli:main'
          ]
      }
)
