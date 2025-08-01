# setup.py - Bot setup and installation script
import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'downloads', 'cache', 'temp']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")

def setup_env_file():
    """Setup environment file"""
    if not Path('.env').exists():
        if Path('.env.template').exists():
            print("📝 Creating .env file from template...")
            with open('.env.template', 'r') as template:
                content = template.read()
            
            with open('.env', 'w') as env_file:
                env_file.write(content)
            
            print("✅ .env file created!")
            print("⚠️  Please edit .env file with your actual bot tokens and settings")
        else:
            print("❌ .env.template not found!")
    else:
        print("✅ .env file already exists")

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found!")
        print("Please install FFmpeg:")
        print("- Windows: Download from https://ffmpeg.org/download.html")
        print("- Ubuntu/Debian: sudo apt install ffmpeg")
        print("- macOS: brew install ffmpeg")
        return False

def main():
    """Main setup function"""
    print("🎵 Ultimate Music Bot Setup")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Setup environment file
    setup_env_file()
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    
    if not ffmpeg_ok:
        print("⚠️  Warning: FFmpeg not found. Audio playback may not work.")
    
    print("\nNext steps:")
    print("1. Edit .env file with your bot tokens")
    print("2. Set your OWNER_ID in .env")
    print("3. Run: python run.py")
    print("\nFor deployment on Render:")
    print("1. Set environment variables in Render dashboard")
    print("2. Deploy using render.yaml or Dockerfile")
    
    return True

if __name__ == "__main__":
    main()
