import os
import sys

# Ensure project src is importable for autodoc
sys.path.insert(0, os.path.abspath("../src"))

project = 'ReceiptScanner'
extensions = ['sphinx.ext.autodoc']
templates_path = ['_templates']
exclude_patterns = []
master_doc = 'index'

html_theme = 'alabaster'
