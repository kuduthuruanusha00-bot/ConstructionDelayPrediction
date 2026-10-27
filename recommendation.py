def get_recommendation(
    risk,
    progress,
    days_remaining,
    utilization
):
    if risk == "High":

        if utilization >= 90:
            return (
                "High Risk: Increase workforce or equipment. "
                "Resource utilization is very high."
            )

        elif progress < 50:
            return (
                "High Risk: Increase manpower and equipment "
                "to improve task progress."
            )

        elif days_remaining <= 3:
            return (
                "High Risk: Deadline is very close. "
                "Assign additional resources immediately."
            )

        else:
            return (
                "High Risk: Closely monitor the task and "
                "increase resources if required."
            )

    elif risk == "Medium":

        if utilization >= 80:
            return (
                "Medium Risk: Consider adding resources "
                "and monitor utilization."
            )

        elif progress < 50:
            return (
                "Medium Risk: Increase manpower to improve "
                "task progress."
            )

        elif days_remaining <= 7:
            return (
                "Medium Risk: Deadline is approaching. "
                "Monitor the task closely."
            )

        else:
            return (
                "Medium Risk: Continue monitoring task "
                "progress and resources."
            )

    else:

        return (
            "Low Risk: Resources are currently sufficient. "
            "Continue regular monitoring."
        )


if __name__ == "__main__":

    result = get_recommendation(
        risk="Medium",
        progress=40,
        days_remaining=7,
        utilization=80
    )

    print("Resource Recommendation:")
    print(result)