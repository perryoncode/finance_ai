from supabase import create_client, Client
import os
import time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  

_supabase: Client | None = None
_last_refresh = 0
_REFRESH_INTERVAL = 60 * 55 

def get_supabase():
    global _supabase, _last_refresh
    now = time.time()
    if _supabase is None or (now - _last_refresh) > _REFRESH_INTERVAL:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        _last_refresh = now
    return _supabase

def authed_postgrest(access_token: str | None):
    """
    Returns a PostgREST client with user's JWT attached (RLS enforced)
    """
    pg = get_supabase().postgrest
    if access_token:
        pg = pg.auth(access_token)
    return pg
