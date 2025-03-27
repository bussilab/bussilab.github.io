import json
import requests
from datetime import datetime
import yaml
import os
import sys
import re
import markdown
from html import escape


FEED_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"

BLSKY_DOMAIN = "bsky.app"  # Recognized Bluesky domain

PROFILE_URL = "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile"

# Cache for profile names to avoid repeated API calls
profile_cache = {}

user_handle="bussilab.org"
profile_handle="bussilab.org"
# Configuration
ALLOWED_DOMAINS = ['disq.us', 'bit.ly', 't.co', 'doi.org', 'prereview.org', 'cecam.org']
MAX_DISPLAY_LENGTH = 25

# Define the base URL for hashtag queries
archive_base_url = "./news?query="

def linkify_hashtags(text):
    """
    Replaces hashtags with clickable links to the News Archive page with a pre-filled query.
    Handles cases where hashtags are followed by punctuation marks.
    """
    hashtag_pattern = re.compile(r"(?<!\w)#(\w+)(?=[\s.,!?;:]|$)")
    return hashtag_pattern.sub(r'<a href="' + archive_base_url + r'%23\1">#\1</a>', text)


def fetch_authorfeed(actor):
    params = {"actor": actor}
    response = requests.get(FEED_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

def fetch_authorprofile(actor):
    params = {"actor": actor}
    response = requests.get(PROFILE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

def replace_links_with_html(text, facets):
    """
    Replaces link-type facets in the text with HTML anchor tags.
    Handles byte-based indices to account for multi-byte characters like emojis.
    """

    # Convert text to bytes
    text_bytes = text.encode("utf-8")

    # Filter for link facets only
    link_facets = [
        facet for facet in facets
        if facet.get("features", [{}])[0].get("$type") == "app.bsky.richtext.facet#link"
    ]

    # Sort facets by byteStart in descending order
    link_facets.sort(key=lambda f: f["index"]["byteStart"], reverse=True)

    # Replace links using byteStart and byteEnd
    for facet in link_facets:
        uri = facet["features"][0]["uri"]
        start = facet["index"]["byteStart"]
        end = facet["index"]["byteEnd"]

        # Extract the link text from bytes
        link_text_bytes = text_bytes[start:end]
        link_text = link_text_bytes.decode("utf-8")

        # Create the replacement in bytes
        replacement = f'<a href="{uri}" target="_blank">{link_text}</a>'.encode("utf-8")

        # Replace in the byte array
        text_bytes = text_bytes[:start] + replacement + text_bytes[end:]

    # Convert bytes back to string
    return text_bytes.decode("utf-8")

def get_display_name(handle):
    """
    Fetches the display name for a given handle using Bluesky API.
    Caches results to avoid redundant calls.
    """
    if handle in profile_cache:
        return profile_cache[handle]  # Return cached result

    profile = fetch_authorprofile(handle)
    if profile and "displayName" in profile:
        display_name = profile["displayName"]
        profile_cache[handle] = display_name  # Cache the result
        return display_name
    else:
        return handle  # Fallback to original handle if not found

def replace_handles_with_display_names(post_text):
    """
    Replaces @handles in the text with their corresponding display names.
    """
    handle_pattern = re.compile(r"@([a-zA-Z0-9_\.\-]+)")  # Match handles like @xxxx
    return handle_pattern.sub(lambda match: get_display_name(match.group(1)), post_text)

# Function to format the text with the '|' style
def convert_to_yaml(data):
    if len(data)==0: return ""

    # Customize the YAML dumper to always use the block scalar style for multiline text
    class IndentedTextDumper(yaml.Dumper):
        def represent_scalar(self, tag, value, style=None):
            if "\n" in value:  # Use block style for multiline text
                style = "|"
            return super().represent_scalar(tag, value, style)

    # Dump the data to YAML
    return yaml.dump(data, Dumper=IndentedTextDumper, sort_keys=False)

def processfeed(profile_handle,feed):
    posts=[]
    for post in feed["feed"]:
        if not "reason" in post and not "reply" in post:
            timestamp=post["post"]["record"]["createdAt"]
            date=datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").date()
            uri=post["post"]["uri"]
            post_id = uri.split("/")[-1]  # Extracts "3lbei2pbnok2y"
            url = f"https://bsky.app/profile/{profile_handle}/post/{post_id}"
            text=post["post"]["record"]["text"]
            if "facets" in post["post"]["record"]:
               text=replace_links_with_html(text, post["post"]["record"]["facets"])
            posts.append(
                {"date":  str(date),
                 "text": text,
                 "uri": uri,
                 "url": url
                })
    return posts

def get_current_urls(path):
    with open(path) as f:
        urls=[]
        for post in yaml.safe_load(f):
            if "url" in post:
                urls.append(post["url"])
        return urls

def render_markdown(text):
    """Convert Markdown to HTML."""
    return markdown.markdown(text)


def preformat_text(content):
    """Process text for URLs after rendering Markdown."""
    # Placeholder to temporarily store <a> tags
    anchor_placeholders = []

    # Step 1: Temporarily remove <a> tags
    def replace_anchor(match):
        anchor_placeholders.append(match.group(0))
        return f"ANCHOR_PLACEHOLDER_{len(anchor_placeholders) - 1}"

    content = re.sub(r'<a [^>]+>.*?<\/a>', replace_anchor, content, flags=re.IGNORECASE)

    # Step 2: Process remaining text for URLs
    def format_url(match):
        full_url = match.group(0)

        # Separate trailing punctuation and HTML tags
        trailing_punctuation_match = re.search(r'([.,:!]+)?(<\/?\w+.*?>)?$', full_url)
        trailing_punctuation = trailing_punctuation_match.group(1) if trailing_punctuation_match else ""
        trailing_tag = trailing_punctuation_match.group(2) if trailing_punctuation_match else ""

        # Remove trailing punctuation and tags from the URL
        url_without_trailing = re.sub(r'([.,:!]+)?(<\/?\w+.*?>)?$', '', full_url)

        # Determine if the URL is complete (starts with http/https)
        is_full_url = url_without_trailing.startswith("http://") or \
                      url_without_trailing.startswith("https://")

        # Format the display URL (strip "http://", "https://")
        display_url = re.sub(r'https?://', '', url_without_trailing)
        shortened_display = (display_url[:MAX_DISPLAY_LENGTH] + '...') if len(display_url) > MAX_DISPLAY_LENGTH else display_url

        # Determine final URL (add https:// for partial URLs)
        if not is_full_url:
            domain = url_without_trailing.split('/')[0]  # Extract domain
            if domain in ALLOWED_DOMAINS:
                final_url = f"https://{url_without_trailing}"
            else:
                return full_url  # Leave non-whitelisted partial URLs unchanged
        else:
            final_url = url_without_trailing

        # Return the clickable link with preserved punctuation and trailing HTML tags
        return (
            f'<a href="{final_url}" target="_blank">{shortened_display}</a>'
            + (trailing_punctuation or "")
            + (trailing_tag or "")
        )

    # Regex to match full and partial URLs
    url_pattern = re.compile(
        r'((https?:\/\/[\w.-]+\.[a-z]{2,}(\/\S*)?)|([\w.-]+\.[a-z]{2,}\/\S*))'
    )
    content = re.sub(url_pattern, format_url, content)

    # Step 3: Restore original <a> tags
    def restore_anchor(match):
        index = int(match.group(1))
        return anchor_placeholders[index]

    content = re.sub(r'ANCHOR_PLACEHOLDER_(\d+)', restore_anchor, content)

    return content





def process_posts(posts_file, formatted_file):
    """Process posts to generate a formatted text dictionary."""
    with open(posts_file, 'r') as file:
        posts = yaml.safe_load(file)

    formatted_posts = {}

    for post in posts:
        if 'text' in post:
            original_text = post['text']
            # Step 1: Render Markdown
            rendered_text = render_markdown(original_text)
            # Step 2: Format hashtags
            rendered_text = linkify_hashtags(rendered_text)
            # Step 3: Preformat links
            formatted_text = preformat_text(rendered_text)
            # Step 4: fix bsky handles
            if "url" in post and BLSKY_DOMAIN in post["url"]: # Only process Bluesky posts
                formatted_text = replace_handles_with_display_names(formatted_text)
            # Store the formatted text using the URL as the key
            formatted_posts[post['url']] = formatted_text

    # Write to the formatted posts file
    with open(formatted_file, 'w') as file:
        yaml.safe_dump(formatted_posts, file, allow_unicode=True)

    print(f"Formatted posts saved to {formatted_file}")


if __name__ == "__main__":
    posts_file="_data/posts.yml"

    labfeed=fetch_authorfeed(profile_handle)

    print(labfeed)

    current_urls=get_current_urls(posts_file)
    posts=[item for item in processfeed(profile_handle,labfeed) if not item["url"] in current_urls]

    add_posts=convert_to_yaml(posts)

    with open(posts_file) as f:
        lines = [line for line in f]

    newlines=[]
    done=False
    for line in lines:
        if not done and line[0]=="-":
            newlines.append(add_posts)
            done=True
        newlines.append(line)
    if not done:
        newlines.append(add_posts)
    with open(posts_file,"w") as f:
        for line in newlines:
            print(line,end="",file=f)
            print(line,end="")

    with open(posts_file) as f:
       text=f.read()


    process_posts(posts_file,re.sub(".yml$","_preformatted_text.yml",posts_file))


