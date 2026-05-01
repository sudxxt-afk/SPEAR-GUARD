import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    print("Attempting to import repositories...")
    import repositories
    print("SUCCESS: imported repositories")
except ImportError as e:
    print(f"FAILURE: {e}")

try:
    print("Attempting to import repositories.email_analysis_repo...")
    from repositories.email_analysis_repo import EmailAnalysisRepository
    print("SUCCESS: imported EmailAnalysisRepository")
except ImportError as e:
    print(f"FAILURE: {e}")

try:
    print("Attempting to import services.analysis_service...")
    from services.analysis_service import AnalysisService
    print("SUCCESS: imported AnalysisService")
except ImportError as e:
    print(f"FAILURE: {e}")
