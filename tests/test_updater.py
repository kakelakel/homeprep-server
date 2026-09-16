from homeprep_server.updater import parse_release, version_key


def test_parse_release_finds_windows_installer_and_digest() -> None:
    release = parse_release(
        {
            "tag_name": "v0.1.200",
            "html_url": "https://github.com/kakelakel/homeprep-server/releases/tag/v0.1.200",
            "assets": [
                {"name": "notes.txt", "browser_download_url": "https://example.invalid/notes"},
                {
                    "name": "HomePrep-Setup.exe",
                    "browser_download_url": "https://example.invalid/HomePrep-Setup.exe",
                    "digest": "sha256:abcd",
                },
            ],
        }
    )
    assert release.tag_name == "v0.1.200"
    assert release.installer_url == "https://example.invalid/HomePrep-Setup.exe"
    assert release.digest == "sha256:abcd"


def test_version_key_orders_development_and_release_builds() -> None:
    assert version_key("v0.1.193") > version_key("0.1.192")
    assert version_key("0.2.0") > version_key("0.1.999")
    assert version_key("0.1.0") > version_key("0.1.0-rc1")
