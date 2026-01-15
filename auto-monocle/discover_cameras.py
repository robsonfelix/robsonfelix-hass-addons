#!/usr/bin/env python3
"""
Auto-discover cameras from Home Assistant and generate Monocle configuration.
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_URL = "http://supervisor/core"

def get_ha_states() -> List[Dict]:
    """Get all entity states from Home Assistant."""
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{HA_URL}/api/states", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get HA states: {e}", file=sys.stderr)
        return []

def get_camera_stream_url(entity_id: str) -> Optional[str]:
    """Get the RTSP stream URL for a camera entity."""
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }

    # Try to get stream source from camera attributes or via API
    try:
        # First check if entity has stream_source attribute
        response = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            state = response.json()
            attrs = state.get("attributes", {})

            # Check common attribute names for stream URL
            for attr in ["stream_source", "rtsp_url", "video_url", "stream_url"]:
                if attr in attrs and attrs[attr]:
                    return attrs[attr]

            # For UniFi Protect, construct RTSP URL from attributes
            if "camera_id" in attrs or "unifi" in entity_id.lower():
                # UniFi cameras typically have RTSP at: rtsp://ip:7447/camera_id
                pass

    except Exception as e:
        print(f"[WARN] Could not get stream URL for {entity_id}: {e}", file=sys.stderr)

    return None

def discover_cameras(filters: List[str] = None) -> List[Dict]:
    """Discover all camera entities from Home Assistant."""
    states = get_ha_states()
    cameras = []

    for state in states:
        entity_id = state.get("entity_id", "")

        # Only process camera entities
        if not entity_id.startswith("camera."):
            continue

        # Apply filters if specified
        if filters:
            skip = True
            for f in filters:
                if f.lower() in entity_id.lower() or f.lower() in state.get("attributes", {}).get("friendly_name", "").lower():
                    skip = False
                    break
            if skip:
                continue

        attrs = state.get("attributes", {})
        friendly_name = attrs.get("friendly_name", entity_id.replace("camera.", "").replace("_", " ").title())

        # Get stream URL
        stream_url = get_camera_stream_url(entity_id)

        camera_info = {
            "entity_id": entity_id,
            "name": friendly_name,
            "stream_url": stream_url,
            "brand": attrs.get("brand", "Unknown"),
            "model": attrs.get("model", "Unknown"),
            "supported_features": attrs.get("supported_features", 0)
        }

        cameras.append(camera_info)
        print(f"[INFO] Discovered camera: {friendly_name} ({entity_id})")

    return cameras

def generate_monocle_config(cameras: List[Dict]) -> Dict:
    """Generate Monocle Gateway configuration (cameras only, token is separate file)."""
    config = {
        "cameras": []
    }

    for camera in cameras:
        if camera.get("stream_url"):
            cam_config = {
                "name": camera["name"],
                "url": camera["stream_url"],
                "tags": ["@proxy"]  # Use Monocle Gateway proxy
            }
            config["cameras"].append(cam_config)
            print(f"[INFO] Added camera to Monocle: {camera['name']}")
        else:
            print(f"[WARN] Skipping {camera['name']} - no stream URL available")

    return config

def write_monocle_token(token: str, path: str = "/etc/monocle/monocle.token"):
    """Write Monocle API token to file (required by gateway)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(token)
    print(f"[INFO] Wrote Monocle token file")

def write_monocle_config(config: Dict, path: str = "/etc/monocle/monocle.json"):
    """Write Monocle configuration to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[INFO] Wrote Monocle config with {len(config.get('cameras', []))} cameras")

def main():
    """Main entry point."""
    # Read add-on options
    options_path = "/data/options.json"
    if os.path.exists(options_path):
        with open(options_path) as f:
            options = json.load(f)
    else:
        options = {}

    monocle_token = options.get("monocle_token", "")
    auto_discover = options.get("auto_discover", True)
    camera_filters = options.get("camera_filters", [])

    if not monocle_token:
        print("[ERROR] Monocle token not configured. Get one from https://monoclecam.com", file=sys.stderr)
        sys.exit(1)

    if not SUPERVISOR_TOKEN:
        print("[ERROR] SUPERVISOR_TOKEN not available", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Starting camera discovery...")

    # Always write the token file (required by gateway)
    write_monocle_token(monocle_token)

    if auto_discover:
        cameras = discover_cameras(camera_filters if camera_filters else None)
        print(f"[INFO] Discovered {len(cameras)} cameras")

        config = generate_monocle_config(cameras)
        write_monocle_config(config)
    else:
        print("[INFO] Auto-discovery disabled")

    print("[INFO] Camera discovery complete")

if __name__ == "__main__":
    main()
