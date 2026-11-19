"""Look for authenticated updates; never alter user preferences or game saves."""
import urllib.request
from update_security import verify_manifest, validate_https_url, version_tuple, UpdateSecurityError

class UpdateNetworkError(RuntimeError):
    pass

def read_limited_https(url, max_bytes=65536, *, opener=None, timeout=12):
    validate_https_url(url)
    fetch = opener or urllib.request.urlopen
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SnowRunnerHelper-Updater/1',
                                                   'Accept': 'application/json'})
        with fetch(req, timeout=timeout) as response:
            # urllib follows redirects; reject any downgrade after redirection.
            validate_https_url(response.geturl())
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise UpdateNetworkError('Release manifest is too large')
        return data
    except (OSError, TimeoutError) as exc:
        raise UpdateNetworkError('Cannot reach the update server') from exc

def check_for_update(url, pubkey, current_version, channel='stable', *, opener=None):
    if not url or not pubkey:
        raise UpdateSecurityError('OTA is not configured: release URL and public key required')
    raw = read_limited_https(url, opener=opener)
    rel = verify_manifest(raw, pubkey, channel=channel)
    return rel if version_tuple(rel.version) > version_tuple(current_version) else None
