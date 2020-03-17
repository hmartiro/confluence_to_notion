# confluence_to_notion
Improve Confluence to Notion HTML exporting using the unofficial [Notion API](https://github.com/jamalex/notion-py).

The current state of exporting from Confluence into Notion is that images
and attachments are broken, titles are broken, and there are a bunch of
annoying formatting issues.

It assumes you've taken the following steps:
    1) Export part of a space from Confluence to HTML and download locally
    2) Import HTML into Notion
    3) Found the URL of an imported Notion page you want to fix up

Currently handles:
    1) Deleting extraneous cells at the start of the page
    2) Setting the page title properly
    3) Properly uploading and showing images

TODOs:
    1) Automatically get list of imported Notion pages, don't call this one by one
    2) Remove "Attachments" section at the bottom of imported pages
    3) Handle videos, PDFs and arbitrary other attachments?

## Running

Build:
`sudo pip3 install -r requirements.txt`

Run:
`python3 confluence_to_notion.py`
