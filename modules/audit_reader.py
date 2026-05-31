import os
import pandas as pd

AUDIT_LOG = "reports/audit_log.csv"


def get_audit_logs(limit=20):

    if not os.path.exists(AUDIT_LOG):
        return {
            "status": "empty",
            "count": 0,
            "logs": []
        }

    try:
        df = pd.read_csv(AUDIT_LOG)

        if df.empty:
            return {
                "status": "empty",
                "count": 0,
                "logs": []
            }

        # newest first
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                errors="coerce"
            )

            df = df.sort_values(
                by="timestamp",
                ascending=False
            )

        logs = (
            df
            .head(limit)
            .fillna("")
            .to_dict(
                orient="records"
            )
        )

        return {
            "status": "success",
            "count": len(df),
            "returned": len(logs),
            "logs": logs
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e),
            "logs": []
        }