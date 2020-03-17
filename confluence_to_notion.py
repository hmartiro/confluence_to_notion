#!/usr/bin/env python3
import logging
import os
import urllib

from notion.client import NotionClient
from notion import block


def fix_confluence_notion_html_import(client, confluence_export_dir, notion_page_url,
                                      dry_run=False):
    """
    Fix up an HTML page imported from Confluence to Notion.

    Args:
        client (NotionClient):
        confluence_export_dir (str): Path to directory containing Confluence HTML export
        notion_page_url (str): URL of Notion page imported from the HTML
        dry_run (bool): Just print what you'll do
    """
    # Get the page as a block
    logging.info(f'Notion page: {notion_page_url}')
    page = client.get_block(notion_page_url)

    # Set title from the second block, stripping out some crap
    original_title = page.title
    new_title = original_title
    if isinstance(page.children[1], block.HeaderBlock):
        if page.children[1].title.startswith('Software : '):
            new_title = page.children[1].title[len('Software : '):]
            if not dry_run:
                page.title = new_title
                page.children[1].remove()

    # Print title
    if original_title == new_title:
        print(f'Title: "{new_title}"')
    else:
        print(f'Title: "{original_title}" --> "{new_title}"')

    # Delete the first block which is a broken space link
    if page.children[0].title == '[Software](index.html)' and not dry_run:
        page.children[0].remove()
    
    # Delete the first block which is a broken space link
    if page.children[0].title.startswith('Created by') and not dry_run:
        note = 'Imported from Confluence page c' + page.children[0].title[1:]
        callout = page.children.add_new(block.CalloutBlock, title=note)
        callout.icon = '💡'
        callout.move_to(page.children[0], "after")
        page.children[0].remove()

    # Traverse the block tree
    def children_recursive(block):
        for blk in block.children:
            yield from children_recursive(blk)
            yield blk

    # Find all incorrectly imported image blocks
    image_blocks_to_replace = []
    for blk in children_recursive(page):
        if isinstance(blk, block.ImageBlock):
            if blk.source.startswith('attachments/'):
                image_blocks_to_replace.append(blk)

    # Fix image blocks
    print(f'Fixing {len(image_blocks_to_replace)} broken image blocks...')
    for broken_image_block in image_blocks_to_replace:
        # Pull out the on-disk directory from the broken URL
        parsed = urllib.parse.urlparse(broken_image_block.source)
        local_image_path = os.path.join(confluence_export_dir, parsed.path)

        query_dict = urllib.parse.parse_qs(parsed.query)
        if 'width' in query_dict:
            width = int(query_dict['width'][0])
        else:
            width = None
    
        print(f'Uploading image (width={width}): {local_image_path}')
        if dry_run:
            continue

        # Create a new block by uploading the image to Notion S3
        new_image_block = page.children.add_new(block.ImageBlock, width=width)
        new_image_block.upload_file(local_image_path)
        
        # Replace old block
        new_image_block.move_to(broken_image_block, "after")
        broken_image_block.remove()


# Confluence HTML export directory
confluence_export_dir = '/Users/hayk/Downloads/confluence_export'

# Notion page to fix up
notion_page_url = 'https://www.notion.so/link/to/My-Page'

# Create Notion client
# Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so
token = 'to_be_filled_in'
client = NotionClient(token_v2=token)

# Run
fix_confluence_notion_html_import(
    client=client,
    confluence_export_dir=confluence_export_dir,
    notion_page_url=notion_page_url,
    dry_run=False
)
