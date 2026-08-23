from pathlib import Path


def test_nginx_serves_http_without_https_redirect():
    template = Path("infra/nginx/nginx.conf.template").read_text(encoding="utf-8")
    locations = Path("infra/nginx/app_locations.conf").read_text(encoding="utf-8")
    http_block = template.split("listen 443", 1)[0]
    assert "listen 80" in http_block
    assert "return 301" not in http_block
    assert "include /etc/nginx/app_locations.conf" in http_block
    assert "location /api/" in locations
    assert "$forwarded_proto" in locations
    assert "trycloudflare" not in template
