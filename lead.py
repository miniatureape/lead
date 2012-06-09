import os
import re
import sys
import glob
import json
import shutil
import jinja2
import fnmatch
import markdown2
from datetime import datetime
from operator import attrgetter

root = ""

default_conf = {
    'posts': 'log',
    'styles': 'styles',
    'images': 'images',
    'output': '_site',
    'layouts': '_layouts',
}

class Post(object):

    def __init__(self, source_path):
        self.source = open(source_path).read()

        data = self.find_data(self.source)
        self.title = data.get('title', 'Untitled')
        self.date = data.get('date', None)
        self.time = datetime.strptime(self.date, "%m-%d-%y").strftime("%s")
        self.layout = data.get('layout')
        self.filename = data.get('filename', None)

        self.raw_content = self.find_raw_content(self.source)
        self.html = self.process_html(self.raw_content)

    def find_data(self, source):
        return json.loads(source[:source.index('}') + 1])

    def find_raw_content(self, post):
        content = post[post.index('}') + 1:]
        return content.strip()

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

def output(key='', *args):
    return os.path.join(root, conf.get('output'), conf.get(key, key), *args)

def write(filename, content):
    if os.path.exists(filename):
        print "Warning: %s already exists. Overwriting." % filename
    out = open(filename, 'w')
    out.write(content)

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
    if os.path.isdir(source('styles')):
        shutil.copytree(source('styles'), output('styles')) 
    if os.path.isdir(source('images')):
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
            ctx = {'post': p}

            template = env.get_template("%s.html" % p.layout)

            filename = output('log', "%s.html" % p.slug())
            write(filename, template.render(ctx))

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
            'posts': posts,
            'page': p
        }

        template = env.get_template("%s.html" % p.layout)

        filename = output("%s.html" % p.filename)
        write(filename, template.render(ctx))

if __name__ == '__main__':
    print "Started Lead."

    "argument to script is root site folder"
    root = sys.argv[1]

    conf = configure(root)

    md = markdown2.Markdown(extras=['code-color'])
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(source('layouts')))

    remove_old_builds()
    create_output_dirs()

    posts = build_blog()
    posts = sorted(posts, key=attrgetter('time'), reverse=True)

    build_pages(posts)

    move_assets()
