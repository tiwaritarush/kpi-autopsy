import gzip
from pathlib import Path
from xml.etree import ElementTree as ET


def write_log(path: Path) -> Path:
    cases = {
        "A": [
            ("A_Create Application", "2016-01-01T00:00:00Z", None),
            ("A_Accepted", "2016-01-01T01:00:00Z", None),
            ("O_Create Offer", "2016-01-01T03:00:00+01:00", "a1"),
            ("O_Accepted", "2016-01-03T00:00:00Z", "a1"),
            ("A_Pending", "2016-01-03T00:00:01Z", None),
        ],
        "B": [
            ("A_Create Application", "2016-01-01T12:00:00Z", None),
            ("A_Accepted", "2016-01-01T13:00:00Z", None),
            ("O_Create Offer", "2016-01-01T16:00:00Z", "b1"),
            ("O_Create Offer", "2016-01-02T01:00:00Z", "b2"),
            ("A_Cancelled", "2016-01-05T00:00:00Z", None),
        ],
        "C": [
            ("A_Create Application", "2015-12-31T23:00:00Z", None),
            ("A_Accepted", "2015-12-31T23:30:00Z", None),
            ("O_Create Offer", "2016-01-02T00:00:00Z", "c1"),
            ("O_Accepted", "2016-01-04T00:00:00Z", "c1"),
            ("A_Pending", "2016-01-04T00:00:01Z", None),
        ],
        "D": [
            ("A_Create Application", "2016-01-03T00:00:00Z", None),
            ("A_Accepted", "2016-01-03T01:00:00Z", None),
            ("A_Incomplete", "2016-01-04T00:00:00Z", None),
            ("W_Call incomplete files", "2016-02-02T00:00:00Z", None),
        ],
        "E": [
            ("A_Create Application", "2016-01-02T00:00:00Z", None),
            ("A_Accepted", "2016-01-02T01:00:00Z", None),
            ("O_Create Offer", "2016-01-04T00:00:00Z", "e1"),
            ("O_Accepted", "2016-01-12T00:00:00Z", "e1"),
            ("A_Pending", "2016-01-12T00:00:01Z", None),
        ],
        "F": [
            ("A_Create Application", "2016-01-04T00:00:00Z", None),
            ("A_Accepted", "2016-01-04T00:30:00Z", None),
            ("O_Create Offer", "2016-01-04T01:00:00Z", "f1"),
            ("A_Cancelled", "2016-01-06T00:00:00Z", None),
        ],
    }
    root = ET.Element("log", xmlns="http://www.xes-standard.org/")
    for identity, events in cases.items():
        trace = ET.SubElement(root, "trace")
        for key, value in {"concept:name": identity, "ApplicationType": "New credit",
                           "LoanGoal": "Car", "RequestedAmount": "10000"}.items():
            ET.SubElement(trace, "string", key=key, value=value)
        for index, (activity, timestamp, offer) in enumerate(events):
            event = ET.SubElement(trace, "event")
            origin = "Application" if activity.startswith("A_") else "Offer" if activity.startswith("O_") else "Workflow"
            attrs = {"concept:name": activity, "time:timestamp": timestamp,
                     "EventID": f"{identity}-{index}", "EventOrigin": origin,
                     "lifecycle:transition": "complete"}
            if offer:
                attrs["OfferID"] = offer
                attrs["OfferedAmount"] = "10000"
            for key, value in attrs.items():
                ET.SubElement(event, "string", key=key, value=value)
    with gzip.open(path, "wb") as stream:
        stream.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return path
