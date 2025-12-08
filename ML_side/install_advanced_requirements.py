"""
Install additional requirements for advanced LLM integration
"""

import subprocess
import sys

def install_package(package):
    """Install package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Successfully installed {package}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")

def main():
    print("🔧 Installing Advanced LLM Integration Requirements...")
    
    # Required packages for LLM integration
    packages = [
        "requests",        # For API calls
        "openai",          # For OpenAI API (optional)
        "python-dotenv",   # For environment variables
        "tiktoken",        # For token counting (OpenAI)
    ]
    
    for package in packages:
        install_package(package)
    
    print("\n Installation completed!")
    print("\nTo use OpenAI integration:")
    print("1. Get an API key from https://platform.openai.com/")
    print("2. Set environment variable: export OPENAI_API_KEY='your-key-here'")
    print("3. Or add to .env file: OPENAI_API_KEY=your-key-here")
    
    print("\nTo use local models:")
    print("1. Install Ollama: https://ollama.ai/")
    print("2. Run: ollama pull llama2")
    print("3. Start Ollama service")

if __name__ == "__main__":
    main()