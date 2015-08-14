#!/usr/bin/env python
# coding: utf-8


from setuptools import setup
import os
import re

cur_dir = os.path.dirname(__file__)

# :TRICKY: после установки по умолчанию модули *.py появятся прямо в 
# env/lib/python<VERSION>/site-packages/*.py(c) ; у pip есть режим
# pip install --egg, в этом случае файлы установятся в site-packages/<name=fablib>
# с добавлением соответ. файла .pth
src_dir = "src"

py_modules = []
for fname in os.listdir(os.path.join(cur_dir, src_dir)):
    m = re.match("(.*)\.py$", fname)
    if m:
        py_modules.append(m.group(1))
        
setup(
    name = "disvolvu",
    version = 1,

    package_dir = {'': 'src'},
    py_modules = py_modules,
    
    entry_points = {
        'console_scripts': ['disvolvu = disvolvu:main'],
    },
)
