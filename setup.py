import os,sys
from setuptools import setup


setup(
	name = 'aoi_server',
	packages = ['aoiserver'],
	include_package_data=True,
	zip_safe = True,
	version = '1.0',
	description = 'A simple server framework',
	author = 'BlueLeaf',
	author_email = 'apolloyeh0123@gmail.com',
	keywords = ['Server','NetWork'],
)
