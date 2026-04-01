from __future__ import annotations

from utils.tunnels import extract_playit_claim_url, extract_playit_public_endpoint


def test_extract_playit_public_endpoint_from_tunnel_address_log():
    log_text = """
    INFO connected
    INFO tunnel_address=147.185.221.24:25565 local_address=127.0.0.1:25565
    """

    assert extract_playit_public_endpoint(log_text) == "147.185.221.24:25565"


def test_extract_playit_public_endpoint_from_hostname_log():
    log_text = """
    INFO tunnel ready
    INFO public endpoint is fancy-world.ply.gg:30123
    """

    assert extract_playit_public_endpoint(log_text) == "fancy-world.ply.gg:30123"


def test_extract_playit_claim_url_from_log():
    log_text = """
    INFO visit https://playit.gg/claim/some-agent-token to link this device
    """

    assert extract_playit_claim_url(log_text) == "https://playit.gg/claim/some-agent-token"
