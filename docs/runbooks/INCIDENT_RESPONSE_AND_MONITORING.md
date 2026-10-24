# Production Monitoring & Incident Response Runbook

**Product:** AI Opportunity Assistant  
**Classification:** Internal DevOps & SRE Operating Procedure  
**Last Updated:** October 10, 2026  

---

## 1. System Health & Observability Metrics

The production system exposes real-time telemetry via:
- **Liveness Probe:** `GET /live` (Process responsive)
- **Readiness Probe:** `GET /ready` (Database & Redis healthy)
- **Prometheus Metrics:** `GET /metrics` (Request latency, counters, circuit breaker states)
- **Beta Analytics:** `GET /api/v1/beta/dashboard` (Aggregate click-through, save rate, costs)

---

## 2. Core Alert Thresholds

| Metric | Warning Threshold (P2) | Critical Alert Threshold (P1/P0) | Notification Target |
| :--- | :--- | :--- | :--- |
| **API Error Rate (5xx)** | > 2% over 5 min | > 5% over 2 min | SRE On-Call / PagerDuty |
| **P95 Latency** | > 800ms over 10 min | > 2000ms over 5 min | DevOps Slack Channel |
| **Search Provider Errors** | > 10% failures over 5 min | Circuit Breaker OPEN | Search Team |
| **Daily AI Spend** | > 80% daily budget ($80/day) | > 100% daily budget ($100/day) | Lead Engineer & Admin |
| **Database Pool Usage** | > 80% active connections | > 95% active connections | Database Admin |
| **Redis Memory** | > 75% max memory | > 90% max memory | DevOps Team |

---

## 3. Incident Severity Levels & Response Protocols

### Level P0 — Blocker / Service Down
- **Definition:** Complete API outage, authentication system failure, user data leak, or systemic data corruption.
- **SLA:** Initial response within **15 minutes**; continuous triage until mitigated.
- **Immediate Action:**
  1. Trigger maintenance mode via `MAINTENANCE_MODE=true` or route load balancer to static maintenance page.
  2. Assemble incident bridge with backend lead and infrastructure architect.
  3. Verify database integrity and error logs.
  4. Post status update to status page (`status.opportunity-assistant.com`).

### Level P1 — Major Degraded Functionality
- **Definition:** External search provider down, vector retrieval failing, email dispatch queue stalled, or daily cost limit breached.
- **SLA:** Initial response within **30 minutes**; mitigation within **2 hours**.
- **Immediate Action:**
  1. Toggle feature flag kill-switches (`live_web_search=false` or `semantic_discovery=false`).
  2. Fall back to cached indexed documents or lexical retrieval.
  3. Investigate upstream provider status (Tavily, OpenAI, SendGrid).

### Level P2 — Minor Issue / Elevated Latency
- **Definition:** Specific background job retries elevated, individual opportunity extraction failing, non-critical UI glitch.
- **SLA:** Triage within **4 hours** during business hours.

---

## 4. Feature Flag Kill-Switches (Emergency Mitigation)

To isolate faulty subsystems without redeploying code, use the feature flag API or Redis keys:
- `disable_live_search`: Deactivates live crawling; serves indexed catalog.
- `disable_ai_chat`: Disables assistant conversational inference while preserving browsing.
- `disable_notifications`: Pauses notification queues during email provider degradation.
- `maintenance_mode`: Instructs `MaintenanceModeMiddleware` to return HTTP 503 with friendly retry-after header.

---

## 5. Database Backup and Disaster Recovery Procedure

### Automated Daily Snapshots
- Managed PostgreSQL instances take automated point-in-time recovery (PITR) snapshots every 24 hours with WAL archiving retained for 30 days.

### Manual On-Demand Backup
```bash
pg_dump -h prod-db.internal.cluster -U app_prod_user -d opportunity_prod -Fc -f backup_$(date +%Y%m%d_%H%M%S).dump
```

### Recovery Verification Procedure (Tested Quarterly)
1. Provision isolated staging database target.
2. Restore snapshot:
   ```bash
   pg_restore -h staging-db -U app_user -d recovery_test_db -v backup_latest.dump
   ```
3. Run Alembic migration check:
   ```bash
   alembic current
   ```
4. Execute test suite against restored database to verify schema and relational constraint integrity.
