"""Locate the torch wheel URL for this interpreter on Chinese PyPI mirrors.

The direct ``download.pytorch.org`` transfer stalls on this network at ~0 bytes
after a TCP connect (2.8 GB wheel), while ordinary-sized wheels download fine,
so the wheel is fetched separately with a resumable client.

Usage:
    python _w1_torch_url.py [--want cu|cpu]
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request

MIRRORS = (
    ("tuna", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("aliyun", "https://mirrors.aliyun.com/pypi/simple"),
    ("tencent", "https://mirrors.cloud.tencent.com/pypi/simple"),
    ("pypi", "https://pypi.org/simple"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--want", default="any", choices=("any", "cu", "cpu"))
    args = parser.parse_args()

    for name, base in MIRRORS:
        try:
            with urllib.request.urlopen(f"{base}/torch/", timeout=30) as response:
                html = response.read().decode("utf-8", "replace")
        except Exception as error:  # noqa: BLE001
            print(f"  {name:<8} index FAIL {type(error).__name__}")
            continue
        # hrefs look like ../../packages/xx/yy/<wheel>#sha256=...
        hrefs = re.findall(r'href="([^"]+)"', html)
        wheels = [h for h in hrefs
                  if h.endswith(".whl") and "cp311" in h and "win_amd64" in h]
        if not wheels:
            print(f"  {name:<8} no cp311/win_amd64 wheel")
            continue
        # newest = last listed (index order is chronological)
        pick = wheels[-1].split("#")[0]
        if pick.startswith("../"):
            url = base.rsplit("/simple", 1)[0] + pick[2:]
        elif pick.startswith("http"):
            url = pick
        else:
            url = f"{base}/torch/{pick}"
        wheel_name = url.rsplit("/", 1)[-1]
        print(f"  {name:<8} {wheel_name}")
        print(f"           {url}")

        # probe size with a ranged request
        try:
            request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                content_range = response.headers.get("Content-Range", "")
                size = content_range.split("/")[-1] if "/" in content_range else "?"
            print(f"           size={size} bytes "
                  f"({int(size)/1e9:.2f} GB)" if size.isdigit() else
                  f"           size={size}")
        except Exception as error:  # noqa: BLE001
            print(f"           size probe FAIL {type(error).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
