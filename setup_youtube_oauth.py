#!/usr/bin/env python3
"""
Setup script for YouTube OAuth configuration.
"""
import json
import os
import sys

def create_oauth_config():
    """Create YouTube OAuth configuration file."""
    
    print("🔧 YouTube OAuth Setup")
    print("=" * 50)
    
    # Get user input
    client_id = input("Enter your Client ID: ").strip()
    if not client_id:
        client_id = "118594423108-6hspek0j3khu43vj4mb-ko2l8l7fiopS.apps.googleusercontent.com"
        print(f"Using default Client ID: {client_id}")
    
    client_secret = input("Enter your Client Secret (the ****pKOH part): ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return False
    
    project_id = input("Enter your Project ID (optional): ").strip()
    if not project_id:
        project_id = "youtube-analytics-dashboard"
    
    # Create OAuth configuration
    oauth_config = {
        "web": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [
                "http://localhost:8000/api/v1/youtube-auth/callback"
            ]
        }
    }
    
    # Save to file
    config_path = "youtube_oauth_config.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(oauth_config, f, indent=2)
        
        print(f"✅ OAuth configuration saved to {config_path}")
        print("\n🚀 Next steps:")
        print("1. Restart your backend server")
        print("2. Test the authorization: curl http://localhost:8000/api/v1/youtube-auth/authorize")
        print("3. Visit the returned URL to complete OAuth flow")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

def test_oauth_config():
    """Test if OAuth configuration is valid."""
    
    config_path = "youtube_oauth_config.json"
    
    if not os.path.exists(config_path):
        print(f"❌ Configuration file {config_path} not found")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        web_config = config.get('web', {})
        
        missing_fields = [field for field in required_fields if not web_config.get(field)]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ OAuth configuration is valid!")
        print(f"   Client ID: {web_config['client_id'][:20]}...")
        print(f"   Project ID: {web_config.get('project_id', 'Not set')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_oauth_config()
    else:
        create_oauth_config()
