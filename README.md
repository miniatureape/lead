# Lead

A static site generator

## Description

This is a static site generator used only by me, for my very specific and very modest needs. 

It in no way tries to mimic the capabilities of something like jekyll, hyde, cactus, etc.

## Usage

To create a site, make a folder and create a file called `conf.json` that defines a number of directories where you'll store you content.

```
{
    "posts": "_log",
    "styles": "_styles",
    "images": "_images",
    "log_images": "_images/log",
    "output": "_site",
    "layouts": "_layouts",
    "remote_location" : "user@remotehost:/public/dir"
}
```

*posts* in this directory, store your blog posts. See below for more.

*styles* in this directory store any styles you want copied over to your public site.

*images* in this directory store any images you want to appear on the site. This can be used for logos, icons, etc.

*log_images* in this directory store the images for blog posts. There is a shortcut for referring to pictures in blogposts, see below.

*output* this is where your built site will be output.

*layouts* blog posts can use templates defined in this directory.

*remote_location* used as the target for scp when you *push*

### Writing a Blog Post

If you run `new` a blank blog post will be created in your "posts" folder. In order for it to be publishable, it needs to have a `.md` ending and the file needs to be renamed with a real file name, not 'untitled'.

Blogs are markdown with some json frontmatter:

```
{
    "title": "",
    "date": "2020-12-17",
    "layout": "post"
}
```

The *layout* key defines the jinja file in layouts to use. Everything else is obvious.

#### Blog Helpers

To add an image, put the file name in on a line by itself. For example:

```
Here is my blog post

example.png

And here is some stuff below the picture
```

If images are greater than 1024 pixels, they'll automatically be resized for the blog.

To add code, use triple back ticks, with language direcly after

```

 ```python
l = [1,2]
```

```
