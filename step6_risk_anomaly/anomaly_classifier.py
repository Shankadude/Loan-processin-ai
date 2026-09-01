from typing import Any, Dict, List

from .schemas import Anomaly


def classify_anomalies(
    detected_anomalies: List[Dict[str, Any]]
) -> List[Anomaly]:
    """
    Convert detected anomaly dictionaries into
    structured Anomaly objects.
    """

    anomalies = []

    for item in detected_anomalies:

        anomaly = Anomaly(

            code=item.get(
                "code",
                "UNKNOWN_ANOMALY"
            ),

            severity=item.get(
                "severity",
                "MEDIUM"
            ),

            description=item.get(
                "description",
                ""
            ),

            source=item.get(
                "source",
                "unknown"
            ),

            evidence=item.get(
                "evidence",
                {}
            )
        )

        anomalies.append(
            anomaly
        )

    return anomalies