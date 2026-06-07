"""
Test script to verify all implemented modules can be imported without errors.
"""
import sys
import traceback

def test_import(module_name, description):
    """Test single module import and return result."""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_name}")
        print(f"   Error: {str(e)}")
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("AI Agent Module Import Test")
    print("=" * 60)
    print()

    results = []

    # Core modules
    print("### Core Modules ###")
    results.append(test_import("config.settings", "Settings"))
    results.append(test_import("collectors.kis_client", "KIS Client"))
    results.append(test_import("collectors.dart_client", "DART Client"))
    results.append(test_import("collectors.news_collector", "News Collector"))
    print()

    # Analysis modules (Stages 2-1, 2-2, 2-3)
    print("### Analysis Modules ###")
    results.append(test_import("analysis.quantitative", "Quantitative Analyzer"))
    results.append(test_import("analysis.sentiment", "Sentiment Analyzer"))
    results.append(test_import("analysis.timeseries", "Time-Series Analyzer"))
    print()

    # ML/NLP models
    print("### ML/NLP Models ###")
    results.append(test_import("models.kr_finbert", "KR-FinBERT"))
    results.append(test_import("models.prophet_trainer", "Prophet Trainer"))
    print()

    # AI decision generator (Stage 4)
    print("### AI Decision Generator ###")
    results.append(test_import("ai.gemini_client", "Gemini Client"))
    results.append(test_import("ai.decision_generator", "Decision Generator"))
    print()

    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Import Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All modules imported successfully!")
        return 0
    else:
        print(f"⚠️ {total - passed} modules failed to import")
        return 1

if __name__ == "__main__":
    sys.exit(main())
