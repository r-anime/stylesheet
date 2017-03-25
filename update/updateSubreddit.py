import praw, OAuth2Util, os, json, sys
from csscompressor import compress

# Get directory of the project root (i.e. parent of this "updates" directory)
update_dir = os.getcwd()
project_dir = os.path.join(update_dir, os.pardir)

# Read public configuration file (OAuth stuff has its own file, not this one)
config_file = open(os.path.join(update_dir, "config.json"), "r")
config = json.load(config_file)
config_file.close()

# Reddit init and login stuff
# scopes = ["wikiedit", "modconfig"]
r = praw.Reddit(
    client_id=config["auth"]["client_id"],
    client_secret=config["auth"]["client_secret"],
    username=config["auth"]["username"],
    password=config["auth"]["password"],
    user_agent=config["user_agent"]
)
print("Hopefully I just logged into Reddit okay.")

# Get the subreddit
print("Using subreddit {}".format(config["subreddit"]))
sub = r.subreddit(config["subreddit"])
print("Hey, in case no one's told you in a while: You're awesome! :D")

# Read stylesheet and minify it, storing the results
stylesheet_file = open(os.path.join(project_dir, "style.css"), "r")
stylesheet = compress(stylesheet_file.read())
# stylesheet = stylesheet_file.read() # no mini
stylesheet_file.close()
print("Got and minified stylesheet.")

# If there's a link specified in the config, add a comment with that link to the uploaded stylesheet
link = config["stylesheet_link"]
if (link):
    print("Including a comment leading to {}".format(link))
    comment = "/* Uncompressed stylesheet can be found here: {} */".format(link)
    stylesheet = comment + "\n" + stylesheet

# Push the stylesheet to the subreddit
print("Now trying to upload the stylesheet to /r/{}".format(config["subreddit"]))
try:
    sub.wiki['config/stylesheet'].edit(stylesheet)
    # TODO: Support an update reason there
except Exception:
    print("Ran into an error while uploading stylesheet; aborting.")
    raise
    sys.exit(1)

print("That's a wrap")

# # Get and upload the sidebar (TODO)
# sidebar = open(os.path.join(os.path.join(dir, os.pardir), "sidebar.md"))
# sidebarContents = sidebar.read()
# sidebar.close()
# sub.edit_wiki_page("config/sidebar", sidebarContents, updateReason)
