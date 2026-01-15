#!/usr/bin/env python3
"""
Auto-discover cameras from Home Assistant and generate Monocle configuration.
Supports multiple discovery methods:
1. go2rtc streams (HA built-in or standalone)
2. UniFi Protect integration (construct RTSP URLs)
3. Generic camera stream_source attributes
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional, Tuple

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_URL = "http://supervisor/core"

def api_get(endpoint: str, timeout: int = 10) -> Optional[Dict]:
    """Make authenticated GET request to HA API."""
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{HA_URL}{endpoint}", headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"[DEBUG] API error {endpoint}: {e}")
    return None


# =============================================================================
# Method 1: go2rtc streams
# =============================================================================

def get_go2rtc_streams() -> Dict[str, str]:
    """Try to get streams from go2rtc (HA built-in or standalone)."""
    streams = {}

    # Try various go2rtc endpoints
    endpoints = [
        "http://supervisor/core/api/go2rtc/streams",  # HA built-in go2rtc
        "http://localhost:1984/api/streams",           # Standalone go2rtc
        "http://localhost:11984/api/streams",          # HA go2rtc alternate port
        "http://homeassistant:1984/api/streams",       # Docker network
    ]

    for url in endpoints:
        try:
            headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"} if "supervisor" in url else {}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"[INFO] Found go2rtc at {url}")
                # go2rtc returns {stream_name: {producers: [{url: "rtsp://..."}]}}
                for name, info in data.items():
                    if isinstance(info, dict):
                        producers = info.get("producers", [])
                        for producer in producers:
                            if isinstance(producer, dict) and "url" in producer:
                                url = producer["url"]
                                if "rtsp" in url.lower():
                                    streams[name] = url
                                    print(f"[INFO] go2rtc stream: {name} -> {url[:50]}...")
                return streams
        except:
            pass

    print("[INFO] go2rtc not found or no streams configured")
    return streams


# =============================================================================
# Method 2: UniFi Protect integration
# =============================================================================

def get_unifi_protect_config() -> Optional[Tuple[str, int]]:
    """Get UniFi Protect NVR IP from config entries."""
    entries = api_get("/api/config/config_entries/entry")
    if not entries:
        print("[DEBUG] Config entries API returned nothing")
        return None

    # Debug: show all integration domains
    domains = set(entry.get("domain", "") for entry in entries)
    print(f"[DEBUG] Found integrations: {sorted(domains)}")

    # Look for UniFi Protect (try various domain names)
    unifi_domains = ["unifiprotect", "unifi_protect", "ubiquiti_unifi_protect", "unifi"]
    for entry in entries:
        domain = entry.get("domain", "")
        if domain in unifi_domains or "unifi" in domain.lower() or "protect" in domain.lower():
            print(f"[DEBUG] Found potential UniFi entry: domain={domain}")
            print(f"[DEBUG]   data keys: {list(entry.get('data', {}).keys())}")
            data = entry.get("data", {})
            host = data.get("host") or data.get("ip") or data.get("address")
            port = data.get("port", 7441)
            if host:
                print(f"[INFO] Found UniFi Protect NVR: {host}:{port}")
                return (host, port)

    print("[DEBUG] No UniFi Protect config entry found")
    return None

def get_unifi_camera_ids() -> Dict[str, str]:
    """Get UniFi Protect camera IDs from device registry."""
    camera_ids = {}

    # Get device registry
    devices = api_get("/api/config/device_registry")
    if not devices:
        print("[DEBUG] Device registry API returned nothing")
        return camera_ids

    print(f"[DEBUG] Device registry has {len(devices)} devices")

    # Debug: show first few device identifier prefixes
    id_prefixes = set()
    for device in devices[:50]:
        identifiers = device.get("identifiers", [])
        for identifier in identifiers:
            if isinstance(identifier, list) and len(identifier) >= 1:
                id_prefixes.add(identifier[0])
    print(f"[DEBUG] Device identifier prefixes: {sorted(id_prefixes)}")

    # Look for UniFi devices (try various identifier prefixes)
    unifi_prefixes = ["unifiprotect", "unifi_protect", "ubiquiti", "unifi"]
    for device in devices:
        identifiers = device.get("identifiers", [])
        for identifier in identifiers:
            if isinstance(identifier, list) and len(identifier) >= 2:
                prefix = identifier[0].lower() if isinstance(identifier[0], str) else ""
                if any(p in prefix for p in unifi_prefixes) or "unifi" in prefix or "protect" in prefix:
                    camera_id = identifier[1]
                    name = device.get("name_by_user") or device.get("name", "")
                    model = device.get("model", "")
                    # Only add cameras (not NVR or other devices)
                    if name and camera_id and ("camera" in model.lower() or "g4" in model.lower() or "g5" in model.lower() or "doorbell" in model.lower()):
                        camera_ids[name] = camera_id
                        print(f"[DEBUG] UniFi camera: {name} ({model}) -> {camera_id}")
                    elif name:
                        print(f"[DEBUG] UniFi device (not camera): {name} ({model})")

    return camera_ids

def get_unifi_rtsp_urls() -> Dict[str, str]:
    """Construct RTSP URLs for UniFi Protect cameras."""
    urls = {}

    nvr_config = get_unifi_protect_config()
    if not nvr_config:
        print("[INFO] UniFi Protect integration not found")
        return urls

    host, port = nvr_config
    camera_ids = get_unifi_camera_ids()

    for name, camera_id in camera_ids.items():
        # UniFi Protect RTSP URL format
        # rtsps for secure (port 7441), rtsp for insecure (port 7447)
        rtsp_url = f"rtsps://{host}:{port}/{camera_id}"
        urls[name] = rtsp_url
        print(f"[INFO] UniFi RTSP: {name} -> {rtsp_url}")

    return urls


# =============================================================================
# Method 3: Camera entity attributes
# =============================================================================

def get_camera_entities() -> List[Dict]:
    """Get all camera entities from HA."""
    states = api_get("/api/states", timeout=30)
    if not states:
        return []

    cameras = []
    for state in states:
        entity_id = state.get("entity_id", "")
        if entity_id.startswith("camera."):
            cameras.append(state)
    return cameras

def get_stream_url_from_attributes(state: Dict) -> Optional[str]:
    """Try to get RTSP URL from camera entity attributes."""
    attrs = state.get("attributes", {})

    # Check common attribute names
    for attr in ["stream_source", "rtsp_url", "video_url", "stream_url", "rtsp_stream"]:
        if attr in attrs and attrs[attr]:
            url = attrs[attr]
            if isinstance(url, str) and "://" in url:
                return url

    return None


# =============================================================================
# Main discovery logic
# =============================================================================

def discover_cameras(filters: List[str] = None) -> List[Dict]:
    """
    Discover cameras using multiple methods:
    1. go2rtc streams
    2. UniFi Protect integration
    3. Camera entity attributes
    """
    discovered = {}  # name -> {entity_id, name, stream_url}

    # Get all camera entities first
    camera_entities = get_camera_entities()
    print(f"[INFO] Found {len(camera_entities)} camera entities in HA")

    # Build entity lookup by name
    entity_lookup = {}  # name variations -> entity_id
    for state in camera_entities:
        entity_id = state.get("entity_id", "")
        attrs = state.get("attributes", {})
        friendly_name = attrs.get("friendly_name", "")

        # Apply filters
        if filters:
            match = False
            for f in filters:
                if f.lower() in entity_id.lower() or f.lower() in friendly_name.lower():
                    match = True
                    break
            if not match:
                continue

        # Store with various name keys for matching
        entity_lookup[entity_id] = state
        entity_lookup[friendly_name.lower()] = state
        entity_lookup[entity_id.replace("camera.", "")] = state

        # Initialize camera info
        discovered[entity_id] = {
            "entity_id": entity_id,
            "name": friendly_name or entity_id.replace("camera.", "").replace("_", " ").title(),
            "stream_url": None
        }

    # Method 1: Try go2rtc
    print("[INFO] Checking go2rtc streams...")
    go2rtc_streams = get_go2rtc_streams()
    for stream_name, rtsp_url in go2rtc_streams.items():
        # Try to match stream name to camera entity
        for entity_id, camera in discovered.items():
            if (stream_name.lower() in entity_id.lower() or
                stream_name.lower() in camera["name"].lower() or
                entity_id.replace("camera.", "") == stream_name):
                camera["stream_url"] = rtsp_url
                print(f"[INFO] Matched go2rtc stream '{stream_name}' to {entity_id}")
                break

    # Method 2: Try UniFi Protect
    print("[INFO] Checking UniFi Protect integration...")
    unifi_urls = get_unifi_rtsp_urls()
    for name, rtsp_url in unifi_urls.items():
        # Try to match UniFi camera to HA entity
        for entity_id, camera in discovered.items():
            if camera["stream_url"]:
                continue  # Already has URL from go2rtc
            if (name.lower() in camera["name"].lower() or
                name.lower() in entity_id.lower()):
                camera["stream_url"] = rtsp_url
                print(f"[INFO] Matched UniFi camera '{name}' to {entity_id}")
                break

    # Method 3: Check entity attributes
    print("[INFO] Checking camera entity attributes...")
    for entity_id, camera in discovered.items():
        if camera["stream_url"]:
            continue  # Already has URL

        state = entity_lookup.get(entity_id)
        if state:
            url = get_stream_url_from_attributes(state)
            if url:
                camera["stream_url"] = url
                print(f"[INFO] Found stream_source for {entity_id}")

    # Summary
    with_urls = sum(1 for c in discovered.values() if c["stream_url"])
    print(f"[INFO] Discovery complete: {len(discovered)} cameras, {with_urls} with RTSP URLs")

    return list(discovered.values())


def generate_monocle_config(cameras: List[Dict]) -> Dict:
    """Generate Monocle Gateway configuration."""
    config = {"cameras": []}

    for camera in cameras:
        if camera.get("stream_url"):
            cam_config = {
                "name": camera["name"],
                "url": camera["stream_url"],
                "tags": ["@proxy"]
            }
            config["cameras"].append(cam_config)
            print(f"[INFO] Added to Monocle: {camera['name']}")
        else:
            print(f"[WARN] Skipping {camera['name']} - no RTSP URL")

    return config


def write_monocle_token(token: str, path: str = "/etc/monocle/monocle.token"):
    """Write Monocle API token to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(token)
    print("[INFO] Wrote Monocle token file")


def write_monocle_config(config: Dict, path: str = "/etc/monocle/monocle.json"):
    """Write Monocle configuration to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[INFO] Wrote Monocle config with {len(config.get('cameras', []))} cameras")


def main():
    """Main entry point."""
    options_path = "/data/options.json"
    options = {}
    if os.path.exists(options_path):
        with open(options_path) as f:
            options = json.load(f)

    monocle_token = options.get("monocle_token", "")
    auto_discover = options.get("auto_discover", True)
    camera_filters = options.get("camera_filters", [])

    if not monocle_token:
        print("[ERROR] Monocle token not configured", file=sys.stderr)
        sys.exit(1)

    if not SUPERVISOR_TOKEN:
        print("[ERROR] SUPERVISOR_TOKEN not available", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Starting camera discovery...")
    write_monocle_token(monocle_token)

    if auto_discover:
        cameras = discover_cameras(camera_filters if camera_filters else None)
        config = generate_monocle_config(cameras)
        write_monocle_config(config)
    else:
        print("[INFO] Auto-discovery disabled")
        write_monocle_config({"cameras": []})

    print("[INFO] Camera discovery complete")


if __name__ == "__main__":
    main()
