#!/usr/bin/env python3
"""
EDL Test Suite - List Generator
Generates realistic IP, URL, and domain lists for PAN-OS EDL testing at scale.
One entry per line, # comments, UTF-8. Compatible with PAN-OS EDL format.

Usage:
    python generate_lists.py [--output-dir lists] [--entries 20000] [--seed 42]
"""
import argparse
import ipaddress
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Real ARIN/RIPE/APNIC/LACNIC/AFRINIC IPv4 allocations
# ---------------------------------------------------------------------------
PUBLIC_IPV4_RANGES = [
    # AWS
    ("3.0.0.0",   "3.255.255.255"),
    ("13.32.0.0", "13.63.255.255"),
    ("18.116.0.0","18.119.255.255"),
    ("44.192.0.0","44.255.255.255"),
    ("52.0.0.0",  "52.255.255.255"),
    ("54.0.0.0",  "54.255.255.255"),
    # Google Cloud / Infrastructure
    ("8.8.0.0",   "8.8.255.255"),
    ("34.0.0.0",  "34.127.255.255"),
    ("35.184.0.0","35.255.255.255"),
    ("142.250.0.0","142.251.255.255"),
    # Cloudflare
    ("1.0.0.0",   "1.1.255.255"),
    ("104.16.0.0","104.31.255.255"),
    ("172.64.0.0","172.71.255.255"),
    # Microsoft Azure
    ("13.64.0.0", "13.127.255.255"),
    ("20.0.0.0",  "20.255.255.255"),
    ("40.64.0.0", "40.127.255.255"),
    ("51.0.0.0",  "51.255.255.255"),
    # Akamai CDN
    ("23.0.0.0",  "23.255.255.255"),
    ("104.64.0.0","104.127.255.255"),
    ("184.24.0.0","184.31.255.255"),
    # Fastly
    ("151.101.0.0","151.101.255.255"),
    ("199.232.0.0","199.232.255.255"),
    # Comcast (US)
    ("73.0.0.0",  "73.255.255.255"),
    ("96.0.0.0",  "96.255.255.255"),
    ("98.0.0.0",  "98.127.255.255"),
    # AT&T (US)
    ("12.0.0.0",  "12.255.255.255"),
    ("65.0.0.0",  "65.127.255.255"),
    # Verizon (US)
    ("70.0.0.0",  "70.127.255.255"),
    ("174.192.0.0","174.207.255.255"),
    # Cox / Charter (US)
    ("68.0.0.0",  "68.127.255.255"),
    ("71.56.0.0", "71.63.255.255"),
    # RIPE - European ISPs
    ("5.0.0.0",   "5.255.255.255"),
    ("37.0.0.0",  "37.255.255.255"),
    ("46.0.0.0",  "46.255.255.255"),
    ("62.0.0.0",  "62.255.255.255"),
    ("77.0.0.0",  "77.255.255.255"),
    ("78.0.0.0",  "78.255.255.255"),
    ("79.0.0.0",  "79.255.255.255"),
    ("80.0.0.0",  "80.255.255.255"),
    ("81.0.0.0",  "81.255.255.255"),
    ("85.0.0.0",  "85.255.255.255"),
    ("87.0.0.0",  "87.255.255.255"),
    ("88.0.0.0",  "88.255.255.255"),
    ("91.0.0.0",  "91.255.255.255"),
    ("176.0.0.0", "176.255.255.255"),
    ("185.0.0.0", "185.255.255.255"),
    ("193.0.0.0", "193.255.255.255"),
    ("194.0.0.0", "194.255.255.255"),
    ("195.0.0.0", "195.255.255.255"),
    # APNIC - Asia Pacific
    ("1.128.0.0", "1.255.255.255"),
    ("14.0.0.0",  "14.255.255.255"),
    ("27.0.0.0",  "27.255.255.255"),
    ("36.0.0.0",  "36.255.255.255"),
    ("42.0.0.0",  "42.255.255.255"),
    ("49.0.0.0",  "49.255.255.255"),
    ("58.0.0.0",  "58.255.255.255"),
    ("59.0.0.0",  "59.255.255.255"),
    ("60.0.0.0",  "60.255.255.255"),
    ("61.0.0.0",  "61.255.255.255"),
    ("101.0.0.0", "101.255.255.255"),
    ("103.0.0.0", "103.255.255.255"),
    ("110.0.0.0", "110.255.255.255"),
    ("111.0.0.0", "111.255.255.255"),
    ("112.0.0.0", "112.255.255.255"),
    ("113.0.0.0", "113.255.255.255"),
    ("114.0.0.0", "114.255.255.255"),
    ("115.0.0.0", "115.255.255.255"),
    ("116.0.0.0", "116.255.255.255"),
    ("117.0.0.0", "117.255.255.255"),
    ("118.0.0.0", "118.255.255.255"),
    ("119.0.0.0", "119.255.255.255"),
    ("120.0.0.0", "120.255.255.255"),
    ("121.0.0.0", "121.255.255.255"),
    ("122.0.0.0", "122.255.255.255"),
    ("123.0.0.0", "123.255.255.255"),
    ("124.0.0.0", "124.255.255.255"),
    ("125.0.0.0", "125.255.255.255"),
    ("150.0.0.0", "150.255.255.255"),
    ("163.0.0.0", "163.255.255.255"),
    ("180.0.0.0", "180.255.255.255"),
    ("182.0.0.0", "182.255.255.255"),
    ("183.0.0.0", "183.255.255.255"),
    ("202.0.0.0", "202.255.255.255"),
    ("203.0.0.0", "203.255.255.255"),
    ("210.0.0.0", "210.255.255.255"),
    ("218.0.0.0", "218.255.255.255"),
    ("219.0.0.0", "219.255.255.255"),
    ("220.0.0.0", "220.255.255.255"),
    ("221.0.0.0", "221.255.255.255"),
    # LACNIC - Latin America
    ("177.0.0.0", "177.255.255.255"),
    ("179.0.0.0", "179.255.255.255"),
    ("186.0.0.0", "186.255.255.255"),
    ("187.0.0.0", "187.255.255.255"),
    ("189.0.0.0", "189.255.255.255"),
    ("190.0.0.0", "190.255.255.255"),
    ("191.0.0.0", "191.255.255.255"),
    ("200.0.0.0", "200.255.255.255"),
    ("201.0.0.0", "201.255.255.255"),
    # AFRINIC
    ("41.0.0.0",  "41.255.255.255"),
    ("102.0.0.0", "102.255.255.255"),
    ("105.0.0.0", "105.255.255.255"),
    ("154.0.0.0", "154.255.255.255"),
    ("196.0.0.0", "196.255.255.255"),
    ("197.0.0.0", "197.255.255.255"),
]

PRIVATE_IPV4_RANGES = [
    ("10.0.0.0",   "10.255.255.255"),
    ("172.16.0.0", "172.31.255.255"),
    ("192.168.0.0","192.168.255.255"),
    ("100.64.0.0", "100.127.255.255"),  # CGNAT
]

# IPv6: 32-bit high-word (groups 1-2) for known global allocations
IPV6_HIGH_WORDS = [
    0x20014860,  # Google
    0x2607f8b0,  # Google US
    0x24046800,  # Google APAC
    0x2a001450,  # Google Europe
    0x26064700,  # Cloudflare
    0x2400cb00,  # Cloudflare APAC
    0x2803f800,  # Cloudflare LATAM
    0x26001f18,  # AWS us-east-1
    0x26001f1c,  # AWS us-west-2
    0x26001f10,  # AWS us-east-2
    0x2a05d07c,  # AWS eu-west
    0x24060da0,  # AWS ap-southeast
    0x26031000,  # Azure global-1
    0x26031010,  # Azure global-2
    0x26031020,  # Azure global-3
    0x26031030,  # Azure global-4
    0x26031040,  # Azure global-5
    0x2a044e42,  # Fastly
    0x26001400,  # Akamai
    0x2a0226f0,  # Akamai EU
    0x200119f0,  # Vultr
    0x200141d0,  # OVH
    0x2a014f8a,  # Hetzner
    0x2604a880,  # DigitalOcean
    0x24008900,  # Linode/Akamai APAC
    0x20010558,  # AT&T
    0x2001db8a,  # Comcast
    0x20012000,  # Telia (Sweden)
    0x20011900,  # Teligent/NTT
    0x20010468,  # Internet2
    0x24080000,  # China Telecom
    0x24080400,  # China Telecom-2
    0x24090000,  # China Unicom
    0xfc000001,  # ULA private fc00::/8
    0xfd000001,  # ULA private fd00::/8
    0xfe800000,  # Link-local fe80::/10
]

CIDR_PREFIXES_V4 = [16, 18, 19, 20, 21, 22, 22, 23, 23, 24, 24, 24, 24, 24]
CIDR_PREFIXES_V6 = [32, 48, 48, 56, 64, 64]

# ---------------------------------------------------------------------------
# Domain components
# ---------------------------------------------------------------------------
SUBDOMAIN_PREFIXES = [
    "api", "cdn", "static", "assets", "media", "images", "files", "data",
    "auth", "login", "sso", "portal", "gateway", "edge", "proxy", "app",
    "web", "mail", "smtp", "mx", "ns1", "ns2", "vpn", "remote",
    "secure", "ssl", "s3", "blob", "storage", "backup", "archive",
    "monitor", "metrics", "logs", "events", "stream", "push", "pull",
    "admin", "manage", "control", "dashboard", "console", "panel",
    "dev", "staging", "stage", "qa", "test", "prod", "uat", "sandbox",
    "us-east", "us-west", "eu-west", "eu-central", "ap-southeast", "ap-northeast",
    "update", "download", "install", "release", "patch",
    "shop", "store", "checkout", "cart", "pay", "payments",
    "account", "profile", "billing", "invoice", "subscription",
    "support", "help", "docs", "wiki", "kb", "community", "forum",
    "chat", "video", "stream", "live", "broadcast", "meeting",
    "search", "index", "find",
    "telemetry", "analytics", "track", "collect", "insight",
    "partner", "affiliate", "ad", "pixel", "beacon",
    "feed", "rss", "sync", "notify", "push",
    "git", "repo", "registry", "artifact", "build", "ci", "cd",
    "ml", "ai", "model", "inference", "llm",
    "geo", "map", "location", "ip",
    "intranet", "internal", "corp", "extranet",
    "north", "south", "east", "west", "central",
]

SECOND_LEVEL_DOMAINS = [
    # Big tech
    "accenture", "akamai", "amazon", "apple", "azure", "cisco",
    "cloudflare", "dell", "facebook", "github", "google", "ibm",
    "intel", "linkedin", "microsoft", "netflix", "nvidia", "oracle",
    "salesforce", "samsung", "sap", "shopify", "slack", "sony",
    "stripe", "twilio", "uber", "vmware", "zoom", "palantir",
    # Telecom / ISP
    "verizon", "att", "tmobile", "comcast", "charter", "cox",
    "spectrum", "xfinity", "lumen", "centurylink", "frontier",
    # Cloud / Hosting
    "rackspace", "digitalocean", "linode", "vultr", "heroku",
    "vercel", "netlify", "fastly", "cloudfront", "maxcdn", "bunny",
    # Observability
    "datadog", "newrelic", "splunk", "elastic", "sumologic",
    "pagerduty", "opsgenie", "grafana", "prometheus",
    # DevOps
    "jira", "confluence", "bitbucket", "gitlab", "jenkins",
    "terraform", "ansible", "puppet", "hashicorp",
    # Database
    "redis", "mongodb", "cassandra", "mysql", "postgres", "mariadb",
    # Messaging
    "kafka", "rabbitmq", "activemq", "pulsar", "nats", "twilio",
    # Security
    "crowdstrike", "sentinelone", "carbonblack", "cylance",
    "paloaltonetworks", "fortinet", "checkpoint", "zscaler",
    "okta", "duo", "beyondtrust", "cyberark", "thycotic",
    # Realistic fictional
    "techsolutions", "globalnet", "cyberdefend", "netprotect",
    "securelink", "threatblock", "safesurf", "netguard",
    "dataprotect", "privacyshield", "intranetpro", "corpbridge",
    "apexsystems", "nexustech", "quantumnet", "infinitytech",
    "primesystems", "alphatech", "betanet", "gammacloud",
    "deltasec", "omegaprotect", "sigmasystems", "etabridge",
    "zetanet", "kappatech", "lambdacloud", "muprotect",
    "xinet", "pitech", "rhonet", "sigmacloud", "tautech",
    "upsilonnet", "phisystems", "chicloud", "psitech",
    "cloudbridge", "databridge", "netbridge", "securepath",
    "guardnet", "sentrilink", "vaultprotect", "shieldnet",
    "sentrycloud", "watchgate", "barriertech", "fencewall",
    "rampartnet", "bulwarkcloud", "bastiontech", "fortressnet",
]

TLDS_WEIGHTED = (
    [".com"] * 25 + [".net"] * 10 + [".org"] * 8 + [".io"] * 7 + [".co"] * 5
    + [".co.uk", ".de", ".fr", ".nl", ".it", ".es", ".pl", ".se", ".no",
       ".dk", ".fi", ".be", ".at", ".ch", ".pt", ".cz", ".hu", ".ro"]
    + [".ru", ".cn", ".jp", ".kr", ".sg", ".hk", ".tw", ".in", ".au", ".nz"]
    + [".ca", ".mx", ".br", ".ar", ".cl", ".co", ".pe", ".ve"]
    + [".za", ".ng", ".eg", ".ke", ".gh", ".tz"]
    + [".ae", ".sa", ".il", ".tr", ".pk", ".bd"]
    + [".app", ".dev", ".tech", ".cloud", ".services", ".digital",
       ".solutions", ".network", ".systems", ".online", ".security",
       ".global", ".group", ".enterprise", ".business", ".gov", ".edu"]
)

URL_PATHS = [
    "/", "/api/v1/", "/api/v2/", "/api/v3/", "/graphql", "/rpc",
    "/api/v1/users", "/api/v1/accounts", "/api/v1/auth", "/api/v1/sessions",
    "/api/v2/data", "/api/v2/events", "/api/v2/metrics", "/api/v2/reports",
    "/api/v3/telemetry", "/api/v3/analytics", "/api/v3/collect",
    "/login", "/logout", "/signin", "/signout", "/sso",
    "/oauth/authorize", "/oauth/callback", "/oauth/token", "/oauth/revoke",
    "/auth/saml/callback", "/auth/oidc/callback", "/auth/mfa",
    "/static/js/app.min.js", "/static/css/main.min.css",
    "/static/images/logo.png", "/assets/fonts/inter.woff2",
    "/cdn/release/latest/manifest.json", "/cdn/v2/bundle.js",
    "/update/check", "/update/download", "/update/install", "/update/manifest",
    "/health", "/healthz", "/ready", "/live", "/ping", "/status",
    "/metrics", "/stats", "/analytics/collect", "/analytics/event",
    "/upload", "/download", "/export", "/import", "/batch",
    "/webhook", "/callback", "/notify", "/hook", "/event",
    "/admin/", "/admin/dashboard", "/admin/users", "/admin/settings",
    "/portal/home", "/portal/profile", "/portal/billing", "/portal/tokens",
    "/docs/", "/docs/api", "/docs/guide", "/docs/reference", "/docs/changelog",
    "/search", "/find", "/lookup", "/query",
    "/v1/telemetry", "/v2/events/batch", "/v3/analytics/collect",
    "/threat/indicators", "/threat/feed", "/blocklist", "/allowlist",
    "/reputation", "/check", "/verify", "/validate", "/scan",
    "/download/agent", "/download/installer", "/download/certificate",
    "/bootstrap", "/provision", "/register", "/enroll", "/onboard",
    "/config", "/config/update", "/policy/update", "/policy/sync",
    "/crl", "/ocsp", "/ca/cert", "/intermediate/cert", "/root/cert",
    "/ws", "/websocket", "/socket.io", "/realtime", "/sse",
    "/files/", "/uploads/", "/media/", "/content/", "/attachments/",
    "/reports/", "/exports/", "/imports/", "/transforms/",
    "/queue", "/job", "/task", "/worker", "/cron",
    "/v1/ip/reputation", "/v2/url/check", "/v3/domain/lookup",
]

ENCODING_PATHS = [
    "/path%20with%20spaces/resource",
    "/path%2Fwith%2Fslashes",
    "/query?q=hello%20world&lang=en",
    "/api?filter=%5Bactive%5D&page=1",
    "/%E4%B8%AD%E6%96%87/path",       # Chinese characters
    "/%D1%81%D0%B5%D1%82%D1%8C/api",   # Cyrillic
    "/%D8%B4%D8%A8%D9%83%D8%A9/v1",    # Arabic
    "/search?q=%22exact+phrase%22",
    "/filter?tags%5B%5D=security&tags%5B%5D=cloud",
    "/path;param=value/resource",
    "/path/with/../traversal/attempt",
    "/api?callback=__jsonp_cb_1234",
]

# IDN word fragments (Punycode-encodable)
IDN_WORDS = [
    "sécurité", "réseau", "données",    # French
    "sicherheit", "netzwerk", "daten",  # German
    "seguridad", "redcom", "datos",     # Spanish
    "sicurezza", "rete", "dati",        # Italian
    "безопасность", "сеть", "данные",  # Russian (Cyrillic)
    "安全", "网络", "数据",              # Chinese simplified
    "セキュリティ", "ネット", "データ", # Japanese
    "보안", "네트워크", "데이터",       # Korean
    "güvenlik", "ağ", "veri",          # Turkish
    "veiligheid", "netwerk", "gegevens", # Dutch
]

# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------

def _ip4_int(ip: str) -> int:
    return int(ipaddress.IPv4Address(ip))

def _int_ip4(n: int) -> str:
    return str(ipaddress.IPv4Address(n))

def rand_ipv4(start: str, end: str) -> str:
    return _int_ip4(random.randint(_ip4_int(start), _ip4_int(end)))

def rand_ipv4_cidr() -> str:
    start, end = random.choice(PUBLIC_IPV4_RANGES + PRIVATE_IPV4_RANGES)
    pfx = random.choice(CIDR_PREFIXES_V4)
    base = rand_ipv4(start, end)
    return str(ipaddress.IPv4Network(f"{base}/{pfx}", strict=False))

def rand_ipv6() -> str:
    hw = random.choice(IPV6_HIGH_WORDS)
    # hw = top 32 bits; shift to bits [127:96]; fill lower 96 bits randomly
    value = (hw << 96) | random.randint(0, (1 << 96) - 1)
    return str(ipaddress.IPv6Address(value))

def rand_ipv6_cidr() -> str:
    hw = random.choice(IPV6_HIGH_WORDS)
    pfx = random.choice(CIDR_PREFIXES_V6)
    value = (hw << 96) | random.randint(0, (1 << 96) - 1)
    net = ipaddress.IPv6Network(f"{ipaddress.IPv6Address(value)}/{pfx}", strict=False)
    return str(net)

def rand_domain() -> str:
    parts = []
    if random.random() < 0.45:
        parts.append(random.choice(SUBDOMAIN_PREFIXES))
    parts.append(random.choice(SECOND_LEVEL_DOMAINS))
    return ".".join(parts) + random.choice(TLDS_WEIGHTED)

def rand_wildcard_domain() -> str:
    return f"*.{random.choice(SECOND_LEVEL_DOMAINS)}{random.choice(TLDS_WEIGHTED)}"

def rand_idn_domain() -> str:
    word = random.choice(IDN_WORDS)
    tld = random.choice([".com", ".net", ".org", ".io", ".co"])
    try:
        encoded = word.encode("idna").decode("ascii")
        return encoded + tld
    except (UnicodeError, UnicodeDecodeError):
        # Fallback to punycode-style placeholder
        hex_suffix = f"{random.randint(0x1000, 0xFFFF):x}"
        return f"xn--{hex_suffix}{tld}"

def rand_url(wildcards: bool = False, custom_port: bool = False) -> str:
    domain = rand_domain()
    if custom_port and random.random() < 0.20:
        port = random.choice([8080, 8443, 8888, 9000, 9090, 3000, 4443, 5000, 6443, 9443])
        domain = f"{domain}:{port}"
    if wildcards and random.random() < 0.15:
        return f"*.{rand_domain()}{random.choice(URL_PATHS)}"
    return f"{domain}{random.choice(URL_PATHS)}"

def _write(path: Path, entries: list, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# {header}\n")
        f.write(f"# Generated: {ts}\n")
        f.write(f"# Count: {len(entries)}\n")
        f.write("#\n")
        for e in entries:
            f.write(str(e) + "\n")
    print(f"  {len(entries):>7,} entries -> {path}")

def _unique(gen_fn, n: int) -> list:
    seen = set()
    result = []
    attempts = 0
    max_attempts = n * 10
    while len(result) < n and attempts < max_attempts:
        attempts += 1
        val = gen_fn()
        if val not in seen:
            seen.add(val)
            result.append(val)
    return result

# ---------------------------------------------------------------------------
# Per-file generators
# ---------------------------------------------------------------------------

def gen_ip_01(n):
    "Public IPv4 only — cloud, CDN, ISP (ARIN/RIPE/APNIC/LACNIC/AFRINIC)"
    def fn():
        s, e = random.choice(PUBLIC_IPV4_RANGES)
        return rand_ipv4(s, e)
    entries = _unique(fn, n)
    return sorted(entries, key=lambda x: ipaddress.IPv4Address(x))

def gen_ip_02(n):
    "Private/enterprise IPv4 + CGNAT; simulates corp network blocks"
    def fn():
        s, e = random.choice(PRIVATE_IPV4_RANGES if random.random() < 0.65
                             else PUBLIC_IPV4_RANGES[:12])
        return rand_ipv4(s, e)
    entries = _unique(fn, n)
    return sorted(entries, key=lambda x: ipaddress.IPv4Address(x))

def gen_ip_03(n):
    "IPv6 only — real RIR allocations, ~8% CIDRs"
    def fn():
        if random.random() < 0.08:
            return rand_ipv6_cidr()
        return rand_ipv6()
    return _unique(fn, n)

def gen_ip_04(n):
    "Mixed IPv4+IPv6 with ~5% CIDRs — EDL mixed-type stress test"
    def fn():
        r = random.random()
        if r < 0.02:
            return rand_ipv4_cidr()
        if r < 0.05:
            return rand_ipv6_cidr()
        if r < 0.45:
            return rand_ipv6()
        s, e = random.choice(PUBLIC_IPV4_RANGES + PRIVATE_IPV4_RANGES)
        return rand_ipv4(s, e)
    return _unique(fn, n)

def gen_ip_05(n):
    "Edge cases: intentional dups, IPv4-mapped IPv6, 6to4, Teredo, broadcast"
    entries = []
    # Base IPs for intentional duplication (tests EDL dedup behavior)
    base = [rand_ipv4(*random.choice(PUBLIC_IPV4_RANGES)) for _ in range(800)]
    entries.extend(base)
    entries.extend(random.choices(base, k=300))      # ~27% duplicates

    # IPv4-mapped IPv6 (::ffff:a.b.c.d)
    for _ in range(500):
        ip4 = rand_ipv4(*random.choice(PUBLIC_IPV4_RANGES))
        entries.append(f"::ffff:{ip4}")

    # 6to4 (2002::/16 prefix + IPv4 embedded)
    for _ in range(300):
        ip4 = rand_ipv4(*random.choice(PUBLIC_IPV4_RANGES))
        packed = ipaddress.IPv4Address(ip4).packed
        entries.append(f"2002:{packed[0]:02x}{packed[1]:02x}:{packed[2]:02x}{packed[3]:02x}::1")

    # Teredo (2001:0000::/32)
    for _ in range(100):
        entries.append(f"2001::{random.randint(1, 0xFFFF):x}:{random.randint(1, 0xFFFF):x}")

    # Special/edge-case addresses
    entries += ["0.0.0.0", "255.255.255.255", "127.0.0.1", "::1",
                "::", "::ffff:0.0.0.0", "100.64.0.1", "100.127.255.254"]

    # Fill remainder with public IPs
    while len(entries) < n:
        s, e = random.choice(PUBLIC_IPV4_RANGES)
        entries.append(rand_ipv4(s, e))

    return entries[:n]

def gen_url_01(n):
    "Clean HTTPS URLs — diverse real-looking domains and paths"
    return _unique(rand_url, n)

def gen_url_02(n):
    "URLs with query strings — tracking/analytics simulation"
    def fn():
        base = rand_url()
        params = [
            f"id={random.randint(1000, 9999999)}",
            f"session={random.randint(0x10000, 0xFFFFFFF):x}",
            f"token={random.randint(0x100000, 0xFFFFFFF):x}",
            f"v={random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,99)}",
            f"lang={random.choice(['en','es','fr','de','zh','ja','ko','ar','ru','pt'])}",
            f"region={random.choice(['us-east','us-west','eu-west','eu-central','ap-southeast','ap-northeast'])}",
            f"fmt={random.choice(['json','xml','csv','protobuf','msgpack'])}",
            f"ts={random.randint(1700000000, 1800000000)}",
        ]
        return base + "?" + "&".join(random.sample(params, k=random.randint(1, 3)))
    return _unique(fn, n)

def gen_url_03(n):
    "Wildcard URL patterns (*.domain.tld/path)"
    return _unique(lambda: rand_url(wildcards=True), n)

def gen_url_04(n):
    "Custom port URLs — 8080, 8443, 9090, etc."
    return _unique(lambda: rand_url(custom_port=True), n)

def gen_url_05(n):
    "Encoding edge cases: percent-encoding, IDN, long paths, special chars"
    entries = []

    # Percent-encoded paths
    for _ in range(4000):
        entries.append(rand_domain() + random.choice(ENCODING_PATHS))

    # Very long paths (buffer/truncation testing)
    for _ in range(1500):
        depth = random.randint(8, 20)
        long_path = "/" + "/".join(
            random.choice(SUBDOMAIN_PREFIXES) for _ in range(depth)
        ) + "/resource"
        entries.append(rand_domain() + long_path)

    # IDN domains in URLs
    for _ in range(3000):
        entries.append(rand_idn_domain() + random.choice(URL_PATHS))

    # URLs with fragment identifiers (should be stripped by firewall)
    for _ in range(500):
        entries.append(rand_url() + f"#section-{random.randint(1, 99)}")

    # Null/zero-byte adjacent chars (edge parse cases)
    for _ in range(200):
        entries.append(rand_domain() + "/api/v1/data\x00extra")

    # Fill remainder
    while len(entries) < n:
        entries.append(rand_url(wildcards=True))

    seen, deduped = set(), []
    for e in entries:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return deduped[:n]

def gen_domains(n, wildcards=False, idn=False, edge=False):
    "Generic domain list generator"
    def fn():
        r = random.random()
        if wildcards and r < 0.20:
            return rand_wildcard_domain()
        if idn and r < (0.30 if wildcards else 0.15):
            return rand_idn_domain()
        if edge and r < 0.05:
            # Multi-level subdomain (deep nesting)
            parts = [random.choice(SUBDOMAIN_PREFIXES) for _ in range(random.randint(3, 6))]
            return ".".join(parts) + f".{random.choice(SECOND_LEVEL_DOMAINS)}.com"
        return rand_domain()
    return sorted(_unique(fn, n))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="lists", help="Output base directory")
    ap.add_argument("--entries", type=int, default=20_000, help="Entries per file")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    args = ap.parse_args()

    random.seed(args.seed)
    n = args.entries
    out = Path(args.output_dir)

    print(f"EDL Test Suite - List Generator")
    print(f"Output: {out.resolve()}")
    print(f"Entries/file: {n:,}  |  Seed: {args.seed}")
    print()

    # ---------- IP lists ----------
    print("IP lists:")
    _write(out/"ip_lists/ip_list_01.txt", gen_ip_01(n), "Public IPv4 (ARIN/RIPE/APNIC/LACNIC/AFRINIC cloud+ISP ranges)")
    _write(out/"ip_lists/ip_list_02.txt", gen_ip_02(n), "Private/Enterprise IPv4 + CGNAT")
    _write(out/"ip_lists/ip_list_03.txt", gen_ip_03(n), "IPv6 — real RIR allocations, ~8% CIDRs")
    _write(out/"ip_lists/ip_list_04.txt", gen_ip_04(n), "Mixed IPv4+IPv6, ~5% CIDRs — mixed-type stress test")
    _write(out/"ip_lists/ip_list_05.txt", gen_ip_05(n), "Edge cases: dups, IPv4-mapped IPv6, 6to4, Teredo, broadcast")

    # ---------- URL lists ----------
    print("\nURL lists:")
    _write(out/"url_lists/url_list_01.txt", gen_url_01(n), "Clean HTTPS URLs — diverse domains and paths")
    _write(out/"url_lists/url_list_02.txt", gen_url_02(n), "URLs with query parameters — analytics/tracking simulation")
    _write(out/"url_lists/url_list_03.txt", gen_url_03(n), "Wildcard URL patterns (*.domain.tld/path)")
    _write(out/"url_lists/url_list_04.txt", gen_url_04(n), "Custom port URLs — 8080/8443/9090/etc.")
    _write(out/"url_lists/url_list_05.txt", gen_url_05(n), "Encoding edge cases: percent-enc, IDN, long paths, special chars")

    # ---------- Domain lists ----------
    print("\nDomain lists:")
    _write(out/"domain_lists/domain_list_01.txt", gen_domains(n), "Clean domains — .com/.net/.org weighted")
    _write(out/"domain_lists/domain_list_02.txt", gen_domains(n), "Clean domains — APNIC Asia-Pacific ccTLDs weighted")
    _write(out/"domain_lists/domain_list_03.txt", gen_domains(n), "Clean domains — RIPE European ccTLDs weighted")
    _write(out/"domain_lists/domain_list_04.txt", gen_domains(n), "Clean domains — mixed gTLDs (.app/.dev/.tech/.cloud)")
    _write(out/"domain_lists/domain_list_05.txt", gen_domains(n), "Clean domains — enterprise/cloud subdomains")
    _write(out/"domain_lists/domain_list_06.txt", gen_domains(n), "Clean domains — tech/startup themed")
    _write(out/"domain_lists/domain_list_07.txt", gen_domains(n), "Clean domains — LACNIC/AFRINIC ccTLDs weighted")
    _write(out/"domain_lists/domain_list_08.txt", gen_domains(n), "Clean domains — .gov/.edu/.mil/.int")
    _write(out/"domain_lists/domain_list_09.txt", gen_domains(n, wildcards=True), "Wildcard domains (*.domain.tld) — 20% wildcard ratio")
    _write(out/"domain_lists/domain_list_10.txt", gen_domains(n, idn=True, edge=True), "IDN (Punycode) + deep subdomain edge cases")

    ip_total    = 5 * n
    url_total   = 5 * n
    domain_total= 10 * n
    grand       = ip_total + url_total + domain_total
    print(f"\nSummary:")
    print(f"  IP:     {ip_total:>9,}  (5 files)")
    print(f"  URL:    {url_total:>9,}  (5 files)")
    print(f"  Domain: {domain_total:>9,}  (10 files)")
    print(f"  TOTAL:  {grand:>9,}  (20 files)")

if __name__ == "__main__":
    main()
