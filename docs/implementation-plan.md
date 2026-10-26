# Implementation plan

1. Verify SC1 tariff leaves and General Rules; record dates, sources and unsupported rules.
2. Import a single electricity consumption stream from CSV or ESPI XML, preserve UTC instants,
   report invalid/duplicate/overlapping/missing intervals, reject ambiguous wall-clock times.
3. Simulate verified standard base delivery for explicit billing periods, including 30-day
   proration, seasonal thresholds and day-weighted tariff changes. Generate an offline report.
4. Add Rate III TOU with its actual all-days windows. Keep demand plans unsupported when
   meter aggregation cannot be verified. Include tested demand arithmetic for future work only.
5. Import actual component totals and separately sourced plan-specific charge inputs;
   reconcile baseline by period and component. Suppress recommendations unless all gates pass.
6. Test synthetic fixtures including DST, period boundaries, tariffs and recommendation gates;
   demonstrate CLI, package and publish only code, research and synthetic data.
