# Observability

The Grafana and Prometheus workloads are part of the MediQueue Helm chart
(`helm/mediqueue/templates/monitoring.yaml`), so the dashboard travels with the
application instead of living in a separate manual install.

| File | Purpose |
| --- | --- |
| `values-local.yaml` | Exposes Prometheus and Grafana as NodePorts for the Kind demo |
| `values-aws.yaml` | Keeps them as ClusterIP services for a cluster behind an Ingress |
| `../helm/mediqueue/dashboards/mediqueue.json` | The provisioned `MediQueue / Service Health` dashboard |

## What Gets Scraped

The backend exposes `/metrics` in Prometheus text format. The chart adds a
headless `backend-metrics` Service so Prometheus discovers **every** backend
replica through DNS — one replica's counters cannot mask another's.

Prometheus scrapes port 8000 of every pod selected by `app=backend`, and two
alert rules ship with the chart:

- `MediQueueBackendUnavailable` — no scrape target is up for two minutes
- `MediQueueHighErrorRate` — more than 5% of responses are 5xx over five minutes

No external notification destination is configured; the alerts are visible in
the Prometheus UI only, which is a deliberate limitation of the local demo.

## Dashboard Panels

| Panel | Query |
| --- | --- |
| Healthy backend replicas | `sum(up{job="mediqueue"})` |
| Appointments requested per second | `sum(rate(mediqueue_http_requests_total[5m]))` |
| P95 request duration | `histogram_quantile(0.95, ...)` |
| Front-desk traffic by route | `sum by (route) (rate(mediqueue_http_requests_total[2m]))` |
| Responses by status code | `sum by (status) (rate(mediqueue_http_requests_total[2m]))` |

Request counters are labelled with **route templates**, never raw appointment or
doctor IDs, so dashboard cardinality stays bounded.

## Generating Traffic

Static health checks do not produce interesting graphs. Use the bounded load
generator:

```bash
python3 scripts/load.py --url http://mediqueue.localhost:8088 --seconds 60 --workers 4
```

Watch the dashboard at <http://localhost:3001> (username `admin`, password from
`scripts/grafana-password.sh`) and the raw targets at
<http://localhost:9090/targets>.
