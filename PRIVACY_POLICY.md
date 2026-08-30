# Privacy Policy for AI DocuSearch

**Last Updated:** August 30, 2026
**Effective Date:** August 30, 2026

## 1. Introduction

AI DocuSearch ("Service" or "Application") is a free experimental personal project operated by Andreea Nistor. It is currently provided for testing and evaluation, without production-service, availability, or support guarantees. This Privacy Policy explains how information is processed when you test the Application.

**Please read this Privacy Policy carefully.** If you do not agree with our policies and practices, please do not use our Service.

---

## 2. Project Operator and Data Controller

For data processed directly by this Application, the data controller is:

- **Name:** Andreea Nistor
- **Email:** lazar87andreea@gmail.com
- **Project:** AI DocuSearch, a personal project offered free of charge for experimental testing

The operator is an individual, not a company, and has not appointed a Data Protection Officer. The project aims to handle personal data consistently with applicable privacy requirements, including GDPR rights where they apply. Because this is an experimental service, users should not upload confidential, highly sensitive, or business-critical documents.

---

## 3. Information We Collect

### 3.1 Information You Provide
- **Document Content**: Files you upload (PDF, DOCX, TXT) for text extraction and analysis
- **Questions & Queries**: Search questions and prompts you submit
- **Feedback**: Ratings, comments, and feedback on responses
- **Session Information**: Conversation history and interaction data

### 3.2 Information Automatically Collected
- **Language Signals**: The Application may attempt to read an available `Accept-Language` header or perform server-side IP geolocation to choose a language. Depending on the hosting platform, these signals may describe the hosting server rather than the individual user and may be unavailable.
- **Session ID**: Unique identifier for tracking your session
- **Device Signal**: The Application may attempt to infer whether the browser is mobile when a user-agent signal is available. It does not intentionally create a detailed device profile.
- **API Usage Metrics**: Token counts, response times, timestamps
- **LangSmith Traces**: Debug logs for AI model performance monitoring

### 3.3 Cookies & Tracking
- **Session Connection**: Streamlit uses a browser connection to associate you with server-side session state while the Application is open.
- **No Third-party Analytics**: We do not use Google Analytics or similar trackers
- **Server-side Session State**: Language preference, uploaded-document state, and cost counters are primarily held in temporary server-side session state, not as permanent browser local storage. Session state may be lost when the tab disconnects or the server restarts.

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
- **Temporary Uploaded Files**: Uploaded files are copied to an application-specific directory on the host system only for extraction and PDF page counting. The application deletes each temporary copy immediately after that processing succeeds or fails. It keeps extracted text and an in-memory retrieval index for the active session instead of retaining the uploaded file. On startup, it also removes application-created upload files older than one hour that may have survived an interrupted server process.

### 5.2 User-Initiated Deletion
You can delete all your data at any time:
- Use "🗑️ Delete Data" in the Privacy & Data Management footer
- This removes the current session's locally stored questions, answers, feedback, and in-memory document state
- Temporary uploaded-file copies have already been removed after extraction; this control does not guarantee deletion of data already processed or retained by configured LLM providers or LangSmith
- **This action is irreversible**

### 5.3 Data Portability
You can download all your personal data at any time:
- Use "📥 Download Data" in the Privacy & Data Management footer
- Export includes: questions, answers, feedback, metrics
- Format: JSON (machine-readable and portable to other services)

---

## 6. Third-Party Data Sharing

### 6.1 LangSmith (Debugging & Tracing)
- **Purpose**: Monitor AI model performance, debug issues, and associate Helpful/Not helpful ratings with the answer trace when LangSmith feedback collection is enabled
- **Data Shared**: Questions, answers, session metadata, and positive or negative answer ratings
- **Provider**: LangChain Inc.
- **Privacy Policy**: https://docs.smith.langchain.com/
- **Data Residency**: US (LangSmith servers)
- **Tracing control**: Tracing is controlled by the Application operator through deployment configuration. Users cannot currently disable it from the interface. Do not use the Application if you do not consent to this processing while tracing is enabled.

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
- **Temporary Processing**: Uploaded files are held in an application-specific temporary directory only during extraction and page counting, then deleted
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
- The Application does not currently provide an interface for editing stored questions or feedback
- Contact the project operator for assistance using the address in Section 10

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
- The current interface does not provide an individual tracing opt-out
- Stop using the Application and email the project operator to request additional restrictions or deletion where supported

### Right to Restrict Processing (Article 18)
Request we limit how we use your data
- Contact us (Section 10) with specific restrictions
- We'll accommodate reasonable requests

### Right Not to Be Subject to Automated Decisions (Article 22)
AI-generated answers are informational outputs and do not make binding decisions about users. The Application does not currently provide a formal human-review workflow. Do not rely on an answer as legal, medical, financial, or other professional advice.

---

## 9. CCPA Rights (California Residents)

If you are a California resident, you have:

- **Right to Know**: Request what personal data we collect (use data export feature)
- **Right to Delete**: Request deletion of personal data (use delete feature)
- **Right to Opt-Out**: Opt out of data sales (we don't sell data)
- **Right to Non-Discrimination**: No discrimination for exercising rights

California residents can submit requests by contacting us (Section 10).

---

## 10. Contact

### Privacy Questions & Requests
**Operator**: Andreea Nistor

**Email**: lazar87andreea@gmail.com

**GitHub**: https://github.com/lazar87andreea-glitch/AI-DocuSearch  
**Response Time**: We aim to respond within 30 days

No Data Protection Officer has been appointed because this is an individually operated experimental project, not a company. If you have concerns about data handling, contact the operator first. You may also contact:
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
| **Download Data** | Footer "📥 Download Data" | Get a JSON export of locally associated session data |
| **Delete Data** | Footer "🗑️ Delete Data" | Remove current-session history, feedback, and in-memory document state; third-party copies are subject to provider controls and retention policies |
| **Language Override** | Not currently available | Language is automatically detected when possible and otherwise defaults to English |
| **Disable Tracing** | Not currently available to users | Deployment configuration is controlled by the project operator |
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

For more details, open the Terms of Service page in the Application.
