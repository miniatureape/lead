import os
import re
import sys
import glob
import yaml
import json
import shutil
import jinja2
import fnmatch
import markdown2
from datetime import datetime

root = ""

default_conf = {
    'posts': 'log',
    'styles': 'styles',
    'images': 'images',
    'output': '_site',
    'layouts': '_layouts',
}

class Post(object):

    yaml_pattern = r'---.*?---'

    def __init__(self, source_path):
        self.source = open(source_path).read()

        data = self.find_data(self.source)
        self.title = data.get('title', 'Untitled')
        self.date = data.get('date', None)
        self.layout = data.get('layout')
        self.filename = data.get('filename', None)

        self.raw_content = self.find_raw_content(self.source)

    def find_data(self, source):
        matches = re.search(self.yaml_pattern, source, re.DOTALL)
        data, empty = yaml.load_all(matches.group(0))
        return data

    def find_raw_content(self, post):
        return re.sub(self.yaml_pattern, '', post, count=0, flags=re.DOTALL)

    def process_html(self, raw_content):
        return md.convert(raw_content)

    def slug(self):
        return self.slugify(self.title)

    def slugify(self, title):
        return re.sub(r'[^a-zA-Z0-9_-]', '-', title).lower()    

def configure(root):
    conf = {}
    full_path = os.path.join(root, 'conf.json')
    if os.path.isfile(full_path):
        conf = json.load(open(full_path))
    conf.update(default_conf)
    return conf

def source(key=''):
    return os.path.join(root, conf.get(key, ''))

def output(key=''):
    return os.path.join(root, conf.get('output'), conf.get(key, ''))

def remove_old_builds():
    "For now, delete the old site"
    output_dir = output()
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

def create_output_dirs():
    "Create output directories"
    os.mkdir(output())
    if not os.path.exists(output('log')): os.mkdir(output('log'))

def move_assets():
    "Copy styles to site: later we can compress, etc"
    shutil.copytree(source('styles'), output('styles')) 
    shutil.copytree(source('images'), output('images')) 

def is_post(filename):
    "Given a file name, returns true if this is a post"
    return os.path.splitext(filename)[1] == '.yml'

"A little Like os.walk, but filters on dirs"
def walk(root, dirfilter, filefilter):
    for item in os.listdir(root):
        path = os.path.join(root, item)
        if os.path.isdir(path) and dirfilter(path, item):
            walk(path, dirfilter, filefilter)
        elif filefilter(path, item):
            yield path, item

def build_blog():
    posts = []
    posts_dir = source('posts')

    for path, dirs, filenames in os.walk(posts_dir):
        for post in fnmatch.filter(filenames, '*.yml'):
            p = Post(os.path.join(path, post))
            ctx = {'posts': [p]}

            template = env.get_template("%s.html" % p.layout)

            out = open(os.path.join(output(), "%s.html" % p.slug()), 'w')
            out.write(template.render(ctx))

            posts.append(p)

    return posts

def build_pages(posts):

    def dirfilter(path, item):
        "Skip 'special' folders"
        return not item[0] == '_'

    def htmlfilter(path, item):
        return os.path.splitext(item)[1] == '.html'

    for fullpath, page in walk(source(), dirfilter, htmlfilter):
        p = Post(page)

        ctx = {
            'posts': processed_posts,
            'page': p
        }

        template = env.get_template("%s.html" % p.layout)

        "TODO: This output needs to get fixed"
        out = open(os.path.join(output(), "%s.html" % p.filename), 'w')
        out.write(template.render(ctx))

if __name__ == '__main__':
    print "Started"
    "argument to script is root site folder"
    root = sys.argv[1]

    conf = configure(root)

    md = markdown2.Markdown()
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(source('layouts')))

    remove_old_builds()
    create_output_dirs()

    posts = build_blog()
    build_pages(posts)

    # move_assets()
