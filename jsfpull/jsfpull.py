#!/usr/bin/env python

import os
import sys
import json
import urllib2
from bs4 import BeautifulSoup

html_id = "#id_code_html"
js_id = "#id_code_js"
css_id = "#id_code_css"

def select(html, id):
    part = html.select(id)
    if part:
        return part[0].string
    return part

def get_fiddle_data(url):
    fiddle = urllib2.urlopen(url).read()
    html = BeautifulSoup(fiddle)
    return {
        "html": select(html, html_id),
        "css": select(html, css_id),
        "js": select(html, js_id),
    }

url = sys.argv[1]
if not url:
    print 'Must specify url'
    exit()

data = get_fiddle_data(url)
print json.dumps(data, indent=4)
