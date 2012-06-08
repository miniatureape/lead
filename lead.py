import os
import re
import glob
import yaml
import shutil
import jinja2
import fnmatch
import markdown2
from datetime import datetime

root_dir = '/home/justin/Documents/projects/justindonato.com/'
posts_dir = os.path.join(root_dir, 'log')
styles_dir = os.path.join(root_dir, 'styles')
output_dir = os.path.join(root_dir, '_site')
styles_output_dir = os.path.join(output_dir, 'styles')
log_output_dir = os.path.join(output_dir, 'log')
template_path = os.path.join(root_dir, '_layouts')

md = markdown2.Markdown()

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

def is_post(filename):
    "Given a file name, returns true if this is a post"
    return os.path.splitext(filename)[1] == '.yml'

if not os.path.isdir(posts_dir):
    raise IOError("Posts directory does not exist at %s" % posts_dir)

"For now, delete the old site"
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

"Create output directories"
os.mkdir(output_dir)
if not os.path.exists(log_output_dir): os.mkdir(log_output_dir)

"Copy styles to site: later we can compress, etc"
shutil.copytree(styles_dir, styles_output_dir)

env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))

"Build Blog"

posts = [os.path.join(posts_dir, post) for post in os.listdir(posts_dir) if is_post(post)]
processed_posts = []

for post in posts:
    p = Post(post)
    ctx = {'posts': [p]}
    template = env.get_template("%s.html" % p.layout)

    output = open(os.path.join(output_dir, "%s.html" % p.slug()), 'w')
    output.write(template.render(ctx))

    # accumulate the posts
    processed_posts.append(p)

"Like os.walk, but filters on dirs"
def walk(root, dirfilter, filefilter):
    for item in os.listdir(root):
        path = os.path.join(root, item)
        if os.path.isdir(path) and dirfilter(path, item):
            walk(path, dirfilter, filefilter)
        elif filefilter(path, item):
            yield path, item


"Build root pages"
def dirfilter(path, item):
    return not item[0] == '_'

def htmlfilter(path, item):
    return os.path.splitext(item)[1] == '.html'

for fullpath, page in walk(root_dir, dirfilter, htmlfilter):
    p = Post(page)

    ctx = {
        'posts': processed_posts,
        'page': p
    }

    template = env.get_template("%s.html" % p.layout)

    output = open(os.path.join(output_dir, "%s.html" % p.filename), 'w')
    output.write(template.render(ctx))
