"""
Quick test script to verify vector retrieval works
"""
import sys
from core.vector_retriever import get_vector_retriever

print("Testing Vector Retriever...")
print("=" * 50)

try:
    retriever = get_vector_retriever()
    print("[OK] VectorRetriever initialized")

    # Test mucgec search
    print("\n1. Testing MUCGEC (correction) search...")
    results = retriever.search_semantic("语法错误怎么改", "mucgec", top_k=3)
    print(f"   Found {len(results)} results")
    if results:
        print(f"   Top result: {results[0]['text'][:100]}...")

    # Test softwares search
    print("\n2. Testing SOFTWARES (Moodle) search...")
    results = retriever.search_semantic("Moodle课程设置", "softwares", top_k=3)
    print(f"   Found {len(results)} results")
    if results:
        print(f"   Top result score: {results[0]['score']:.2%}")

    # Test teacher search
    print("\n3. Testing TEACHER search...")
    results = retriever.search_semantic("教师素养标准", "teacher", top_k=3)
    print(f"   Found {len(results)} results")

    # Test HSK search
    print("\n4. Testing HSK search...")
    results = retriever.search_hsk_vocab("爱", level="1")
    print(f"   Found {len(results)} results")

    print("\n" + "=" * 50)
    print("[OK] All tests passed!")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
