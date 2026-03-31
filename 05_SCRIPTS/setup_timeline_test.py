#!/usr/bin/env python3
"""
Quick Test Setup Script for Timeline Director
Generates sample video and audio files for testing
"""

import os
import sys
from pathlib import Path

def create_sample_files():
    """Create sample video and audio files for testing"""
    root = Path(__file__).resolve().parents[2]
    video_dir = root / "02_INPUT" / "video"
    audio_dir = root / "02_INPUT" / "audio"
    
    # Create directories
    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    print("📁 Directories created:")
    print(f"   ✓ {video_dir}")
    print(f"   ✓ {audio_dir}")
    
    # Try to create sample files with ffmpeg if available
    try:
        import subprocess
        
        # Check if ffmpeg is available
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n🎬 Generating sample video (10s)...")
            video_file = video_dir / "sample_intro.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-f", "lavfi",
                    "-i", "color=c=blue:s=1920x1080:d=10",
                    "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=10",
                    "-pix_fmt", "yuv420p",
                    "-y",
                    str(video_file)
                ],
                capture_output=True
            )
            if video_file.exists():
                size_mb = video_file.stat().st_size / 1024 / 1024
                print(f"   ✓ Created: {video_file.name} ({size_mb:.2f} MB)")
            
            print("\n🎵 Generating sample audio (30s)...")
            audio_file = audio_dir / "sample_music.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=30",
                    "-q:a", "9",
                    "-acodec", "libmp3lame",
                    "-y",
                    str(audio_dir / "sample_music.mp3")
                ],
                capture_output=True
            )
            
            # Also create WAV
            subprocess.run(
                [
                    "ffmpeg",
                    "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=30",
                    "-y",
                    str(audio_file)
                ],
                capture_output=True
            )
            if audio_file.exists():
                size_mb = audio_file.stat().st_size / 1024 / 1024
                print(f"   ✓ Created: {audio_file.name} ({size_mb:.2f} MB)")
            
            return True
        else:
            print("⚠️  ffmpeg not found. Creating placeholder files instead...")
            return False
            
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"⚠️  Could not generate files: {e}")
        return False

def create_placeholder_files():
    """Create placeholder files to show the directory structure"""
    root = Path(__file__).resolve().parents[2]
    video_dir = root / "02_INPUT" / "video"
    audio_dir = root / "02_INPUT" / "audio"
    
    # Create .gitkeep files
    (video_dir / ".sample_video_here").touch()
    (audio_dir / ".sample_audio_here").touch()
    
    print("\n📝 Created placeholder files.")
    print("   To test, add your own media files to:")
    print(f"   - {video_dir}/")
    print(f"   - {audio_dir}/")

if __name__ == "__main__":
    print("🎬 Timeline Director - Test Setup\n")
    
    success = create_sample_files()
    
    if not success:
        create_placeholder_files()
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Start the dashboard: python 05_SCRIPTS/dashboard/app.py")
    print("2. Open browser: http://localhost:8787/timeline-editor")
    print("3. Add tracks and import sample media")
    print("4. Save configuration to test pipeline integration")
