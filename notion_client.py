"""
Fix a Python 3.5 compatibility issue with the status= keyword to urllib3.Retry.

Once this pull request is merged, can kill this module:

    https://github.com/jamalex/notion-py/pull/121
"""

import hashlib
from requests import Session
from requests.adapters import HTTPAdapter
from requests.cookies import cookiejar_from_dict
from requests.packages.urllib3.util.retry import Retry

from notion.monitor import Monitor
from notion.store import RecordStore

from notion import client as nc


def create_session():
    """
    retry on 502
    """
    session = Session()
    retry = Retry(
        # NOTE: This was the only change made.
        5,
        # status=5
        backoff_factor=0.3,
        status_forcelist=(502,),
        # CAUTION: adding 'POST' to this list which is not technically idempotent
        method_whitelist=("POST", "HEAD", "TRACE", "GET", "PUT", "OPTIONS", "DELETE"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session



class NotionClientPy35(nc.NotionClient):
    """
    This is the entry point to using the API. Create an instance of this class, passing it the value of the
    "token_v2" cookie from a logged-in browser session on Notion.so. Most of the methods on here are primarily
    for internal use -- the main one you'll likely want to use is `get_block`.
    """

    def __init__(self, token_v2, monitor=False, start_monitoring=False, enable_caching=False, cache_key=None):
        self.session = create_session()
        self.session.cookies = cookiejar_from_dict({"token_v2": token_v2})
        if enable_caching:
            cache_key = cache_key or hashlib.sha256(token_v2.encode()).hexdigest()
            self._store = RecordStore(self, cache_key=cache_key)
        else:
            self._store = RecordStore(self)
        if monitor:
            self._monitor = Monitor(self)
            if start_monitoring:
                self.start_monitoring()
        else:
            self._monitor = None
        self._update_user_info()
