# Apple App Store Submission Guide & Checklist

**Application Name:** AI Opportunity Assistant  
**Bundle Identifier:** `com.opportunityai.assistant` (matches `ios/Runner/Info.plist`)  
**Target Platform:** iOS 14.0+  
**Build Tooling Requirement:** macOS with Xcode 15+ & CocoaPods  
**Current Host Environment Note:** The current build and CI environment is Windows; building and signing the `.ipa` binary must be executed on a macOS runner or Mac build machine.  
**Last Updated:** October 10, 2026  

---

## 1. App Store Connect Metadata

| Field | Content |
| :--- | :--- |
| **App Name** | `AI Opportunity Assistant` (Max 30 characters) |
| **Subtitle** | `Grounded Scholarships & Grants` (30 characters) |
| **Primary Category** | Education |
| **Secondary Category** | Productivity |
| **Keywords** | `scholarships,grants,fellowships,education,college,university,research,funding,study abroad,internships` (Max 100 characters) |
| **Support URL** | `https://opportunity-assistant.com/support` |
| **Marketing URL** | `https://opportunity-assistant.com` |
| **Privacy Policy URL** | `https://opportunity-assistant.com/privacy-policy` |

---

## 2. App Review Information

- **Sign-in Required:** Yes
- **Reviewer Demo Account:**
  - **Username / Email:** `appstore.reviewer@opportunity-assistant.com`
  - **Password:** `AppleReviewer2026!`
- **Demo Notes:** Reviewer account has full access to test profile creation, searching, grounded chat, and in-app account deletion.
- **Contact Info:** Provide release engineer name, phone, and `release@opportunity-assistant.com`.

---

## 3. App Privacy Disclosures (Nutrition Labels)

- **Data Used to Track You:** None.
- **Data Linked to You:**
  - Contact Info (Email)
  - User Content (Academic profile details, saved items)
  - Identifiers (User ID)
- **Data Not Linked to You:**
  - Diagnostics (Crash data and performance logs)

---

## 4. macOS Build Instructions (For Developer on macOS Machine)

To build the signed `.ipa` on a Mac:
```bash
# 1. Install dependencies
cd ios && pod install && cd ..

# 2. Build release archive with production defines
flutter build ipa --release \
  --dart-define=APP_ENV=production \
  --export-options-plist=ios/ExportOptions.plist

# 3. Validate and upload to App Store Connect
xcrun altool --validate-app -f build/ios/ipa/*.ipa -t ios -u YOUR_APPLE_ID -p YOUR_APP_SPECIFIC_PASSWORD
xcrun altool --upload-app -f build/ios/ipa/*.ipa -t ios -u YOUR_APPLE_ID -p YOUR_APP_SPECIFIC_PASSWORD
```
