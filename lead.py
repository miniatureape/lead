import os
import re
import sys
import glob
import json
import shutil
import jinja2
import fnmatch
import optparse
import markdown2
from PIL import Image
from datetime import date
from datetime import datetime
from operator import attrgetter


md   = None
env  = None
root = ""

default_conf = {
    'posts': 'log',
    'styles': 'styles',
    'scripts': 'scripts',
    'images': 'images',
    'log_images': 'images/log',
    'output': '_site',
    'layouts': '_layouts',
}

class Post(object):

    def __init__(self, source_path):
        self.source = open(source_path).read()

        data = self.find_data(self.source)
        self.title = data.get('title', 'Untitled')
        self.date = data.get('date', None)
        self.time = datetime.strptime(self.date, "%Y-%m-%d").strftime("%s")
        self.layout = data.get('layout')
        self.filename = data.get('filename', None)

        self.raw_content = self.find_raw_content(self.source)
        self.html = self.process_html(self.raw_content)

    def find_data(self, source):
        return json.loads(source[:source.index('}') + 1])

    def find_raw_content(self, post):
        content = post[post.index('}') + 1:]
        return content.strip()

    def replace_images(self, content):
        def is_log_image(match):
            image_name = match.group(0)
            replace_str = image_name

            base, ext = os.path.splitext(image_name)

            log_images_dir = conf.get('log_images')
            orig_image_path = os.path.join(log_images_dir, image_name)

            if os.path.exists(orig_image_path):
                im = Image.open(orig_image_path)

                im.thumbnail((1024, 1024))
                medium_name = "%s.medium.%s" % (base, ext,)
                im.save(os.path.join(log_images_dir,medium_name))

                full_path = os.path.join('/', log_images_dir, image_name)
                medium_path = os.path.join('/', log_images_dir, medium_name)

                replace_str = '<a href="%s"><img class="log-image" src="%s" /></a>' % (full_path, medium_path)

            return replace_str

        return re.sub(r'[a-zA-Z0-9_-]+\.(jpg|jpeg|gif|png)', is_log_image, content)


    def process_html(self, raw_content):
        raw_content = self.replace_images(raw_content)
        return md.convert(raw_content)

    def slug(self):
        return slugify(self.title)

def slugify(title):
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
    out.write(content.encode('utf-8'))

def remove_old_builds():
    "For now, delete the old site"
    output_dir = output()
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

def create_output_dirs():
    "Create output directories"
    os.mkdir(output())
    if not os.path.exists(output('log')): os.mkdir(output('log'))

def move_assets(assets):
    "Copy styles to site: later we can compress, etc"
    assets_dirs = [conf.get(asset) for asset in assets]
    for asset_dir in assets_dirs:
        if os.path.isdir(source(asset_dir)):
            shutil.copytree(source(asset_dir), output(asset_dir)) 

def is_post(filename):
    "Given a file name, returns true if this is a post"
    return os.path.splitext(filename)[1] == '.md'

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
        for post in fnmatch.filter(filenames, '*.md'):
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
        p = Post(fullpath)

        ctx = {
            'posts': posts,
            'page': p
        }

        template = env.get_template("%s.html" % p.layout)

        filename = output("%s.html" % p.filename)
        write(filename, template.render(ctx))

def build_site():
    "Build all content and move with static assets to output directory"
    global md
    global env

    md = markdown2.Markdown(extras=['code-color'])
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(source('layouts')))

    remove_old_builds()
    create_output_dirs()

    posts = build_blog()
    posts = sorted(posts, key=attrgetter('time'), reverse=True)

    build_pages(posts)

    move_assets(('images', 'styles'))

def test_site():
    "Run an HTTP server to serve output directory for testing"
    site = output()

    import BaseHTTPServer
    import fcntl
    import SimpleHTTPServer
    import SocketServer

    os.chdir(site)
    server_address = ('', 8000)
    httpd = BaseHTTPServer.HTTPServer(server_address, SimpleHTTPServer.SimpleHTTPRequestHandler)

    flags = fcntl.fcntl(httpd.socket.fileno(), fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(httpd.socket.fileno(), fcntl.F_SETFD, flags)

    httpd.serve_forever()

    return "serving at port", 8000 

def update_static():
    "Build and move only static assets to output directory"
    output_dirs = (output(conf.get('styles')), output(conf.get('scripts')))
    for output_dir in output_dirs:
        try:
            shutil.rmtree(output_dir)
        except:
            print("Warning: %s does not exist" % output_dir)
    move_assets(('styles', 'scripts'))

def new_post():
    "Quickly start a new post"
    stub = {
        "title": "Untitled Post",
        "date": date.today().strftime("%Y-%m-%d"),
        "layout": "post",
    }

    filename = "%s-%s.md" % (stub.get('title'), stub.get('date'))
    filename = slugify(filename)
    path = os.path.join(root, conf.get('posts'), filename)

    if os.path.exists(path):
        return "Stub already exists: %s" % filename

    with open(path, 'w') as f:
        f.write(json.dumps(stub, indent=4))

    return path

def invalid_command():
    return "Unknown command. Try one of: %s" % ', '.join(commands.keys())

def command_help(command_name):
    "Pass command name for usage help"
    command = commands.get(command_name, None)
    if command:
        print command.__doc__
    else:
        print invalid_command()

commands = {
    "build"  : build_site,
    "test"   : test_site,
    "static" : update_static,
    "new"    : new_post,
    "help"   : command_help,
}

if __name__ == '__main__':
    conf = configure(root)
    root = os.getcwd()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', default="", help="The command to run.", nargs='*')
    args = parser.parse_args()

    try:
        command = args.command[0]
    except IndexError:
        command_help("")
        exit()
    
    if command == 'help':
        if len(args.command) > 1:
            command_name = args.command[1]
            command_help(command_name)
        else:
            print command_help.__doc__
        exit()
        
    command = commands.get(command, invalid_command)
    result = command()

    if result:
        print result
