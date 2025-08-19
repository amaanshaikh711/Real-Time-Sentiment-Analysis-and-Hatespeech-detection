#!/usr/bin/env python3
"""
Favicon Generator for HateSense AI
Generates favicon files from the logo URL
"""

import requests
from PIL import Image, ImageDraw, ImageFont
import io
import os

def create_favicon():
    """Create favicon files for HateSense AI"""
    
    # Logo URL from your navbar
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ6u2GaWZHiyXqheenkO4ISJSxodgY_wN_a6A&s"
    
    try:
        # Download the logo
        response = requests.get(logo_url)
        response.raise_for_status()
        
        # Open the image
        img = Image.open(io.BytesIO(response.content))
        
        # Create different sizes
        sizes = {
            'favicon-16x16.png': (16, 16),
            'favicon-32x32.png': (32, 32),
            'apple-touch-icon.png': (180, 180)
        }
        
        # Create static directory if it doesn't exist
        os.makedirs('static', exist_ok=True)
        
        for filename, size in sizes.items():
            # Resize the image
            resized_img = img.resize(size, Image.Resampling.LANCZOS)
            
            # Save the favicon
            filepath = os.path.join('static', filename)
            resized_img.save(filepath, 'PNG')
            print(f"Created {filepath}")
        
        # Create ICO file (16x16)
        ico_img = img.resize((16, 16), Image.Resampling.LANCZOS)
        ico_path = os.path.join('static', 'favicon.ico')
        ico_img.save(ico_path, 'ICO')
        print(f"Created {ico_path}")
        
        print("✅ All favicon files created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating favicon: {e}")
        print("Creating a simple text-based favicon instead...")
        
        # Create a simple text-based favicon as fallback
        create_text_favicon()

def create_text_favicon():
    """Create a simple text-based favicon as fallback"""
    
    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Create a simple favicon with "HA" text
    sizes = {
        'favicon-16x16.png': (16, 16),
        'favicon-32x32.png': (32, 32),
        'apple-touch-icon.png': (180, 180)
    }
    
    for filename, size in sizes.items():
        # Create a new image with purple background
        img = Image.new('RGBA', size, (138, 43, 226, 255))  # Purple background
        
        # Add text "HA" (HateSense AI)
        draw = ImageDraw.Draw(img)
        
        # Calculate font size (about 60% of image height)
        font_size = int(size[1] * 0.6)
        
        try:
            # Try to use a system font
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Calculate text position to center it
        text = "HA"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        # Draw white text
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
        # Save the favicon
        filepath = os.path.join('static', filename)
        img.save(filepath, 'PNG')
        print(f"Created {filepath}")
    
    # Create ICO file
    ico_img = Image.new('RGBA', (16, 16), (138, 43, 226, 255))
    draw = ImageDraw.Draw(ico_img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except:
        font = ImageFont.load_default()
    
    text = "HA"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (16 - text_width) // 2
    y = (16 - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    ico_path = os.path.join('static', 'favicon.ico')
    ico_img.save(ico_path, 'ICO')
    print(f"Created {ico_path}")
    
    print("✅ Fallback favicon files created successfully!")

if __name__ == "__main__":
    print("🎨 Generating favicon files for HateSense AI...")
    create_favicon()
