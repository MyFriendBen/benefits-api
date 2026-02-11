#!/usr/bin/env python
"""
Quick test script to verify Google Cloud Translate is working with updated dependencies.
Run with: python test_translation.py
"""
import json
from decouple import config
from google.oauth2 import service_account
from google.cloud import translate_v2 as translate
import html

def test_google_translate():
    print("=" * 60)
    print("Testing Google Cloud Translate Integration")
    print("=" * 60)

    try:
        # Initialize credentials
        print("\n1. Loading Google credentials...")
        info = json.loads(config("GOOGLE_APPLICATION_CREDENTIALS"))
        creds = service_account.Credentials.from_service_account_info(info)
        print("✓ Credentials loaded successfully")

        # Create client
        print("\n2. Creating translate client...")
        client = translate.Client(credentials=creds)
        print("✓ Client created successfully")

        # Test simple translation
        print("\n3. Testing translation (English -> Spanish)...")
        test_text = "Hello, this is a test of the translation system."
        result = client.translate(
            test_text,
            target_language='es',
            source_language='en'
        )

        translated = html.unescape(result['translatedText'])
        print(f"   Original: {test_text}")
        print(f"   Translated: {translated}")
        print("✓ Translation successful")

        # Test bulk translation
        print("\n4. Testing bulk translation (English -> Spanish, French)...")
        texts = ["Good morning", "Good afternoon", "Good evening"]

        # Translate to Spanish
        es_results = client.translate(texts, target_language='es', source_language='en')
        print("   Spanish translations:")
        for orig, res in zip(texts, es_results):
            print(f"      {orig} -> {html.unescape(res['translatedText'])}")

        # Translate to French
        fr_results = client.translate(texts, target_language='fr', source_language='en')
        print("   French translations:")
        for orig, res in zip(texts, fr_results):
            print(f"      {orig} -> {html.unescape(res['translatedText'])}")

        print("✓ Bulk translation successful")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Google Cloud Translate is working!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_google_translate()
    exit(0 if success else 1)
