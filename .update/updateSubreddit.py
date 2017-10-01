import praw, os, json, sys
from csscompressor import compress

# Get directory of the project root (i.e. parent of this "updates" directory)
update_dir = os.getcwd()
project_dir = os.path.join(update_dir, os.pardir)

# Read config from environment variables
client_id = os.environ['REDDIT_CLIENT_ID']
client_secret = os.environ['REDDIT_CLIENT_SECRET']
username = os.environ['REDDIT_USERNAME']
password = os.environ['REDDIT_PASSWORD']
sub_name = os.environ['REDDIT_SUBREDDIT']
if not client_id or not client_secret:
    print("Missing Reddit app credentials. Make sure you set the REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars in Travis.")
    sys.exit(1)
if not username or not password:
    print("Missing Reddit user authentication. Make sure you set the REDDIT_USERNAME and REDDIT_PASSWORD env vars in Travis.")
    sys.exit(1)
if not sub_name:
    print("Missing target subreddit. Make sure you set the REDDIT_SUBREDDIT env var in Travis. Note that this sub's theme will be overwritten.")
    sys.exit(1)

# Reddit init and login stuff
# scopes = ["wikiedit", "modconfig"]
r = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    username=username,
    password=password,
    user_agent="script:geo1088/reddit-stylesheet-sync:v1.0 (by /u/geo1088)")
print("Hopefully I just logged into Reddit okay.")

# Get the subreddit
print("Writing stylesheet to /r/{}".format(sub_name))
sub = r.subreddit(sub_name)
print("Hey, in case no one's told you in a while: You're awesome! :D")

# Read stylesheet and minify it, storing the results
stylesheet_file = open(os.path.join(project_dir, "style.css"), "r")
stylesheet = compress(stylesheet_file.read()) # minify
# stylesheet = stylesheet_file.read() # don't minify
stylesheet_file.close()
print("Got and minified stylesheet.")

# Push the stylesheet to the subreddit
# print("Now trying to upload the stylesheet to /r/{}".format(sub_name))
# print("Using revision reason: {}".format(os.environ['REV_EDIT_MSG']))
# try:
#     sub.wiki['config/stylesheet'].edit(stylesheet, os.environ['REV_EDIT_MSG'])
# except Exception:
#     print("Ran into an error while uploading stylesheet; aborting.")
#     sys.exit(1)

# Debug some shit
print(os.environ["TRAVIS_COMMIT_MESSAGE"])
print(os.environ["TRAVIS_COMMIT_RANGE"])

print("That's a wrap")

# # Get and upload the sidebar (TODO)
# sidebar = open(os.path.join(os.path.join(dir, os.pardir), "sidebar.md"))
# sidebarContents = sidebar.read()
# sidebar.close()
# sub.edit_wiki_page("config/sidebar", sidebarContents, updateReason)
