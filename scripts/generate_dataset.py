import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.evaluation.dataset.generator import generate_dataset

if __name__ == "__main__":
    generate_dataset("backend/evaluation/dataset/cases")
