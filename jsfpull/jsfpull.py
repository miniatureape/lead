#! /usr/bin/env python

import os
import sys
import urllib2
from string import Template
from bs4 import BeautifulSoup

html_id = "#id_code_html"
js_id = "#id_code_js"
css_id = "#id_code_css"

def select(html, id):
    part = html.select(id)
    if part:
        return part[0].string
    return part

def get_fiddle_pieces(url):
    fiddle = urllib2.urlopen(url).read()
    html = BeautifulSoup(fiddle)
    return select(html, html_id), select(html, js_id), select(html, css_id)

url = sys.argv[1]

if not url:
    print 'Must specify url'
    exit()

url = "http://jsfiddle.net/justindonato/w5fJz/54/"
html, js, css = get_fiddle_pieces(url)

tpl_filename = os.path.join(os.path.dirname(__file__), 'template.html')
tplstr = open(tpl_filename).read()
tpl = Template(tplstr)

print tpl.substitute(html=html, js=js, css=css)
