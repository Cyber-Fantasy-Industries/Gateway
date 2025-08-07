# globals.py
import os, uuid
from zep_cloud.client import AsyncZep, Zep

API_KEY = os.getenv("ZEP_API_KEY")
USER_ID = os.getenv("ZEP_USER_ID") or "default_user"
THREAD_ID = os.getenv("ZEP_THREAD_ID") or uuid.uuid4().hex
GROUP_GRAPH_ID = os.getenv("ZEP_GRAPH_ID") or "global_knowledge"

# Die Clients werden *bei Bedarf* gebaut:
sync_zep_client = Zep(api_key=API_KEY)
async_zep_client = AsyncZep(api_key=API_KEY)
