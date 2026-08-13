from . import schemas
from . import models
from typing import Optional

def select_rendition(content: schemas.ContentResponse, screen: models.Screen) -> Optional[schemas.MediaRenditionResponse]:
    """
    Selects the most appropriate media rendition for a screen based on its hardware capabilities.
    """
    if not content.renditions:
        return None
        
    # Rule 2: If screen has never reported capabilities, return 720p (safe default)
    if screen.screen_width is None:
        safe_rend = next((r for r in content.renditions if r.resolution == "720p"), None)
        return safe_rend if safe_rend else None
        
    valid_renditions = list(content.renditions)
    
    # Rule 3: Drop any rendition whose codec the screen does not support.
    # ffprobe typically reports 'h264' or 'hevc'
    # Android MediaCodecList reports MIME types like 'video/avc' (h264) or 'video/hevc' (hevc)
    if screen.supported_video_codecs:
        codecs = screen.supported_video_codecs
        if isinstance(codecs, str):
            # In case it somehow got stored as string instead of list
            import json
            try:
                codecs = json.loads(codecs)
            except:
                codecs = []
        
        # Mappings from ffprobe codec name to Android MIME types
        codec_map = {
            "h264": ["video/avc"],
            "hevc": ["video/hevc", "video/x-h265"],
            "vp8": ["video/x-vnd.on2.vp8"],
            "vp9": ["video/x-vnd.on2.vp9"],
            "av1": ["video/av01"]
        }
        
        supported = []
        for rend in valid_renditions:
            if not rend.codec:
                supported.append(rend) # Be lenient if we don't know the codec
                continue
                
            mime_types = codec_map.get(rend.codec.lower(), [f"video/{rend.codec.lower()}"])
            if any(mime in codecs for mime in mime_types):
                supported.append(rend)
        valid_renditions = supported

    # Rule 4: Drop any rendition exceeding max_decode_width / max_decode_height
    if screen.max_decode_width and screen.max_decode_height:
        valid_renditions = [
            r for r in valid_renditions 
            if r.width <= screen.max_decode_width and r.height <= screen.max_decode_height
        ]
        
    # Rule 6: If total_ram_mb < 1536, cap at 720p (max dimension 1280)
    if screen.total_ram_mb and screen.total_ram_mb < 1536:
        # A 720p rendition is typically 1280x720 or 720x1280
        valid_renditions = [
            r for r in valid_renditions
            if max(r.width, r.height) <= 1280
        ]
        
    # Rule 5: Pick the largest that fits the panel
    # Never upscale beyond screen_width/screen_height
    # Rule 7: Portrait panels keep portrait renditions. (Width <= panel width, Height <= panel height ensures this)
    if screen.screen_width and screen.screen_height:
        valid_renditions = [
            r for r in valid_renditions
            if r.width <= screen.screen_width and r.height <= screen.screen_height
        ]
        
    if not valid_renditions:
        return None
        
    # Sort remaining renditions by resolution/size (pick the largest remaining)
    # We can use file_size_bytes or width * height as a proxy for "largest"
    valid_renditions.sort(key=lambda r: r.width * r.height, reverse=True)
    
    return valid_renditions[0]
