# Automatic Insights

**Report → Insights** shows findings that are calculated automatically from data already stored in the database. There is no external service and no AI/LLM: everything is statistics whose numbers can be explained. Every finding carries its own figures and the comparison it was judged against.

## When it runs

The worker runs the analysis every 30 minutes (and one minute after the worker starts). A Super Admin can run it manually with **Analyze now** on the Insights page. The result and the time of the last run are listed in Admin → System → Source Status (source "Insight").

## How findings are judged

- **Anomaly:** the latest value is compared with what is normal, that is the median and the robust deviation (MAD) of earlier data, using the same weekday when there is a weekly pattern. A finding appears when the robust z-score is above 3 and the absolute difference is large enough, so small fluctuations are ignored.
- **Trend and forecast:** a linear regression slope over recent days (availability, ticket volume), projected forward and compared with the target (`net.target`).
- **Repeats:** counts inside a time window (flapping links, flapping devices, the same host in many XDR alerts).
- **SLA risk:** open tickets whose age is approaching or past the SLA target (`cfg.sla`).
- **Cross-source correlation:** several signals at the same location (links, devices, tickets) that go wrong together point to a cause at the location, not at the ISP.
- **Incident grouping:** events within 10-minute windows are grouped into one incident.
- **Location health score:** link 45%, devices 35%, tickets 20%, shown per location.
- **Shift summary:** a plain-text summary of the top findings, generated from templates (no LLM), which can be added to the handover.

Checks are skipped when there are fewer than 5 comparison points, so WiFi and device findings only appear once enough history has been collected.

## Page layout

Findings, rankings (top-N), the location health table, and the shift summary are on one page under the Report menu. Insights are calculated from historical data, so the period, shift, and location filters do not apply.

## Finding status

- **New:** just detected and not yet read. Click **Acknowledge** after viewing.
- **Acknowledged:** seen, still active.
- **Resolved:** not detected in the next analysis. Resolved findings stay visible for 14 days.
- **Dismissed:** hidden for the chosen number of days (`suppress_until`), then evaluated again.

New warning and critical findings are sent once through the webhook when the **New insight** event is selected in Admin → Notifications → Webhooks.

## Changing thresholds

Thresholds are in `backend/app/insight.py` (`ZCUT`, `MIN_BASE`, and the conditions inside each `d_*` function). Adding a new check means adding one function that returns a list of findings and registering it in `DETECTORS`.
