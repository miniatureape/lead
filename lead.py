#!/usr/bin/env python

import os
import re
import sys
import time
import glob
import json
import shutil
import jinja2
import fnmatch
import pathlib
import optparse
import markdown
import subprocess
from PIL import Image
from datetime import date
from datetime import datetime
from datetime import timezone
from bs4 import BeautifulSoup
from operator import attrgetter
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from feedgen.feed import FeedGenerator

md   = None
env  = None
root = ""

default_conf = {
    'posts'      : '_log',
    'styles'     : '_styles',
    'scripts'    : '_scripts',
    'demos'      : '_demos',
    'images'     : '_images',
    'log_images' : '_images/log',
    'output'     : '_site',
    'layouts'    : '_layouts',
    'remote_location' : '',
}

class Post(object):

    def __init__(self, source_path):
        print("Building", source_path)
        self.source_path = source_path
        self.source = open(source_path).read()

        data = self.find_data(self.source)
        self.title = data.get('title', 'Untitled')
        self.date = data.get('date', None)
        self.time = datetime.strptime(self.date, "%Y-%m-%d").strftime("%s")
        self.layout = data.get('layout')
        self.filename = data.get('filename', None)
        self.unlisted = data.get('unlisted', None)

        self.raw_alsos = data.get('also', [])
        self.alsos = []

        self.raw_content = self.find_raw_content(self.source)
        if data.get('raw', None):
            self.html = self.raw_content
        else:
            self.html = self.process_html(self.raw_content)

    def link_alsos(self, posts):
        for raw_also in self.raw_alsos:
            for p in posts:
                if raw_also == p.title or raw_also == p.slug or raw_also in p.source_path:
                    self.alsos.append(p)

    def find_data(self, source):
        return json.loads(source[:source.index('}') + 1])

    def find_raw_content(self, post):
        content = post[post.index('}') + 1:]
        return content.strip()

    def replace_code(self, content):
        def highlight_code(match):
            lexer_name = match.group(1)
            code = match.group(2)

            lexer = get_lexer_by_name(lexer_name, stripall=True)
            formatter = HtmlFormatter(linenos=True, cssclass="source")

            return "<div class='code-block'>%s</div>" % highlight(code, lexer, formatter)

        return re.sub(r"```(\w+)\s*\n+(.*?)```", highlight_code, content, flags=re.DOTALL|re.UNICODE)

    def replace_images(self, content):
        def is_log_image(match):
            image_name = match.group(0)
            replace_str = image_name

            base, ext = os.path.splitext(image_name)

            log_images_dir = conf.get('log_images')
            orig_image_path = os.path.join(log_images_dir, image_name)

            # todo this is another dirty hack to get the _ off the output dirs
            build_images_dir = log_images_dir.replace("_", "", 1)

            if os.path.exists(orig_image_path):
                im = Image.open(orig_image_path)

                medium_name = None

                if im.size[0] > 1024 or im.size[1] > 1024:
                    im.thumbnail((1024, 1024))
                    medium_name = "%s.medium%s" % (base, ext,)
                    im.save(os.path.join(log_images_dir, medium_name))

                full_path = os.path.join('/', build_images_dir, image_name)
                if medium_name:
                    medium_path = os.path.join('/', build_images_dir, medium_name)
                else:
                    medium_path = full_path

                replace_str = '<a href="%s"><img class="log-image" src="%s" /></a>' % (full_path, medium_path)

            return replace_str

        return re.sub(r'[a-zA-Z/0-9_-]+\.(jpg|jpeg|gif|png)', is_log_image, content)

    def process_html(self, raw_content):
        raw_content = self.replace_images(raw_content)
        raw_content = self.replace_code(raw_content)
        return markdown.markdown(raw_content)

    def slug(self):
        return slugify(self.title)

def slugify(title):
    return re.sub(r'[^a-zA-Z0-9_-]', '-', title).lower()

def configure(root):
    conf = {}
    full_path = os.path.join(root, 'conf.json')
    if os.path.isfile(full_path):
        conf = json.load(open(full_path))
    default_conf.update(conf)
    return default_conf

def source(key=''):
    return os.path.join(root, conf.get(key, ''))

def output(key='', *args):
    # TODO this is an ugly hack. I dont want underscores on the outdirs
    part = conf.get(key, key).replace("_", "", 1)
    return os.path.join(root, conf.get('output'), part, *args)

def write(filename, content):
    head, tail = os.path.split(filename)
    pathlib.Path(head).mkdir(parents=True, exist_ok=True)
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
    if not os.path.exists(output('notebook')): os.mkdir(output('notebook'))
    if not os.path.exists(output('demos')): os.mkdir(output('demos'))

def move_assets(*assets):
    "Copy styles to site: later we can compress, etc"
    for asset_dir in assets:
        if os.path.isdir(source(asset_dir)):
            try:
                shutil.copytree(source(asset_dir), output(asset_dir))
            except:
                pass

def build_blog():
    posts = []
    posts_dir = source('posts')

    fg = FeedGenerator()
    fg.title('www.justindonato.com')
    fg.id('www.justindonato.com')
    fg.description('Posts from www.justindonato.com')
    fg.link( href='https://www.justindonato.com/feed.atom', rel='self' )
    fg.language('en')

    for path, dirs, filenames in os.walk(posts_dir):
        for post in fnmatch.filter(filenames, '*.md'):
            p = Post(os.path.join(path, post))

            if not p.unlisted:

                fe = fg.add_entry()
                fe.id('https://www.justindonato.com/notebook/' + p.slug() + '.html')
                fe.title(p.title)
                fe.link(href="https://www.justindonato.com/feed/")
                pubdate = datetime.strptime(p.date, '%Y-%m-%d')
                pubdate = pubdate.replace(tzinfo=timezone.utc)
                fe.published(published=pubdate)
                fe.updated(updated=pubdate)

                posts.append(p)

    for p in posts:
        p.link_alsos(posts)
        template = env.get_template("%s.html" % p.layout)
        filename = output('notebook', "%s.html" % p.slug())
        ctx = {'post': p}
        write(filename, template.render(ctx))

    fg.atom_file(output('atom.xml'))
    fg.rss_file(output('rss.xml'))

    return posts

"A little Like os.walk, but filters on dirs"
def walk(root, dirfilter, filefilter):
    for item in os.listdir(root):
        path = os.path.join(root, item)
        if os.path.isdir(path) and dirfilter(path, item):
            for path, item in walk(path, dirfilter, filefilter):
                yield path, item
        elif filefilter(path, item):
            yield path, item

def build_pages(posts):

    def dirfilter(path, item):
        "Skip 'special' folders"
        return not (item[0] == '_' or item[0] == '.')

    def htmlfilter(path, item):
        return os.path.splitext(item)[1] == '.html'

    for fullpath, page in walk(source(), dirfilter, htmlfilter):
        fullpath = fullpath.replace(root, '')[1:]
        p = Post(fullpath)

        ctx = {
            'posts': posts,
            'page': p
        }

        head, tail = os.path.split(fullpath)
        if head:
            try:
                os.makedirs(output(head))
            except:
                pass

        template = env.get_template("%s.html" % p.layout)

        filename = output(os.path.join(head, "%s.html" % p.filename))
        write(filename, template.render(ctx))

def init_jinja():
    global env
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(source('layouts')))
    env.filters['slugify'] = slugify

def build_site():
    "Build all content and move with static assets to output directory"
    init_jinja();

    remove_old_builds()
    create_output_dirs()

    posts = build_blog()
    posts = sorted(posts, key=attrgetter('time'), reverse=True)

    build_pages(posts)

    build_demos()
    move_assets('images', 'styles', 'scripts')

def build_demos():
    """
    A demo is an html page to be included via an iframe in a log entry.
    There are three ways you can build a "demo":
    1. build a json object with html, js and css keys.
    2. place a single standalone html page in the demos folder
    3. put a folder of html and assets in a folder.

    2 and 3 just get copied to the built /demos/ path.
    1 gets built into a page with tab nav, one tab has the highlighted source.
    """

    pygment_afix = '```'
    js_prefix = "%s%s\n" % (pygment_afix, 'javascript')
    css_prefix = "%s%s\n" % (pygment_afix, 'css')

    demos_dir = conf.get('demos', None)

    if not demos_dir:
        return

    template = env.get_template("demo.html")

    "Case 1"
    pattern = os.path.join(demos_dir, '*.json')
    demos = glob.glob(pattern)

    for demo in demos:
        with open(demo) as f:
            data = json.loads(f.read())

            js = data.get('js', '')
            css = data.get('css', '')
            html = data.get('html', '')

            fmt_js = ''
            if js:
                lexer = get_lexer_by_name('js', stripall=True)
                formatter = HtmlFormatter(linenos=True, cssclass="source")
                fmt_js = highlight(js, lexer, formatter)

            ctx = {
                "js": js,
                "html": html,
                "css": css,
                "fmt_js": fmt_js,
            }

        output_file = os.path.join(output('demos'), os.path.basename(demo).replace('json', 'html'))
        write(output_file, template.render(ctx))

        "Case 2"
        pattern = os.path.join(demos_dir, '*.html')
        demos = glob.glob(pattern)
        for demo in demos:
            output_file = os.path.join(output('demos'), os.path.basename(demo))
            with open(demo) as f:
                write(output_file, f.read())

        "Case 3"
        demo_folders = [ (f.path, f.name) for f in os.scandir(demos_dir) if f.is_dir() ]
        for path, name in demo_folders:
            output_dir = os.path.join(output('demos'), name)
            try:
                shutil.copytree(path, output_dir)
            except Exception as e:
                print("could not copy", path, "to", output_dir)

def test_site():
    "Run an HTTP server to serve output directory for testing"
    site = output()

    import http.server
    import fcntl
    import http.server
    import socketserver

    os.chdir(site)
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

    flags = fcntl.fcntl(httpd.socket.fileno(), fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(httpd.socket.fileno(), fcntl.F_SETFD, flags)

    print("Serving locally at port", 8000)
    httpd.serve_forever()

def update_static():
    "Build and move only static assets to output directory"
    output_dirs = (output(conf.get('styles')),
                    output(conf.get('scripts')),)
    for output_dir in output_dirs:
        try:
            shutil.rmtree(output_dir)
        except:
            print(("Warning: %s does not exist" % output_dir))

    move_assets('images', 'styles', 'scripts')

def new_post():
    "Quickly start a new post"
    stub = {
        "title": "Untitled Post",
        "date": date.today().strftime("%Y-%m-%d"),
        "layout": "post",
        "unlisted": True,
    }

    filename = "%s-%s.md" % (stub.get('title'), stub.get('date'))
    filename = slugify(filename)
    path = os.path.join(root, conf.get('posts'), filename)

    if os.path.exists(path):
        return "Stub already exists: %s" % filename

    with open(path, 'w') as f:
        f.write(json.dumps(stub, indent=4))

    return path

def push_remote():
    "Sync output folder with remote server"
    command = "rsync -r -v -e ssh %s %s" % (output(), conf.get('remote_location'))
    print(command)
    p = subprocess.Popen(command.split(),
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    print(stdout, stderr)

def invalid_command():
    return "Unknown command. Try one of: %s" % ', '.join(list(commands.keys()))

def command_help(command_name):
    "Pass command name for usage help"
    command = commands.get(command_name, None)
    if command:
        print(command.__doc__)
    else:
        print(invalid_command())

def command_dev():
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    from multiprocessing import Process
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    def create_server():
        site = output()
        os.chdir(site)
        httpd = HTTPServer(('', 8000), SimpleHTTPRequestHandler)
        httpd.serve_forever()

    class Rebuilder(FileSystemEventHandler):

        p = None

        def stop_server(self):
            if self.p:
                print("Stopping server")
                self.p.terminate()

        def rebuild(self):
            os.chdir('/home/justin/projects/justindonato.com/')
            update_static()
            build_site()

        def start_server(self):
            if self.p:
                self.stop_server()
            print("Starting Server")
            self.p = Process(target=create_server)
            self.p.start()

        def on_modified(self, event):
            if self.should_rebuild(event):
                self.stop_server()
                print("Rebuilding")
                self.rebuild()
                self.start_server()

        def should_rebuild(self, event):
            if event.is_directory:
                return False
            base, ext = os.path.splitext(event.src_path)
            if ext == ".swp":
                return False
            if output() in event.src_path:
                return False
            print("should rebuild", event.src_path)
            return True

    rebuilder = Rebuilder()
    rebuilder.start_server()

    site = output()
    os.chdir(site)

    observer = Observer()
    observer.schedule(rebuilder, "/home/justin/projects/justindonato.com/", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

commands = {
    "build"  : build_site,
    "test"   : test_site,
    "static" : update_static,
    "dev"   : command_dev,
    "new"    : new_post,
    "push"   : push_remote,
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
            print(command_help.__doc__)
        exit()

    command = commands.get(command, invalid_command)
    result = command()

    if result:
        print(result)
