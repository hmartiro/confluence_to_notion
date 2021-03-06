#!/usr/bin/env python3
import logging
import os
import re
import sys
import urllib

from notion_client import NotionClientPy35
from notion import block as nb


def main(client, notion_import_url, confluence_export_dir, space_name, dry_run=False):
    """
    Fix up Notion pages imported from Confluence HTML export.

    Args:
        client (NotionClient):
        notion_import_url (str): Notion URL to import summary page
        confluence_export_dir (str): Local directory containing Confluence HTML export
        space_name (str): Name of the exported Confluence space
        dry_run (bool): Print, don't execute
    """
    # Get the summary page as a block
    logging.info('Notion import URL: {}'.format(notion_import_url))
    summary_page = client.get_block(notion_import_url)

    # Fix each child page
    for blk in summary_page.children:
        if isinstance(blk, nb.PageBlock):
            logging.info('Fixing page: "{}"'.format(blk.title))
            fix_confluence_notion_html_import(
                client=client,
                confluence_export_dir=confluence_export_dir,
                page=blk,
                dry_run=dry_run,
                space_name=space_name,
            )


def children_recursive(element):
    """
    Traverse the tree and recursively yield all child elements.

    Args:
        element (nb.Block):

    Returns:
        generator(nb.Block):
    """
    for blk in element.children:
        yield from children_recursive(blk)
        yield blk


def fix_confluence_notion_html_import(
    client, page, confluence_export_dir, space_name, dry_run=False
):
    """
    Fix up one Notion page imported from Confluence HTML export.

    Args:
        client (NotionClient):
        page (nb.PageBlock):
        confluence_export_dir (str):
        space_name (str):
        dry_run (bool):
    """
    blocks_to_delete = []

    if page.title == 'index':
        # If it's the index page, delete
        logging.info('Found dummy index page, deleting.')
        if not dry_run:
            page.remove()
        return
    elif not page.children[0].title.startswith('[{}'.format(space_name)):
        logging.error('Aborting, I don\'t recognize this page format.')
        return

    blocks_to_delete.append(page.children[0])

    # Set title from the second block, stripping out some crap
    original_title = page.title
    new_title = original_title
    if isinstance(page.children[1], nb.HeaderBlock):
        expected_title = '{} : '.format(space_name)
        if page.children[1].title.startswith(expected_title):
            new_title = page.children[1].title[len(expected_title) :]
            if not dry_run:
                page.title = new_title
            blocks_to_delete.append(page.children[1])

    # Print title
    if original_title == new_title:
        logging.info('Title: "{}"'.format(new_title))
    else:
        logging.info('Title: "{}" --> "{}"'.format(original_title, new_title))

    # Delete the now first block which is a broken space link
    if isinstance(page.children[2], nb.HeaderBlock):
        if page.children[2].title.startswith('Created by'):
            note = 'Imported from Confluence page c' + page.children[2].title[1:]
            if not dry_run:
                callout = page.children.add_new(nb.CalloutBlock, title=note)
                callout.icon = '💡'
                callout.move_to(page.children[2], "after")
            blocks_to_delete.append(page.children[2])

    # Find all incorrectly imported image blocks
    image_blocks_to_replace = []
    for blk in children_recursive(page):
        if isinstance(blk, nb.ImageBlock):
            if blk.source.startswith('attachments/'):
                # This is a relative image which we'll upload to S3 and replace
                image_blocks_to_replace.append(blk)
            elif blk.source.startswith('https://skydio.atlassian.net/secure/viewavatar'):
                # This is a JIRA ticket avatar image which we'll delete
                blocks_to_delete.append(blk)
            elif 'images/icons/emoticons' in blk.source:
                # This is an emoticon relative link which doesn't work
                blocks_to_delete.append(blk)

    # Fix image blocks
    logging.info('Fixing {} broken image blocks...'.format(len(image_blocks_to_replace)))
    for broken_image_block in image_blocks_to_replace:
        # Pull out the on-disk directory from the broken URL
        parsed = urllib.parse.urlparse(broken_image_block.source)
        local_image_path = os.path.join(confluence_export_dir, parsed.path)

        query_dict = urllib.parse.parse_qs(parsed.query)
        if 'width' in query_dict:
            width = int(query_dict['width'][0])
        else:
            width = None

        blocks_to_delete.append(broken_image_block)

        if not os.path.exists(local_image_path):
            logging.error('Image not found: {}'.format(local_image_path))
            continue

        logging.info('Uploading image (width={}): {}'.format(width, local_image_path))

        if dry_run:
            continue

        # Create a new block by uploading the image to Notion S3
        new_image_block = page.children.add_new(nb.ImageBlock, width=width)
        new_image_block.upload_file(local_image_path)

        # Replace old block
        new_image_block.move_to(broken_image_block, "after")

    # Delete some other unwanted blocks
    found = False
    for blk in page.children:
        # Delete everything after and including the attachments header
        if isinstance(blk, nb.SubheaderBlock) and blk.title == 'Attachments:':
            found = True
        if found:
            blocks_to_delete.append(blk)

        # Also delete this footer
        if isinstance(blk, nb.TextBlock) and blk.title.startswith('Document generated by'):
            blocks_to_delete.append(blk)

        # Also delete this footer
        if isinstance(blk, nb.TextBlock) and blk.title.startswith('[Atlassian'):
            blocks_to_delete.append(blk)

    # Actually delete all blocks
    for blk in blocks_to_delete:
        logging.info('Removing {}: {}'.format(blk.__class__.__name__, blk))
        if not dry_run:
            blk.remove()


def get_subpage_titles_to_url(page):
    """
    Return a dict of immediate subpage titles to Notion page URL.

    Args:
        page (nb.PageBlock):

    Returns:
        dict(str, str): title -> URL
    """
    data = dict()
    for block in page.children:
        if isinstance(block, nb.PageBlock):
            data[block.title] = block.get_browseable_url()
    return data


# Pattern for matching links
PAGE_LINK_PATTERN = re.compile(r'\[(?P<title>.+)\]\((?P<confluence_page_id>.+)\)')


def fix_page_links(title_to_url, page):
    """
    Fix the links on the given page using the dict of titles to URLs.

    Args:
        title_to_url (dict):
        page (nb.PageBlock):
    """
    for block in children_recursive(page):
        if isinstance(block, nb.PageBlock):
            logging.info('=== Page: {} ==='.format(block.title))

        if not hasattr(block, 'title'):
            continue

        for match in PAGE_LINK_PATTERN.finditer(block.title):
            title = match.groupdict()['title']
            if title not in title_to_url:
                logging.warning('Unmatched URL: "{}"'.format(title))
                continue
            url = title_to_url[title]

            logging.info('Fixing link for "{}"'.format(title))
            block.title = block.title.replace(match.string, '[{}]({})'.format(title, url))


if __name__ == '__main__':
    import argparse

    # Set log level
    logging.root.setLevel(logging.INFO)

    # Read auth token
    notion_token = os.environ.get('NOTION_TOKEN', '')
    if not notion_token:
        logging.critical(
            'Set NOTION_TOKEN environment variable by inspecting your browser '
            'on a logged-in session to Notion.so.'
        )
        sys.exit(1)

    # Create client
    client = NotionClientPy35(token_v2=notion_token)

    # Parse args
    parser = argparse.ArgumentParser(description='Fix Confluence to Notion HTML importing.')
    parser.add_argument(
        '--confluence-dir', required=True, type=str, help='Confluence HTML export directory'
    )
    parser.add_argument(
        '--notion-url', required=True, type=str, help='Notion import summary page URL'
    )
    parser.add_argument(
        '--space-name', type=str, default='Software', help='Exported Confluence Space name'
    )
    parser.add_argument('--dry-run', action='store_true', help='Print actions but don\'t execute.')
    parser.add_argument(
        '--fix-links', action='store_true', help='Try to fix links to known imported pages.'
    )

    args = parser.parse_args()

    # Run
    main(
        client=client,
        notion_import_url=args.notion_url,
        confluence_export_dir=args.confluence_dir,
        space_name=args.space_name,
        dry_run=args.dry_run,
    )

    if args.fix_links:
        # Get mapping of page title to Notion URL from the import page
        import_page = client.get_block(args.notion_url)
        title_to_url = get_subpage_titles_to_url(import_page)
        logging.info('Made title->URL dict with {} entries.'.format(len(title_to_url)))

        # Fix page links
        fix_page_links(title_to_url, import_page)
