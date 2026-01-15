"""Global news sources configuration."""

from schemas import NewsSource

# fmt: off
GLOBAL_SOURCES: list[NewsSource] = [
    NewsSource(country="联合国", media_name="联合国新闻网", url="https://news.un.org/en/"),
    NewsSource(country="美国", media_name="CNN", url="https://edition.cnn.com/"),
    NewsSource(country="美国", media_name="AP", url="https://www.ap.org/"),
    NewsSource(country="俄罗斯", media_name="RT", url="https://www.rt.com/"),
    NewsSource(country="俄罗斯", media_name="TASS", url="https://tass.com/"),
    NewsSource(country="德国", media_name="Die Zeit", url="https://www.zeit.de/index"),
    NewsSource(country="英国", media_name="Telegraph", url="https://www.telegraph.co.uk/"),
    NewsSource(country="法国", media_name="France 24", url="https://www.france24.com/en/"),
    NewsSource(country="日本", media_name="NHK", url="https://www3.nhk.or.jp/news/"),
    NewsSource(country="韩国", media_name="Yonhap", url="https://en.yna.co.kr/"),
    NewsSource(country="意大利", media_name="ANSA", url="https://www.ansa.it/english"),
    NewsSource(country="加拿大", media_name="CTV News", url="https://www.ctvnews.ca/"),
    NewsSource(country="巴西", media_name="Folha de S.Paulo", url="https://www.folha.uol.com.br/"),
    NewsSource(country="以色列", media_name="Times of Israel", url="https://www.timesofisrael.com/"),
    NewsSource(country="伊朗", media_name="Press TV", url="https://www.presstv.ir/"),
    NewsSource(country="新加坡", media_name="Mothership.SG", url="https://mothership.sg"),
    NewsSource(country="乌克兰", media_name="Kyiv Independent", url="https://kyivindependent.com/"),
]
# fmt: on


def format_sources_for_planning(sources: list[NewsSource]) -> str:
    """Format sources as a readable list grouped by country."""
    by_country: dict[str, list[NewsSource]] = {}
    for source in sources:
        by_country.setdefault(source.country, []).append(source)

    lines = ["Available news sources (grouped by country/organization):"]
    for country, country_sources in sorted(by_country.items()):
        lines.append(f"\n{country}:")
        for source in country_sources:
            lines.append(f"  - {source.media_name}: {source.url}")

    return "\n".join(lines)
