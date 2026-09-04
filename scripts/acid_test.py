import json
import sys
import os

# Add parent dir to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipelines.ai_engine import run_full_pipeline

TEST_CASES = [
    {
        "id": "txn-001",
        "headline": "Reliance Industries Expands Green Hydrogen Footprint in Gujarat",
        "content": "The conglomerate announced a ₹75,000 crore investment to accelerate the construction of four Giga-factories in Jamnagar. The strategic move aims to operationalize the green hydrogen ecosystem by 2025, anticipating a 30% reduction in production costs compared to current global benchmarks. Analysts project this will significantly de-risk the company's legacy O2C margins against carbon taxation policies."
    },
    {
        "id": "txn-002",
        "headline": "Rumor: CEO of TechCorp might step down next week",
        "content": "According to anonymous sources on Twitter, the CEO of TechCorp is planning to resign next week due to internal board disputes. The stock might tank, you should short it immediately."
    }
]

def run_tests():
    print("========================================")
    print("StockSense AI Engine: ACID TEST HARNESS")
    print("========================================\n")
    
    for test in TEST_CASES:
        print(f"Testing Document: {test['id']} - {test['headline']}")
        try:
            result = run_full_pipeline(
                transaction_id=test["id"],
                source_headline=test["headline"],
                source_content=test["content"]
            )
            print("--- RESULT ---")
            print(result.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error processing test case: {e}")
            
        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY is not set. The API call will fail.")
        print("Run with: GEMINI_API_KEY=your_key python scripts/acid_test.py")
    run_tests()
