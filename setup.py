"""
Setup script for development environment.
"""
import os
import sys
from pathlib import Path


def setup_environment():
    """Setup development environment."""
    print("🔧 Setting up Jinkies development environment...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        sys.exit(1)
    
    print("✅ Python version OK")
    
    # Check if .env exists
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("📝 Creating .env from .env.example...")
            env_file.write_text(env_example.read_text())
            print("⚠️  Please edit .env with your credentials")
        else:
            print("❌ .env.example not found")
            sys.exit(1)
    else:
        print("✅ .env file exists")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    os.system(f"{sys.executable} -m pip install -r requirements.txt")
    
    print("✅ Setup complete!")
    print("\n📖 Next steps:")
    print("1. Edit .env with your credentials")
    print("2. Run: python run.py")
    print("3. Check README.md for more information")


if __name__ == "__main__":
    setup_environment()
