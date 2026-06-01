#!/usr/bin/env python3
"""
Brevo Image Uploader
Pulls images from private GitHub repo and uploads to Brevo
Writes results directly to GitHub repo
"""

import os
import sys
import json
import base64
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
# Try multiple locations: current dir, parent dirs, or specific path
env_path = None
possible_paths = [
    '.env',
    '../.env',
    '../../.env',
    os.path.expanduser('~/Documents/github/cnsdojo-main/.env')
]

for path in possible_paths:
    if os.path.exists(path):
        env_path = path
        break

if env_path:
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {os.path.abspath(env_path)}")
else:
    load_dotenv()  # Load from default location

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'CNSeattle/cnsdojo')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

BREVO_API_URL = 'https://api.brevo.com/v3/emailCampaigns/images'
GITHUB_API_URL = 'https://api.github.com'
OUTPUT_FILE_PATH = 'Extras/brevo-assets/brevo-asset-url.md'
MAPPING_FILE_PATH = 'Extras/brevo-assets/brevo-asset-mapping.json'



def validate_config():
    """Validate required environment variables"""
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not found in .env")
        sys.exit(1)
    if not BREVO_API_KEY:
        print("ERROR: BREVO_API_KEY not found in .env")
        sys.exit(1)
    print("✓ Configuration loaded")


def upload_to_brevo(image_url, image_name):
    """Upload image URL to Brevo and return Brevo URL"""
    headers = {
        'api-key': BREVO_API_KEY,
        'Content-Type': 'application/json'
    }

    payload = {
        'imageUrl': image_url,
        'name': image_name
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        brevo_url = data.get('url')
        return brevo_url
    except requests.exceptions.RequestException as e:
        try:
            error_detail = response.json()
            print(f"✗ Failed to upload {image_name}: {e} - {error_detail}")
        except:
            print(f"✗ Failed to upload {image_name}: {e}")
        return None


def process_images(image_list):
    """Process list of image filenames and upload to Brevo"""
    results = []

    for image_file in image_list:
        image_file = image_file.strip()
        if not image_file:
            continue

        image_url = f'https://raw.githubusercontent.com/CNSeattle/brevo/main/brevo-assets/{image_file}'

        print(f"Uploading: {image_file}...", end=' ')
        brevo_url = upload_to_brevo(image_url, image_file)

        if brevo_url:
            print("✓")
            results.append({
                'filename': image_file,
                'brevo_url': brevo_url
            })
        else:
            print("✗")

    return results


def get_file_sha(file_path):
    """Get the SHA of an existing file in GitHub"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'{GITHUB_API_URL}/repos/{GITHUB_REPO}/contents/{file_path}?ref={GITHUB_BRANCH}'

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('sha')
        return None
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch existing file SHA: {e}")
        return None


def push_to_github(content, file_path):
    """Push content to GitHub repo"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Get existing file SHA if it exists (for updating)
    sha = get_file_sha(file_path)

    # Encode content to base64
    encoded_content = base64.b64encode(content.encode()).decode()

    payload = {
        'message': f'Update Brevo asset URLs - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        'content': encoded_content,
        'branch': GITHUB_BRANCH
    }

    # Add SHA if file exists
    if sha:
        payload['sha'] = sha

    url = f'{GITHUB_API_URL}/repos/{GITHUB_REPO}/contents/{file_path}'

    try:
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"✓ Results pushed to GitHub: {file_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to push to GitHub: {e}")
        return False


def format_markdown(results):
    """Format results as Markdown table"""
    content = '# Brevo Asset URLs\n\n'
    content += f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
    content += '| Filename | Brevo URL |\n'
    content += '|----------|----------|\n'

    for result in results:
        content += f'| {result["filename"]} | {result["brevo_url"]} |\n'

    return content


def main():
    validate_config()

    # Get image list from command line or file
    if len(sys.argv) > 1:
        # Command line arguments (space-separated filenames)
        image_list = sys.argv[1:]
    else:
        # Read from input_images.txt if it exists
        if os.path.exists('input_images.txt'):
            with open('input_images.txt', 'r') as f:
                image_list = f.readlines()
            print(f"✓ Loaded {len(image_list)} images from input_images.txt")
        else:
            print("Usage: python brevo_uploader.py image1.jpg image2.png ...")
            print("   OR: Create input_images.txt with one filename per line")
            sys.exit(1)

    # Process images
    results = process_images(image_list)

    if results:
        # Format and write to local file and push to GitHub
        content = format_markdown(results)

        # Write to local file
        with open(OUTPUT_FILE_PATH, 'w') as f:
            f.write(content)
        print(f"✓ Results written to: {OUTPUT_FILE_PATH}")

        push_to_github(content, OUTPUT_FILE_PATH)
        print(f"\n✓ Successfully uploaded {len(results)} images")
    else:
        print("\n✗ No images were successfully uploaded")
        sys.exit(1)


if __name__ == '__main__':
    main()
