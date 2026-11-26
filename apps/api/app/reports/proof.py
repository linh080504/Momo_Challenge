from uuid import uuid4


def issue_result(event, signer, owner):
    result = event["result"]
    result["analysis_id"] = signer.issue("analysis", {
        "id": uuid4().hex, "owner": owner, "keys": event["keys"], "risk": result["risk_level"],
        "group": result["scenario_group"],
        "signals": [item["finding"] for item in result["evidence"] if item["weight"] > 0][:6],
    }, 1800)
    return result
