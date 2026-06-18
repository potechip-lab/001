"""
fetch_news.py
キーワードごとにGoogle News RSSから記事を取得し、data.jsonに保存するスクリプト。
GitHub Actionsから毎日1回呼び出される。
"""

import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def fetch_google_news_rss(keyword: str, max_items: int = 8) -> list[dict]:
    """指定キーワードでGoogle News RSSを取得して記事リストを返す。"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; UniversityNewsBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()

        root = ET.fromstring(content)
        articles = []

        for item in root.findall(".//item")[:max_items]:
            title    = (item.findtext("title")   or "").strip()
            link     = (item.findtext("link")    or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source   = (item.findtext("source")  or "").strip()

            if title and link:
                articles.append({
                    "title":   title,
                    "link":    link,
                    "pubDate": pub_date,
                    "source":  source,
                })

        return articles

    except Exception as e:
        print(f"    ⚠️  取得失敗: {e}")
        return []


def fetch_trending_keywords() -> list[str]:
    """Google Trends Japan急上昇ワードを返す。"""
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=JP"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; UniversityTrendsBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()

        root = ET.fromstring(content)
        return [
            item.findtext("title").strip()
            for item in root.findall(".//item")
            if item.findtext("title")
        ]

    except Exception as e:
        print(f"    ⚠️  Trends取得失敗: {e}")
        return []


def main() -> None:
    print("=" * 40)
    print("  ニュース取得スクリプト開始")
    print("=" * 40)

    # ── 設定読み込み ──────────────────────────────
    with open("keywords.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    university_name  = config.get("university_name", "")
    match_keywords   = config.get("match_keywords", [])
    categories       = dict(config["categories"])  # シャローコピー

    # ── トレンド取得 & キーワード自動拡張 ─────────
    print("\n📈 急上昇ワードを取得中...")
    trending = fetch_trending_keywords()
    print(f"   取得件数: {len(trending)} 件")

    auto_added = []
    for trend in trending:
        for match in match_keywords:
            if match in trend and trend not in auto_added:
                auto_added.append(trend)
                break

    if auto_added:
        categories["🔥 急上昇"] = auto_added
        print(f"   自動追加キーワード: {auto_added}")
    else:
        print("   関連トレンドなし（自動追加なし）")

    # ── ニュース取得 ───────────────────────────────
    print("\n📰 ニュース記事を取得中...")
    result: dict = {
        "updated_at":      datetime.now(timezone.utc).isoformat(),
        "university_name": university_name,
        "categories":      {},
    }

    for cat_name, keywords in categories.items():
        result["categories"][cat_name] = {}
        for keyword in keywords:
            print(f"   → {keyword}")
            articles = fetch_google_news_rss(keyword)
            result["categories"][cat_name][keyword] = articles
            time.sleep(1.5)  # レートリミット対策

    # ── data.json 保存 ─────────────────────────────
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = sum(
        len(arts)
        for cat in result["categories"].values()
        for arts in cat.values()
    )
    print(f"\n✅ 完了: {total} 件の記事を data.json に保存しました")
    print("=" * 40)


if __name__ == "__main__":
    main()
