"""
Icon Manager for Warframe Relic Companion.
Downloads and caches Warframe icons (mastery ranks, currencies, etc.)
Also creates custom mastery rank badges.
"""

import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def get_icons_dir() -> str:
    """Get the icons directory path."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    
    icons_dir = os.path.join(base, "icons")
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    return icons_dir


def create_hexagon_points(cx: int, cy: int, radius: int) -> list:
    """Create points for a hexagon centered at (cx, cy)."""
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 90)  # Start from top
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((x, y))
    return points


def create_mastery_badge(rank: int, size: int = 50) -> Image.Image:
    """
    Create a custom mastery rank badge as a hexagon.
    
    Colors based on rank tier:
    - 0-9: Silver/Gray
    - 10-19: Gold
    - 20-29: White/Platinum
    - 30+: Legendary (Purple/Gold gradient look)
    """
    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = size // 2, size // 2
    outer_radius = size // 2 - 2
    inner_radius = outer_radius - 3
    
    # Determine colors based on rank
    if rank >= 30:
        # Legendary - Purple/Gold
        outer_color = (147, 112, 219)  # Medium purple
        inner_color = (75, 0, 130)     # Dark purple
        text_color = (255, 215, 0)     # Gold text
    elif rank >= 20:
        # True Master - White/Silver
        outer_color = (200, 200, 210)
        inner_color = (40, 40, 50)
        text_color = (255, 255, 255)
    elif rank >= 10:
        # Gold tier
        outer_color = (218, 165, 32)   # Goldenrod
        inner_color = (30, 30, 40)
        text_color = (255, 215, 0)
    else:
        # Silver tier
        outer_color = (169, 169, 169)
        inner_color = (30, 30, 40)
        text_color = (220, 220, 220)
    
    # Draw outer hexagon (border)
    outer_points = create_hexagon_points(cx, cy, outer_radius)
    draw.polygon(outer_points, fill=outer_color)
    
    # Draw inner hexagon (fill)
    inner_points = create_hexagon_points(cx, cy, inner_radius)
    draw.polygon(inner_points, fill=inner_color)
    
    # Draw the rank number
    # Try to use a bold font, fall back to default
    font_size = size // 3 if rank < 10 else size // 4
    try:
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    text = str(rank)
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = cx - text_width // 2
    text_y = cy - text_height // 2 - 2  # Slight adjustment for visual centering
    
    draw.text((text_x, text_y), text, fill=text_color, font=font)
    
    return img


def get_mastery_icon_path(rank: int, size: int = 50) -> str:
    """
    Get the path to a mastery rank icon (official Warframe stone icons).
    
    Args:
        rank: Mastery rank (0-34, supports Legendary ranks as 31-34)
        size: Icon size in pixels
        
    Returns:
        Path to the icon file
    """
    rank = max(0, min(34, rank))  # Clamp to valid range (0-30 + L1-L4)
    icons_dir = get_icons_dir()
    
    # Check for sized version first
    sized_path = os.path.join(icons_dir, f"mr_{rank}_{size}.png")
    if os.path.exists(sized_path):
        return sized_path
    
    # Check for official icon (downloaded from Wiki)
    original_path = os.path.join(icons_dir, f"mr_{rank}.png")
    if os.path.exists(original_path):
        try:
            img = Image.open(original_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            img.save(sized_path, 'PNG')
            return sized_path
        except Exception as e:
            print(f"Error resizing mastery icon: {e}")
    
    # Fall back to custom hexagon badge
    img = create_mastery_badge(rank, size)
    img.save(sized_path, 'PNG')
    
    return sized_path


def download_icon(url: str, save_path: str, size: tuple = None) -> bool:
    """Download an icon from URL and optionally resize it."""
    if not HAS_REQUESTS:
        return False
    
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'WarframeRelicCompanion/1.0'
        })
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        img.save(save_path, 'PNG')
        return True
    except Exception as e:
        print(f"Failed to download icon: {e}")
        return False


def create_platinum_icon(size: int = 20) -> Image.Image:
    """Create a simple platinum gem icon."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Platinum colors
    light_plat = (200, 220, 255)
    dark_plat = (100, 150, 200)
    
    # Draw a simple diamond/gem shape
    cx, cy = size // 2, size // 2
    r = size // 2 - 2
    
    # Diamond points
    points = [
        (cx, cy - r),           # Top
        (cx + r, cy),           # Right
        (cx, cy + r),           # Bottom
        (cx - r, cy),           # Left
    ]
    
    # Draw main shape
    draw.polygon(points, fill=light_plat, outline=dark_plat)
    
    # Add a center highlight
    inner_r = r // 2
    inner_points = [
        (cx, cy - inner_r),
        (cx + inner_r, cy),
        (cx, cy + inner_r),
        (cx - inner_r, cy),
    ]
    draw.polygon(inner_points, fill=(230, 240, 255))
    
    return img


def get_platinum_icon_path(size: int = 20) -> str:
    """Get the path to the platinum icon."""
    icons_dir = get_icons_dir()
    icon_path = os.path.join(icons_dir, f"platinum_{size}.png")
    
    if os.path.exists(icon_path):
        return icon_path
    
    # Check if we have the original platinum.png from warframe.market
    original_path = os.path.join(icons_dir, "platinum.png")
    if os.path.exists(original_path):
        try:
            img = Image.open(original_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            img.save(icon_path, 'PNG')
            return icon_path
        except Exception as e:
            print(f"Error resizing platinum icon: {e}")
    
    # Try to download from warframe.market
    url = 'https://warframe.market/static/assets/icons/en/platinum.png'
    if download_icon(url, icon_path, size=(size, size)):
        return icon_path
    
    # Fall back to creating our own
    img = create_platinum_icon(size)
    img.save(icon_path, 'PNG')
    return icon_path


def get_credits_icon_path(size: int = 20) -> str:
    """Get the path to the credits icon (official Warframe icon)."""
    icons_dir = get_icons_dir()
    icon_path = os.path.join(icons_dir, f"credits_{size}.png")
    
    if os.path.exists(icon_path):
        return icon_path
    
    # Check if we have the original credits.png downloaded from Wiki
    original_path = os.path.join(icons_dir, "credits.png")
    if os.path.exists(original_path):
        try:
            img = Image.open(original_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            img.save(icon_path, 'PNG')
            return icon_path
        except Exception as e:
            print(f"Error resizing credits icon: {e}")
    
    # Try to download from Wiki
    url = 'https://static.wikia.nocookie.net/warframe/images/2/2b/Credits.png/revision/latest'
    if download_icon(url, icon_path, size=(size, size)):
        return icon_path
    
    # Fall back to creating a simple credits icon
    img = create_credits_icon(size)
    img.save(icon_path, 'PNG')
    return icon_path


def create_credits_icon(size: int = 20) -> Image.Image:
    """Create a simple credits icon fallback (golden coin)."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Gold colors
    gold_outer = (218, 165, 32)
    gold_inner = (255, 215, 0)
    
    # Draw a simple coin circle
    margin = 2
    draw.ellipse([margin, margin, size - margin, size - margin], 
                 fill=gold_inner, outline=gold_outer)
    
    return img


def get_ducats_icon_path(size: int = 20) -> str:
    """Get the path to the ducats icon (official Warframe icon)."""
    icons_dir = get_icons_dir()
    icon_path = os.path.join(icons_dir, f"ducats_{size}.png")
    
    if os.path.exists(icon_path):
        return icon_path
    
    # Check if we have the original ducats.png downloaded from Wiki
    original_path = os.path.join(icons_dir, "ducats.png")
    if os.path.exists(original_path):
        try:
            img = Image.open(original_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            img.save(icon_path, 'PNG')
            return icon_path
        except Exception as e:
            print(f"Error resizing ducats icon: {e}")
    
    # Try to download from Wiki
    url = 'https://static.wikia.nocookie.net/warframe/images/d/d5/OrokinDucats.png/revision/latest'
    if download_icon(url, icon_path, size=(size, size)):
        return icon_path
    
    # Fall back to creating a simple ducats icon
    img = create_ducats_icon(size)
    img.save(icon_path, 'PNG')
    return icon_path


def create_ducats_icon(size: int = 20) -> Image.Image:
    """Create a simple ducats icon fallback (golden diamond)."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Orokin gold/bronze colors
    outer_color = (205, 133, 63)   # Bronze
    inner_color = (255, 215, 0)    # Gold
    
    cx, cy = size // 2, size // 2
    r = size // 2 - 2
    
    # Diamond points (rotated square)
    points = [
        (cx, cy - r),     # Top
        (cx + r, cy),     # Right
        (cx, cy + r),     # Bottom
        (cx - r, cy),     # Left
    ]
    
    draw.polygon(points, fill=inner_color, outline=outer_color)
    
    return img


# Test
if __name__ == "__main__":
    print("Creating mastery badges...")
    
    for rank in [5, 15, 25, 30, 32]:
        path = get_mastery_icon_path(rank, 50)
        print(f"MR{rank}: {path}")
    
    print("\nCurrency icons:")
    path = get_platinum_icon_path(20)
    print(f"Platinum: {path}")
    
    path = get_credits_icon_path(20)
    print(f"Credits: {path}")
    
    path = get_ducats_icon_path(20)
    print(f"Ducats: {path}")
