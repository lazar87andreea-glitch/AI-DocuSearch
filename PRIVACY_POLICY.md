# Privacy Policy for AI DocuSearch

**Last Updated:** August 25, 2026  
**Effective Date:** August 25, 2026

## 1. Introduction

AI DocuSearch ("Service," "Application," "we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered document search application.

**Please read this Privacy Policy carefully.** If you do not agree with our policies and practices, please do not use our Service.

---

## 2. Data Controller & Compliance

This Service is GDPR-compliant and respects user privacy rights under:
- **General Data Protection Regulation (GDPR)** - EU/EEA residents
- **California Consumer Privacy Act (CCPA)** - California residents
- **Data Protection Laws** - Other applicable jurisdictions

---

## 3. Information We Collect

### 3.1 Information You Provide
- **Document Content**: Files you upload (PDF, DOCX, TXT) for text extraction and analysis
- **Questions & Queries**: Search questions and prompts you submit
- **Feedback**: Ratings, comments, and feedback on responses
- **Session Information**: Conversation history and interaction data

### 3.2 Information Automatically Collected
- **IP Address**: For language detection via browser location/geolocation
- **Browser Headers**: Accept-Language header for language preference
- **Session ID**: Unique identifier for tracking your session
- **Device Information**: Mobile/desktop detection for UI optimization
- **API Usage Metrics**: Token counts, response times, timestamps
- **LangSmith Traces**: Debug logs for AI model performance monitoring

### 3.3 Cookies & Tracking
- **Session Cookies**: Store user language preference and session state
- **No Third-party Analytics**: We do not use Google Analytics or similar trackers
- **Local Storage**: Session data persisted in browser (cleared on logout)

---

## 4. How We Use Your Information

We use collected information for:

| Purpose | Legal Basis | Retention |
|---------|------------|-----------|
| **Process queries** | Service performance | Duration of session |
| **Language detection** | User preference | Session only |
| **Improve AI accuracy** | Legitimate interest | 30 days (anonymized) |
| **Technical support** | Contractual obligation | 30 days |
| **Analytics & debugging** | Legitimate interest | 90 days max |
| **Legal compliance** | Legal obligation | As required |

---

## 5. Data Retention & Deletion

### 5.1 Automatic Cleanup
- **Chat History**: Deleted automatically after 30 days
- **Feedback Data**: Deleted automatically after 90 days
- **Session Data**: Deleted when session ends
- **Temporary Files**: Deleted after upload processing completes

### 5.2 User-Initiated Deletion
You can delete all your data at any time:
- Click "🗑️ Delete all my data (GDPR)" in the sidebar
- All stored questions, answers, feedback, and session data will be permanently removed
- **This action is irreversible**

### 5.3 Data Portability
You can download all your personal data at any time:
- Click "📥 Download my data (GDPR)" in the sidebar
- Export includes: questions, answers, feedback, metrics
- Format: JSON (machine-readable and portable to other services)

---

## 6. Third-Party Data Sharing

### 6.1 LangSmith (Debugging & Tracing)
- **Purpose**: Monitor AI model performance and debug issues
- **Data Shared**: Questions, answers, session metadata
- **Provider**: LangChain Inc.
- **Privacy Policy**: https://docs.smith.langchain.com/
- **Data Residency**: US (LangSmith servers)
- **Opt-out**: Set `LANGSMITH_TRACING=false` in environment

### 6.2 LLM Providers (OpenAI, Grok, Groq, etc.)
- **Purpose**: Process your questions through AI models
- **Data Shared**: Question text, document excerpts (required for AI processing)
- **Providers**: OpenAI, xAI, Groq, or other configured endpoints
- **Privacy Policy**: Check your provider's policy (e.g., https://openai.com/policies/privacy-policy)
- **Data Residency**: Depends on provider (usually US for major providers)

### 6.3 IP Geolocation (ip-api.com)
- **Purpose**: Detect your country for language localization
- **Data Shared**: Your IP address only
- **Provider**: ip-api.com
- **Privacy Policy**: https://ip-api.com/privacy
- **Fallback**: Browser Accept-Language header (no IP needed if available)

### 6.4 No Other Sharing
- ❌ We do NOT sell your data
- ❌ We do NOT share with marketing companies
- ❌ We do NOT use your data for advertising
- ❌ We do NOT share with social media platforms

---

## 7. Data Security

### Security Measures
- **Encryption in Transit**: HTTPS/TLS for all connections
- **Local Storage**: Sensitive files stored in temporary directories with restricted access
- **Access Control**: Only authorized processes access data
- **No Database**: Data stored as JSON files locally (not cloud)
- **Session Isolation**: Each user's data isolated by session ID

### Limitations
- No security measure is 100% secure
- Sensitive documents should be reviewed before uploading
- Do not upload documents containing passwords, API keys, or financial data
- Use VPN for additional privacy on public networks

---

## 8. Your Rights Under GDPR

### Right to Access (Article 15)
Request a copy of all personal data we hold about you
- Use: "📥 Download my data (GDPR)" button
- Or: Contact us (see Section 10)

### Right to Rectification (Article 16)
Request correction of inaccurate data
- Edit your questions/feedback directly in the interface
- Or: Contact us for assistance

### Right to Erasure (Article 17)
Request permanent deletion of your data ("Right to be Forgotten")
- Use: "🗑️ Delete all my data (GDPR)" button
- Or: Request via contact information in Section 10
- Automatic deletion after 30/90 days for historical data

### Right to Data Portability (Article 20)
Receive your data in structured, portable format
- Use: "📥 Download my data (GDPR)" button
- Format: JSON (portable to any service)

### Right to Object (Article 21)
Object to processing for legitimate interests
- Set environment: `LANGSMITH_TRACING=false`
- Email us to request additional restrictions

### Right to Restrict Processing (Article 18)
Request we limit how we use your data
- Contact us (Section 10) with specific restrictions
- We'll accommodate reasonable requests

### Right Not to Be Subject to Automated Decisions (Article 22)
Our AI decisions are not binding - always reviewed by you
- You can request human review of any answer
- Contact us if you believe a decision is unfair

---

## 9. CCPA Rights (California Residents)

If you are a California resident, you have:

- **Right to Know**: Request what personal data we collect (use data export feature)
- **Right to Delete**: Request deletion of personal data (use delete feature)
- **Right to Opt-Out**: Opt out of data sales (we don't sell data)
- **Right to Non-Discrimination**: No discrimination for exercising rights

California residents can submit requests by contacting us (Section 10).

---

## 10. Contact & Data Protection Officer

### Privacy Questions & Requests
**Email**: [your-contact-email]  
**GitHub**: https://github.com/lazar87andreea-glitch/AI-DocuSearch  
**Response Time**: We aim to respond within 30 days

### Data Protection Officer
If you have concerns about our data handling, you can contact:
- **Your Local Data Protection Authority** (DPA)
- **EU**: https://edpb.ec.europa.eu/edpb/node
- **UK**: https://ico.org.uk/
- **US**: Your state's privacy attorney general

---

## 11. Children's Privacy

Our Service is not directed to individuals under 13 years of age. We do not knowingly collect personal data from children under 13. If we become aware that we have collected personal data from a child under 13, we will delete such information promptly.

---

## 12. International Data Transfers

Your data may be processed in countries other than your residence (primarily US, where LLM providers are based). By using this Service, you consent to such transfers under GDPR adequacy or standard contractual clauses.

---

## 13. Changes to This Privacy Policy

We may update this Privacy Policy periodically. The "Last Updated" date above indicates the most recent changes. Continued use of the Service constitutes acceptance of changes.

---

## 14. Summary of Your Controls

| Control | Location | Effect |
|---------|----------|--------|
| **Download Data** | Sidebar "📥 Download my data" | Get JSON export of all data |
| **Delete Data** | Sidebar "🗑️ Delete my data" | Permanently remove all stored data |
| **Language Override** | NOT USED (auto-detected only) | - |
| **Disable Tracing** | Environment: `LANGSMITH_TRACING=false` | Stop debug logs from being sent |
| **Clear History** | Automatic after 30 days | Questions/answers auto-deleted |

---

## 15. Legal Basis for Processing (GDPR Article 6)

| Data | Legal Basis |
|------|------------|
| Questions & Answers | Performance of contract (service delivery) |
| Feedback & Ratings | Legitimate interest (improve service) |
| Session/IP Data | Legitimate interest (security, functionality) |
| LangSmith Traces | Legitimate interest (debugging, performance) |
| Language Detection | Legitimate interest (user experience) |

---

**By using AI DocuSearch, you acknowledge that you have read and understood this Privacy Policy.**

For more details, see our [Terms of Service](TERMS_OF_SERVICE.md).
