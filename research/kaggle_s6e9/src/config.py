import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_EXT_DIR = BASE_DIR / "data" / "external"
OOF_DIR = BASE_DIR / "oof"
SUBMISSIONS_DIR = BASE_DIR / "submissions"

TRAIN_PATH = DATA_RAW_DIR / "train.csv"
TEST_PATH = DATA_RAW_DIR / "test.csv"
SAMPLE_SUB_PATH = DATA_RAW_DIR / "sample_submission.csv"
ORIGINAL_DATA_PATH = DATA_EXT_DIR / "EV_Adoption_and_Range_Anxiety_Dataset.csv"

# Ensure runtime directories exist
OOF_DIR.mkdir(parents=True, exist_ok=True)
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Training Hyperparameters
RANDOM_SEED = 42
N_FOLDS = 10
TARGET_COL = "Will_Buy_EV"
ID_COL = "id"

# Categorical and Numerical Columns
CATEGORICAL_COLS = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]

NUMERICAL_COLS = [
    "Age",
    "Annual_Income_USD",
    "Daily_Commute_km",
    "Number_of_Cars_Owned",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Environmental_Concern_Level",
]
