#!/usr/bin/env python3
"""
Auto-discover cameras from Home Assistant and generate Monocle configuration.
Supports multiple discovery methods:
1. go2rtc streams (HA built-in or standalone)
2. UniFi Protect integration (construct RTSP URLs from storage files)
3. Generic camera stream_source attributes
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional, Tuple

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_URL = "http://supervisor/core"

# HA storage paths (mapped as homeassistant_config:ro)
HA_STORAGE_PATH = "/homeassistant/.storage"

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


def read_storage_file(filename: str) -> Optional[Dict]:
    """Read HA storage file directly (more reliable than API for some data)."""
    filepath = os.path.join(HA_STORAGE_PATH, filename)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[DEBUG] Storage file error {filename}: {e}")
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
# Method 2: UniFi Protect integration (reads from HA storage files)
# =============================================================================

def get_unifi_protect_config() -> Optional[Tuple[str, int]]:
    """Get UniFi Protect NVR IP from config entries (storage file or API)."""

    # Try reading from storage file first (more reliable - contains full data)
    config_data = read_storage_file("core.config_entries")
    if config_data:
        entries = config_data.get("data", {}).get("entries", [])
        print(f"[DEBUG] Read {len(entries)} config entries from storage")
    else:
        # Fall back to API
        entries = api_get("/api/config/config_entries/entry") or []
        print(f"[DEBUG] Got {len(entries)} config entries from API")

    if not entries:
        print("[DEBUG] No config entries found")
        return None

    # Look for UniFi Protect
    unifi_domains = ["unifiprotect", "unifi_protect", "ubiquiti_unifi_protect"]
    for entry in entries:
        domain = entry.get("domain", "")
        if domain in unifi_domains or "protect" in domain.lower():
            print(f"[DEBUG] Found UniFi Protect entry: domain={domain}")
            data = entry.get("data", {})
            host = data.get("host") or data.get("ip") or data.get("address")
            # RTSP port is 7441 for secure, 7447 for insecure
            port = 7441
            if host:
                print(f"[INFO] Found UniFi Protect NVR: {host}:{port}")
                return (host, port)

    print("[DEBUG] No UniFi Protect config entry found")
    return None


def get_unifi_camera_info_from_entities(stream_quality: str = "high") -> Dict[str, Dict]:
    """Get UniFi camera MAC addresses from entity registry, with device names from device registry.

    Args:
        stream_quality: "high" (channel 0), "medium" (channel 1), or "low" (channel 2)
    """
    cameras = {}

    # Map quality to channel number
    quality_to_channel = {"high": "0", "medium": "1", "low": "2"}
    target_channel = quality_to_channel.get(stream_quality, "0")
    print(f"[INFO] Using stream quality: {stream_quality} (channel {target_channel})")

    # Read device registry to get pretty names (name_by_user or name)
    device_names = {}
    device_data = read_storage_file("core.device_registry")
    if device_data:
        devices = device_data.get("data", {}).get("devices", [])
        for dev in devices:
            dev_id = dev.get("id")
            # name_by_user is the user's custom alias, name is the original device name
            name = dev.get("name_by_user") or dev.get("name")
            if dev_id and name:
                device_names[dev_id] = name
        print(f"[DEBUG] Loaded {len(device_names)} device names")

    # Read entity registry from storage
    entity_data = read_storage_file("core.entity_registry")
    if not entity_data:
        print("[DEBUG] Could not read entity registry")
        return cameras

    entities = entity_data.get("data", {}).get("entities", [])
    print(f"[DEBUG] Read {len(entities)} entities from registry")

    # Track which MACs we've already added (to avoid duplicates across quality levels)
    seen_macs = set()

    for ent in entities:
        entity_id = ent.get("entity_id", "")
        platform = ent.get("platform", "")
        unique_id = ent.get("unique_id", "")

        # Look for UniFi Protect camera entities
        if (entity_id.startswith("camera.") and
            "unifi" in platform.lower() and
            f"_{target_channel}" in unique_id and  # Match target quality channel
            "_insecure" not in unique_id):  # Skip insecure duplicates

            # unique_id format: "MAC_channel" e.g. "68D79AE248C8_0"
            parts = unique_id.rsplit("_", 1)
            if len(parts) == 2:
                mac = parts[0]
                channel = parts[1]

                # Skip if we already have this MAC (handles duplicate entity registrations)
                if mac in seen_macs:
                    continue
                seen_macs.add(mac)

                # Get device name from device registry (the pretty name like "Garagem E9")
                device_id = ent.get("device_id")
                name = device_names.get(device_id)

                # Fallback to entity_id if no device name found
                if not name:
                    name = entity_id.replace("camera.", "").replace("_high", "").replace("_medium", "").replace("_low", "").replace("_", " ").title()

                cameras[entity_id] = {
                    "entity_id": entity_id,
                    "name": name,
                    "mac": mac,
                    "channel": channel
                }
                print(f"[DEBUG] Found UniFi camera: {name} (MAC: {mac})")

    return cameras


def get_unifi_rtsp_urls(stream_quality: str = "high") -> Dict[str, str]:
    """Construct RTSP URLs for UniFi Protect cameras using entity registry."""
    urls = {}

    nvr_config = get_unifi_protect_config()
    if not nvr_config:
        print("[INFO] UniFi Protect integration not found")
        return urls

    host, port = nvr_config
    cameras = get_unifi_camera_info_from_entities(stream_quality)

    for entity_id, cam_info in cameras.items():
        mac = cam_info["mac"]
        channel = cam_info["channel"]
        name = cam_info["name"]

        # UniFi Protect RTSP URL format:
        # rtsps://NVR_IP:7441/MAC_ADDRESS?channel=N
        # channel 0 = high, 1 = medium, 2 = low
        rtsp_url = f"rtsps://{host}:{port}/{mac}?channel={channel}"
        urls[entity_id] = rtsp_url
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

def discover_cameras(filters: List[str] = None, stream_quality: str = "high") -> List[Dict]:
    """
    Discover cameras using multiple methods:
    1. go2rtc streams
    2. UniFi Protect integration
    3. Camera entity attributes

    Args:
        filters: List of filter strings to match camera names/entity_ids
        stream_quality: "high", "medium", or "low" for UniFi cameras
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

    # Method 2: Try UniFi Protect (uses entity_id as key)
    print("[INFO] Checking UniFi Protect integration...")
    unifi_urls = get_unifi_rtsp_urls(stream_quality)
    for unifi_entity_id, rtsp_url in unifi_urls.items():
        # Direct match by entity_id
        if unifi_entity_id in discovered:
            if not discovered[unifi_entity_id]["stream_url"]:
                discovered[unifi_entity_id]["stream_url"] = rtsp_url
                print(f"[INFO] Matched UniFi camera {unifi_entity_id}")
        else:
            # Try fuzzy matching if entity wasn't in discovered list
            for entity_id, camera in discovered.items():
                if camera["stream_url"]:
                    continue
                # Match by base entity name (without _high suffix)
                base_unifi = unifi_entity_id.replace("camera.", "").replace("_high", "")
                base_entity = entity_id.replace("camera.", "").replace("_high", "")
                if base_unifi == base_entity:
                    camera["stream_url"] = rtsp_url
                    print(f"[INFO] Fuzzy matched UniFi {unifi_entity_id} to {entity_id}")
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
    stream_quality = options.get("stream_quality", "high")
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
        cameras = discover_cameras(camera_filters if camera_filters else None, stream_quality)
        config = generate_monocle_config(cameras)
        write_monocle_config(config)
    else:
        print("[INFO] Auto-discovery disabled")
        write_monocle_config({"cameras": []})

    print("[INFO] Camera discovery complete")


if __name__ == "__main__":
    main()
