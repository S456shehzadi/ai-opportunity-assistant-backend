# App Store Data Safety & Privacy Declarations

**Applicable to:** Google Play Console Data Safety & Apple App Store Privacy Nutrition Labels  
**Application Name:** AI Opportunity Assistant  
**Bundle ID / Package Name:** `com.opportunityai.assistant` (Android) / `ai_opportunity_assistant`  
**Last Verified:** October 10, 2026  

---

## 1. Google Play Console Data Safety Section

### Data Collection & Sharing Overview

| Question | Answer |
| :--- | :--- |
| Does your app collect or share any user data? | **Yes** |
| Is all data collected by your app encrypted in transit? | **Yes** (TLS 1.3 / HTTPS mandatory) |
| Do you provide a way for users to request that their data be deleted? | **Yes** (In-app `DELETE /api/v1/auth/account` + privacy email) |
| Does the app allow account creation? | **Yes** |
| Account deletion URL (for Play Console listing): | `https://opportunity-assistant.com/delete-account` |

---

### Data Types Collected

#### 1. Personal Info
- **Email address:**
  - *Collected:* Yes
  - *Shared:* No
  - *Purposes:* App functionality (Account management, password recovery, notifications)
  - *Optional or Required:* Required for account creation
- **Name:**
  - *Collected:* Yes (User display name)
  - *Shared:* No
  - *Purposes:* App personalization
  - *Optional or Required:* Optional
- **Academic / Career Information:**
  - *Collected:* Yes (Degrees, skills, target disciplines, GPA)
  - *Shared:* No
  - *Purposes:* App functionality (Eligibility matching, opportunity ranking)
  - *Optional or Required:* Optional

#### 2. App Activity
- **App interactions:**
  - *Collected:* Yes (Saved opportunities, search queries, feedback votes)
  - *Shared:* No
  - *Purposes:* App functionality, Analytics (Improving search retrieval quality)
  - *Optional or Required:* Optional

#### 3. App Info & Performance
- **Crash logs & Diagnostics:**
  - *Collected:* Yes (Anonymous crash stack traces via Sentry)
  - *Shared:* No (Transferred to first-party/service infrastructure)
  - *Purposes:* Analytics, Crash reporting, Performance diagnostics
  - *Optional or Required:* Automatic / System diagnostics

---

## 2. Apple App Store Privacy Nutrition Labels

### Data Used to Track You
- **None.** The App does not track users across apps and websites owned by other companies for advertising.

### Data Linked to You (Associated with User Account)
- **Contact Info:** Email address
- **User Content:** Academic profile records, skills, search preferences, saved opportunities
- **Identifiers:** User ID (internal relational identifier)

### Data Not Linked to You
- **Diagnostics:** Crash data, performance latency metrics (aggregated without user identity)

---

## 3. Account Deletion Compliance Verification

Both Google Play and Apple App Store require that apps supporting account creation must provide:
1. An easily discoverable in-app account deletion mechanism.
2. A public web link where users can submit account and data deletion requests without reinstalling the app.

**Implementation Status:**
- **In-App Deletion:** Implemented in `DELETE /api/v1/auth/account` (cascades deletion of profile, academic records, skills, saved opportunities, notifications, and revokes JWTs).
- **Public Deletion Web Link:** Provided at `https://opportunity-assistant.com/delete-account` routing to the privacy deletion queue.
