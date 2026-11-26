from uuid import uuid4


def issue_result(event, signer, owner):
    result = event["result"]
    document = result.get("document")
    forensics = ({"ocr_regions": len(document["ocr_boxes"]), "jpeg_regions": len(document["recompression_regions"])}
                 if document else {})
    result["analysis_id"] = signer.issue("analysis", {
        "id": uuid4().hex, "owner": owner, "keys": event["keys"], "risk": result["risk_level"],
        "group": result["scenario_group"],
        "inputs": event["inputs"],
        "forensics": forensics,
        "sources": sorted({item["source"] for item in result["evidence"] if item["weight"] > 0}),
        "signals": [item["finding"] for item in result["evidence"] if item["weight"] > 0][:6],
    }, 1800)
    return result
