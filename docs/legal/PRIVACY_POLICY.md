# Privacy Policy — AI Opportunity Assistant

**Last Updated:** October 10, 2026  
**Effective Date:** October 10, 2026  
**Product Name:** AI Opportunity Assistant  
**Website / Support:** https://opportunity-assistant.com/support  
**Contact:** privacy@opportunity-assistant.com  

---

## 1. Overview and Scope

AI Opportunity Assistant ("we", "our", or "the App") is an AI-powered global discovery platform designed to help students, researchers, graduates, and professionals find scholarships, fellowships, grants, internships, and funding programs. We are committed to transparency, data protection, and privacy by design.

This Privacy Policy explains what personal information we collect, why we collect it, how it is stored and processed, and how you can exercise your legal rights under applicable data protection laws (including the EU/UK General Data Protection Regulation (GDPR) and the California Consumer Privacy Act (CCPA)).

---

## 2. Information We Collect

We strictly collect data necessary to provide personalized opportunity discovery, eligibility matching, and notifications.

### A. Account & Authentication Data
- **Email Address & Password Hash:** Collected during registration to secure your account. Passwords are cryptographically hashed using PBKDF2 / Argon2 and are never stored in plaintext.
- **Account Metadata:** Registration timestamp, last login date, and authentication session tokens (JWTs).

### B. Profile & Academic Information (User-Provided)
To calculate eligibility scores and rank relevant opportunities, you may optionally provide:
- **Academic History:** Degrees, institutions attended, fields of study, graduation dates, and GPA / grading scales.
- **Skills & Experience:** Technical skills, languages, publications, research interests, and work/internship history.
- **Target Preferences:** Desired study destinations, degree levels (Undergraduate, Master's, PhD, Postdoc), funding type preferences (fully funded vs. partial), and intended start dates.

### C. Search & AI Interactions
- **Search Queries:** Natural language queries entered into the search bar to find matching opportunities.
- **Conversational Queries:** Questions submitted to the grounded AI Assistant regarding opportunity details, application deadlines, or eligibility criteria.
- **Interaction Logs:** Aggregate click-throughs, saved opportunities, and user feedback ratings (e.g., helpful / not helpful flags) used to evaluate retrieval relevance.

### D. Technical & Diagnostic Information
- **Network & Device Telemetry:** IP address (used for rate-limiting and security abuse detection), request latency, device operating system version, and application build version.
- **Crash Reports:** Anonymous stack traces and diagnostic errors (collected via Sentry when enabled) to diagnose system stability.

---

## 3. How We Use Your Information

We process personal data solely for legitimate product purposes:
1. **Personalized Opportunity Matching:** Comparing your academic profile and preferences against structured criteria extracted from verified opportunities.
2. **Grounded AI Advice:** Providing contextual, factual answers grounded strictly in verified source materials.
3. **Deadline & Opportunity Tracking:** Sending alerts and notifications regarding saved deadlines when opted-in.
4. **Security & Abuse Prevention:** Enforcing rate limits, preventing distributed attacks, and defending against fraud.
5. **Quality Assurance:** Aggregating search quality metrics to detect stale links or extraction errors.

---

## 4. What We Do NOT Do

- **We do NOT sell your data:** We never sell, rent, or monetize your personal information to third-party data brokers or advertisers.
- **We do NOT share your profile for targeted third-party advertising.**
- **We do NOT submit applications without your knowledge:** The App provides advisory discovery; all official applications are completed directly by you on official university or provider portals.

---

## 5. Third-Party Service Providers & Data Transfers

We partner only with vetted technical infrastructure providers:
- **Cloud Hosting & Database Infrastructure:** Managed PostgreSQL and Redis hosting with encrypted network connections (TLS 1.3).
- **Search & Retrieval Providers:** External web search engines (e.g., Tavily / SerpAPI) receive anonymized search queries without user-identifiable profile data.
- **AI Inference Providers:** Context prompts sent to AI inference models (OpenAI, Anthropic, or self-hosted LLMs) contain only query parameters and anonymized criteria; your private identifying information (email, real name) is excluded.
- **Transactional Notifications:** SMTP/Email gateways (e.g., SendGrid) process email notifications when you request password resets or alert digests.

---

## 6. Data Retention and Security

- **Encryption in Transit:** All traffic between the Flutter mobile application and the FastAPI backend is encrypted via HTTPS / TLS 1.3.
- **Encryption at Rest:** Databases and disk volumes use AES-256 encryption at rest.
- **Session Security:** Short-lived access tokens (30 minutes) and revokable refresh tokens with secure blacklist revocation.

---

## 7. Your Rights: Access, Export, and Right to Be Forgotten

Under GDPR and CCPA, you have fundamental rights over your data:
- **Right to Access & Rectify:** You can view, update, and edit your profile, academic records, and preferences at any time in the App.
- **Right to Object / Restrict Processing:** You can disable optional notifications or telemetry in Settings.
- **Right to Erasure (Account Deletion):**
  - You can permanently delete your account directly inside the App by visiting **Settings → Account → Delete Account**, or by sending a request to `privacy@opportunity-assistant.com`.
  - When an account is deleted via `DELETE /api/v1/auth/account`, our backend immediately and irrevocably cascades the purge of your user record, profile, academic history, skills, saved opportunities, search sessions, and notification records. All active session tokens are revoked.

---

## 8. Children's Privacy

The App is intended for students, researchers, and adults pursuing higher education, research, and career opportunities. We do not knowingly collect personal data from children under the age of 13 (or under 16 in the EEA). If you believe a child has provided us with personal information, please contact us immediately.

---

## 9. Changes to this Privacy Policy

We may update this policy periodically to reflect product improvements or regulatory updates. We will notify users of material changes via an in-app banner or email before changes take effect.

---

## 10. Contact Us

If you have questions or concerns regarding this Privacy Policy:
- **Data Protection Officer:** `privacy@opportunity-assistant.com`
- **Support Portal:** https://opportunity-assistant.com/support
