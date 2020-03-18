# confluence_to_notion
Improve Notion pages imported from a Confluence HTML export using the unofficial [Notion API](https://github.com/jamalex/notion-py) to fix up common issues.

The current state of exporting from Confluence into Notion is that images
and attachments are broken, titles are broken, and there are a bunch of
annoying formatting issues. This fixes some of those.

Currently handles:  
1) Deleting extraneous cells at the start of the page  
2) Setting the page title properly  
3) Properly uploading and showing images  
4) Deleting the extraneous "Attachments" section at the end 
5) Deleting JIRA ticket type images that show up huge
6) Adding a callout that shows when the confluence page was made 
7) Delete emoticon images that become broken

Does not handle: 
1) Links to other confluence pages
2) Handle videos, PDFs and arbitrary other attachments?
3) Callout should link back to original confluence page

# Usage

### 1) Export from Confluence to HTML

Space Settings -> Content Tools -> Export -> HTML -> Custom Export -> Deselect All

Select the pages you want -> Export -> Download Here -> Unzip

Save the path of this folder, it will be passed to the script.

### 2) Import HTML into Notion

... -> Import -> HTML -> Select all HTML pages in the unzipped folder

This will create a page like "Import Mar 18, 2020". You should see the subpages underneath
along with an index page.

Save the URL of this page, it will be passed to the script.

### 3) Set your Notion cookie

In a browser session where you're logged into Notion.so, open:  
`chrome://settings/cookies/detail?site=www.notion.so`

Find the `token_v2` entry and copy the Content.

Set this as an environment variable as follows:  
`export NOTION_TOKEN=8e8ec87b5cf11f4e354fb1d145f78ca...`

### 4) Run confluence_to_notion

Install requirements (just the unofficial Notion API):  
`sudo pip3 install -r requirements.txt`

Test with dry run:  
`python3 confluence_to_notion.py --confluence ~/Downloads/Confluence_Export --notion https://www.notion.so/blah/Path-To-Page --dry-run`

If that looks good and prints the right titles and images, run without `--dry-run`.  
This can take a while as it recursively parses all blocks and uploads a bunch of images to S3 through Notion.

Notion will live update as the script runs.
