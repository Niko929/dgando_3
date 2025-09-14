from rest_framework import serializers
from urllib.parse import urlparse
import re


class ExternalLinkValidator:
    def __init__(self, field):
        self.field = field

    def __call__(self, value):
        if value:
            # Проверяем, является ли ссылка YouTube
            if not self.is_youtube_link(value):
                raise serializers.ValidationError(
                    "Разрешены только ссылки на YouTube. Другие внешние ресурсы запрещены."
                )

    def is_youtube_link(self, url):
        """Проверяет, является ли ссылка YouTube ссылкой"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Разрешенные YouTube домены
            youtube_domains = [
                'youtube.com',
                'www.youtube.com',
                'youtu.be',
                'www.youtu.be',
                'm.youtube.com'
            ]

            # Проверяем домен
            if any(domain.endswith(yt_domain) for yt_domain in youtube_domains):
                return True

            # Проверяем шаблоны YouTube ссылок
            youtube_patterns = [
                r'^https?://(www\.)?youtube\.com/',
                r'^https?://youtu\.be/',
                r'^https?://(www\.)?youtube\.com/embed/',
                r'^https?://(www\.)?youtube\.com/v/',
                r'^https?://(www\.)?youtube\.com/watch\?v=',
            ]

            return any(re.match(pattern, url.lower()) for pattern in youtube_patterns)

        except Exception:
            return False