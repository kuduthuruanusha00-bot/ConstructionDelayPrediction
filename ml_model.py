import pandas as pd
from sklearn.tree import DecisionTreeClassifier


# ==========================================
# TRAINING DATA
# ==========================================

data = {
    "progress": [95, 85, 75, 65, 55, 45, 35, 25, 15, 10, 80, 60],
    "days_remaining": [25, 20, 15, 20, 15, 10, 5, 3, 2, -2, 30, 7],
    "dependency": [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1],
    "utilization": [50, 55, 60, 70, 75, 80, 90, 95, 95, 100, 50, 85],
    "risk": [
        "Low",
        "Low",
        "Low",
        "Medium",
        "Medium",
        "Medium",
        "High",
        "High",
        "High",
        "High",
        "Low",
        "High"
    ]
}


df = pd.DataFrame(data)


# ==========================================
# INPUT FEATURES
# ==========================================

X = df[
    [
        "progress",
        "days_remaining",
        "dependency",
        "utilization"
    ]
]

y = df["risk"]


# ==========================================
# TRAIN MODEL
# ==========================================

model = DecisionTreeClassifier(
    random_state=42,
    max_depth=4
)

model.fit(X, y)


# ==========================================
# PREDICTION FUNCTION
# ==========================================

def predict_risk(
    progress,
    days_remaining,
    dependency,
    utilization
):

    input_data = pd.DataFrame(
        [[
            progress,
            days_remaining,
            dependency,
            utilization
        ]],
        columns=[
            "progress",
            "days_remaining",
            "dependency",
            "utilization"
        ]
    )

    prediction = model.predict(input_data)

    return prediction[0]


# ==========================================
# TEST MODEL
# ==========================================

if __name__ == "__main__":

    result = predict_risk(
        progress=40,
        days_remaining=13,
        dependency=1,
        utilization=80
    )

    print("Predicted Risk:", result)