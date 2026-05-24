import pandas as pd
import os
from datetime import datetime

AUDIT_LOG = "reports/audit_log.csv"


def log_audit(result):

    os.makedirs("reports", exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(),
        "query": result["query"],
        "answer": result["answer"],
        "hallucination_analysis": str(
            result["hallucination_analysis"]
        ),
        "risk_level": result["risk_analysis"]["risk_level"],
        "risk_reason": result["risk_analysis"]["risk_reason"]
    }

    df = pd.DataFrame([row])

    if os.path.exists(AUDIT_LOG):
        df.to_csv(
            AUDIT_LOG,
            mode="a",
            header=False,
            index=False
        )
    else:
        df.to_csv(
            AUDIT_LOG,
            index=False
        )

    print(f"Audit log saved to {AUDIT_LOG}")