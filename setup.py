#!/usr/bin/env python3
import os
import argparse
import logging
import sys
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup')

# Model URLs
MODEL_URLS = {
    "llama-2-7b": "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf",
    "mistral-7b": "https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf",
}

def create_directories():
    """Create necessary directories for the project"""
    dirs = ["models", "data", "temp_audio"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        logger.info(f"Created directory: {dir_name}")

def download_model(model_name, output_dir="models"):
    """Download a model from Hugging Face"""
    if model_name not in MODEL_URLS:
        available_models = ", ".join(MODEL_URLS.keys())
        logger.error(f"Model {model_name} not found. Available models: {available_models}")
        return False
    
    url = MODEL_URLS[model_name]
    filename = url.split("/")[-1]
    output_path = os.path.join(output_dir, filename)
    
    # Check if model already exists
    if os.path.exists(output_path):
        logger.info(f"Model {filename} already exists at {output_path}")
        return True
    
    # Download model
    logger.info(f"Downloading {model_name} from {url}...")
    try:
        # Use curl for better progress reporting
        result = subprocess.run(
            ["curl", "-L", url, "-o", output_path],
            check=True
        )
        logger.info(f"Downloaded {model_name} to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download model: {e}")
        return False

def setup_environment():
    """Create a .env file from the example if it doesn't exist"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as example, open(".env", "w") as env:
                env.write(example.read())
            logger.info("Created .env file from example")
        else:
            logger.warning(".env.example not found, skipping .env creation")

def install_dependencies(metal_support=True):
    """Install required Python dependencies"""
    try:
        if metal_support:
            # Install llama-cpp-python with Metal support
            logger.info("Installing llama-cpp-python with Metal support...")
            os.environ["CMAKE_ARGS"] = "-DLLAMA_METAL=on"
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "llama-cpp-python"],
                check=True
            )
        
        # Install other dependencies
        logger.info("Installing other dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        
        logger.info("Dependencies installed successfully")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Setup Discord Meeting Notes Bot")
    parser.add_argument("--model", choices=["llama-2-7b", "mistral-7b"], default="llama-2-7b",
                        help="LLM model to download (default: llama-2-7b)")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--no-metal", action="store_true", help="Skip Metal support for llama-cpp-python")
    
    args = parser.parse_args()
    
    logger.info("Setting up Discord Meeting Notes Bot")
    
    # Create directories
    create_directories()
    
    # Set up environment file
    setup_environment()
    
    # Install dependencies
    if not args.no_deps:
        install_dependencies(metal_support=not args.no_metal)
    
    # Download the chosen model
    download_model(args.model)
    
    logger.info("Setup complete!")
    logger.info("To start the bot, run: python main.py")

if __name__ == "__main__":
    main() 