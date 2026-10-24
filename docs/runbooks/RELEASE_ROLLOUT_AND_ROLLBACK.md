# Controlled Rollout & Rollback Protocol

**Product:** AI Opportunity Assistant  
**Classification:** Deployment & Release Management  
**Last Updated:** October 10, 2026  

---

## 1. Staged Rollout Strategy

To prevent cascading failures and protect user experience, releases follow a 5-stage phased rollout:

```text
Internal Testing (Day 0) 
       ↓
Closed Beta / Canary (Day 1 - 2, 5% cohort) 
       ↓
Staged Public Rollout (Day 3, 20% cohort) 
       ↓
Expanded Rollout (Day 5, 50% cohort) 
       ↓
Global General Availability (Day 7, 100% cohort)
```

---

## 2. Release Gates & Stage Progression Criteria

Before advancing from one cohort stage to the next, the following gate criteria must be satisfied for at least 24 consecutive hours:
1. **Crash-Free User Rate:** $\ge 99.5\%$ on Google Play / Sentry.
2. **API 5xx Error Rate:** $\le 0.5\%$.
3. **P95 Latency:** $\le 1000\text{ ms}$.
4. **P0 / P1 Triage Reports:** 0 unaddressed critical correctness or security bugs.
5. **Cost Compliance:** Daily AI and search provider expenditures remain below budget ceiling ($100/day).

---

## 3. Rollback Triggers

An automated or manual rollback is mandated immediately if ANY of the following occur:
- **Crash Rate Surge:** Crash-free session rate falls below $98.5\%$.
- **Security or Privacy Breach:** Cross-user data leakage or authentication bypass detected.
- **Hallucinated Opportunity Epidemic:** AI assistant returns non-existent scholarships or fabricated deadlines.
- **Runaway Infrastructure Spend:** Cost burn rate exceeds $150\%$ of budgeted daily projection.
- **Database Connection Saturation:** Unresolvable pool exhaustion causing widespread HTTP 503s.

---

## 4. Rollback Execution Procedure

### A. Mobile App (Google Play Console)
1. Navigate to **Google Play Console → Release → Production → Staged Rollout**.
2. Click **Halt Rollout** immediately.
3. If critical bug affects existing users, upload hotfix bundle (`versionCode + 1`) with bug fix or reverted commit to 100% rollout.

### B. Backend API (FastAPI / Kubernetes / Cloud Run)
1. Re-route traffic to previous stable container revision:
   ```bash
   kubectl rollout undo deployment/backend-api
   ```
2. Verify previous pods are receiving traffic and `/ready` returns HTTP 200.
3. Validate database compatibility:
   - *Rule:* All database migrations must be forward- and backward-compatible (expand-contract pattern). Destructive schema drops are never executed in the same release as application code.

### C. Feature Flag Instant Isolation
If the issue is isolated to a specific module (e.g. conversational assistant or live search):
- Disable the module via remote configuration without triggering a full deployment:
  ```bash
  curl -X PATCH https://api.opportunity-assistant.com/api/v1/beta/features/live_web_search \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d '{"is_enabled": false}'
  ```
