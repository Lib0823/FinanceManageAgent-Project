#!/usr/bin/env python3
"""Test Gemini API models and connectivity"""
import google.generativeai as genai
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

def test_gemini_api():
    settings = get_settings()
    api_key = settings.gemini_api_key

    print(f"API Key: {api_key[:20]}..." if api_key else "No API key found")
    print()

    if not api_key:
        print("❌ No API key configured")
        return

    try:
        # Configure API
        genai.configure(api_key=api_key)
        print("✅ API key configured successfully")
        print()

        # List available models
        print("=" * 80)
        print("Available Models:")
        print("=" * 80)

        for model in genai.list_models():
            print(f"\nModel: {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description[:100] if model.description else 'N/A'}")
            print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")
            print(f"  Input Token Limit: {model.input_token_limit if hasattr(model, 'input_token_limit') else 'N/A'}")
            print(f"  Output Token Limit: {model.output_token_limit if hasattr(model, 'output_token_limit') else 'N/A'}")

        print()
        print("=" * 80)
        print("Testing generateContent with available models:")
        print("=" * 80)
        print()

        # Test each model that supports generateContent
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name
                print(f"Testing {model_name}...")

                try:
                    test_model = genai.GenerativeModel(model_name)
                    response = test_model.generate_content("Say 'Hello' in one word")

                    print(f"  ✅ SUCCESS: {model_name}")
                    print(f"  Response: {response.text[:100]}")
                    print()

                    # If we found a working model, we can stop
                    print(f"\n🎉 Found working model: {model_name}")
                    print(f"   Use this in gemini_client.py: MODEL_NAME = '{model_name}'")
                    break

                except Exception as e:
                    print(f"  ❌ FAILED: {model_name}")
                    print(f"  Error: {str(e)[:200]}")
                    print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_api()
