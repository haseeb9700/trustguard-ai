import os
import pandas as pd

AUDIT_LOG = "reports/audit_log.csv"


def get_audit_logs():
    if not os.path.exists(AUDIT_LOG):
        return {
            "status": "empty",
            "logs": []
        }

    df = pd.read_csv(AUDIT_LOG)

    logs = df.tail(20).iloc[::-1].to_dict(orient="records")

    return {
        "status": "success",
        "logs": logs
    }