import praw
import OAuth2Util
import os
import json
from csscompressor import compress

# Get directory of the project root (i.e. parent of this "updates" directory)
update_dir = os.getcwd()
project_dir = os.path.join(update_dir, os.pardir)

# Read public configuration file (OAuth stuff has its own file, not this one)
config_file = open(os.path.join(update_dir, "config.json"), "r")
config = json.load(config_file)
config_file.close()

# Reddit login
r = praw.Reddit(config['user_agent'])
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)
print("Hopefully I just logged into Reddit okay.")

# Get the subreddit
sub = r.get_subreddit(config["subreddit"])
print("Using subreddit {}".format(config["subreddit"]))

# Read stylesheet and minify it, storing the results
stylesheet_file = open(os.path.join(project_dir, "style.css"), "r")
stylesheet = compress(stylesheet_file.read())
stylesheet_file.close()

# If there's a link specified in the config, add a comment with that link to the uploaded stylesheet
link = config["stylesheet_link"]
if (link):
    print("Including a comment leading to {}".format(link))
    comment = "/* Uncompressed stylesheet can be found here: {} */".format(link)
    stylesheet = comment + "\n" + stylesheet

# Push the stylesheet to the subreddit
sub.edit_wiki_page("config/stylesheet", stylesheet, "")
print("That's a wrap")
# TODO: Support an update reason there

# # Get and upload the sidebar (TODO)
# sidebar = open(os.path.join(os.path.join(dir, os.pardir), "sidebar.md"))
# sidebarContents = sidebar.read()
# sidebar.close()
# sub.edit_wiki_page("config/sidebar", sidebarContents, updateReason)
