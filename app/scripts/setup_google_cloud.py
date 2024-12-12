import os
import json
from pathlib import Path
import subprocess
import sys

def setup_google_cloud():
    """Setup Google Cloud credentials"""
    print("\nGoogle Cloud Setup")
    print("-----------------")
    
    # Check if credentials file exists
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path and os.path.exists(creds_path):
        print(f"âœ“ Found existing credentials at: {creds_path}")
        return
    
    print("\nNo credentials found. Please follow these steps:")
    print("1. Go to Google Cloud Console: https://console.cloud.google.com")
    print("2. Create a new project or select existing project")
    print("3. Enable Vertex AI API")
    print("4. Create a service account and download the JSON key file")
    
    # Get credentials file path
    while True:
        creds_file = input("\nEnter path to your credentials JSON file: ").strip()
        if os.path.exists(creds_file):
            break
        print("File not found. Please try again.")
    
    # Create credentials directory if it doesn't exist
    creds_dir = Path.home() / '.google-cloud'
    creds_dir.mkdir(exist_ok=True)
    
    # Copy credentials to a secure location
    target_path = creds_dir / 'beaver-credentials.json'
    try:
        with open(creds_file, 'r') as source:
            creds_data = json.load(source)
        with open(target_path, 'w') as target:
            json.dump(creds_data, target)
        
        # Set environment variable
        if sys.platform.startswith('win'):
            os.system(f'setx GOOGLE_APPLICATION_CREDENTIALS "{target_path}"')
        else:
            shell = os.path.basename(os.environ.get('SHELL', '/bin/bash'))
            rc_file = Path.home() / f'.{shell}rc'
            with open(rc_file, 'a') as f:
                f.write(f'\nexport GOOGLE_APPLICATION_CREDENTIALS="{target_path}"\n')
        
        print(f"\nâœ“ Credentials saved to: {target_path}")
        print(f"âœ“ Environment variable GOOGLE_APPLICATION_CREDENTIALS set")
        print("\nPlease restart your terminal for changes to take effect.")
        
    except Exception as e:
        print(f"\nError setting up credentials: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    setup_google_cloud()