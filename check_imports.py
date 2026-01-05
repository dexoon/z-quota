import sys
try:
    import aiohttp
    print("aiohttp ok")
except ImportError:
    print("aiohttp missing")
    sys.exit(1)
