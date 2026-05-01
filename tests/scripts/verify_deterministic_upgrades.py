import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from analyzers.contextual_analyzer import ContextualAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_contextual_analyzer():
    analyzer = ContextualAnalyzer()
    
    print("\n--- Testing Contextual Analyzer Deterministic Upgrades ---\n")

    # TestCase 1: Fuzzy Matching
    print("Test 1: Fuzzy Matching ('P@ssw0rd', 'Urgentt')")
    res1 = await analyzer.analyze(
        from_address="hack@bad.com",
        to_address="victim@gov.ru",
        subject="Very Urgentt Request",
        body_preview="Please reset your P@ssw0rd immediately."
    )
    if "Fuzzy keyword match" in str(res1['issues']):
        print("✅ PASS: Deteced fuzzy keywords")
    else:
        print(f"❌ FAIL: Did not detect fuzzy keywords. Issues: {res1['issues']}")

    # TestCase 2: Homoglyphs (Latin 'a' in Cyrillic word or vice versa)
    print("\nTest 2: Homoglyph Detection")
    # 'Sberbank' where 'a' is cyrillic 'а' (U+0430)
    # Latin S(U+0053), b(U+0062), e(U+0065), r(U+0072), b(U+0062), CYRILLIC а(U+0430), n(U+006E), k(U+006B)
    mixed_word = "Sberb\u0430nk" 
    res2 = await analyzer.analyze(
        from_address="bad@bad.com",
        to_address="victim@gov.ru",
        subject=f"Update from {mixed_word}",
        body_preview="Security alert."
    )
    if "Possible homoglyph attack" in str(res2['issues']):
        print(f"✅ PASS: Detected homoglyph '{mixed_word}'")
    else:
        print(f"❌ FAIL: Did not detect homoglyph. Issues: {res2['issues']}")

    # TestCase 3: Link Hygiene
    print("\nTest 3: Link Hygiene")
    html_body = """
    <html>
        <body>
            <p>Please login here: 
            <a href="http://evil-site.com/login">http://secure-gosuslugi.ru/login</a>
            </p>
        </body>
    </html>
    """
    res3 = await analyzer.analyze(
        from_address="bad@bad.com",
        to_address="victim@gov.ru",
        subject="Login",
        body_html=html_body
    )
    if "Deceptive link" in str(res3['issues']):
        print("✅ PASS: Detected deceptive link")
    else:
        print(f"❌ FAIL: Did not detect deceptive link. Issues: {res3['issues']}")

if __name__ == "__main__":
    asyncio.run(test_contextual_analyzer())
