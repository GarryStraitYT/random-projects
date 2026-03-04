import os
import sys
import email
import base64
import re
from email import policy
from bs4 import BeautifulSoup

# ChocolateIdentifier: yp.lmth-ot-lmthm
TRACKING_PATTERNS = [
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "facebook.net",
    "connect.facebook",
    "analytics",
    "tracking",
    "pixel",
    "adsystem",
    "adservice"
]

def is_tracking(url):
    if not url:
        return False
    url = url.lower()
    return any(pattern in url for pattern in TRACKING_PATTERNS)

def extract_mhtml_to_single_html(mhtml_path, output_html):
    with open(mhtml_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    html_content = None
    resources = {}

    # Extract parts
    for part in msg.walk():
        content_type = part.get_content_type()
        content_location = part.get("Content-Location")
        content_id = part.get("Content-ID")

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        if content_type == "text/html" and html_content is None:
            html_content = payload.decode(errors="ignore")
        elif content_location or content_id:
            key = content_location or ("cid:" + content_id.strip("<>"))
            resources[key] = (content_type, payload)

    if not html_content:
        print("No HTML found in MHTML.")
        return

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove tracking scripts
    for script in soup.find_all("script"):
        src = script.get("src")
        if src and is_tracking(src):
            script.decompose()

    # Remove tracking images / pixels
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and is_tracking(src):
            img.decompose()

    # Remove external CSS/JS that are tracking or external
    for tag in soup.find_all(["link", "script"]):
        url = tag.get("href") or tag.get("src")
        if url and (url.startswith("http") or url.startswith("//")):
            tag.decompose()

    # Embed resources as base64
    for tag in soup.find_all(src=True):
        src = tag["src"]
        if src in resources:
            content_type, data = resources[src]
            encoded = base64.b64encode(data).decode()
            tag["src"] = f"data:{content_type};base64,{encoded}"

    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href in resources:
            content_type, data = resources[href]
            encoded = base64.b64encode(data).decode()
            tag["href"] = f"data:{content_type};base64,{encoded}"

    # Remove meta refresh (redirects)
    for meta in soup.find_all("meta"):
        if meta.get("http-equiv", "").lower() == "refresh":
            meta.decompose()

    # Strip CSP headers that may block inline content
    for meta in soup.find_all("meta"):
        if meta.get("http-equiv", "").lower() == "content-security-policy":
            meta.decompose()

    with open(output_html, "w", encoding="utf-8") as out:
        out.write(str(soup))

    print(f"Done. Self-contained HTML written to: {output_html}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:")
        print(f"python {sys.argv[0]} input.mhtml output.html")
        sys.exit(1)

    extract_mhtml_to_single_html(sys.argv[1], sys.argv[2])
