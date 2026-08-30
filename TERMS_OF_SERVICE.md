# Terms of Service for AI DocuSearch

**Last Updated:** August 30, 2026
**Effective Date:** August 30, 2026

## 1. Service Status and Operator

AI DocuSearch (the "Service") is a free experimental personal project operated by Andreea Nistor. It is currently provided for testing and evaluation, without production-service, availability, support, or data-recovery guarantees. The operator is an individual, not a company.

Contact: lazar87andreea@gmail.com

Do not use the Service for business-critical work or upload confidential, highly sensitive, or irreplaceable information.

## 2. Acceptance and Eligibility

By using the Service, you agree to these Terms and the Privacy Policy. If you do not agree, do not upload a document or submit a question.

You must be at least 18 years old, or use the Service with the authorization and supervision of a parent or legal guardian where permitted by applicable law. The supervising adult is responsible for the minor's use of the Service.

## 3. Experimental Service

The Service accepts PDF, DOCX, and TXT files, extracts text, and uses AI systems to answer questions about that text. It normally attempts retrieval-augmented generation first and may fall back to sending more of the document text directly to a configured large language model provider.

The Service may be changed, restricted, suspended, reset, or discontinued at any time. Features may fail or behave differently during testing. No uptime, response-time, compatibility, or continued-availability commitment is provided.

## 4. Usage Limits and Cost Estimates

The hosted testing Service is currently offered free of charge. It may enforce a per-session usage budget or query limit to control third-party API costs.

- Displayed token counts and costs may be estimates.
- Cost calculations may use pricing assumptions that differ from the configured provider's actual charges.
- Failed or simulated requests may be displayed differently as the testing implementation evolves.
- Reaching a session limit may prevent additional questions.
- No paid upgrade, credit purchase, refund, or guaranteed quota is currently offered.

Limits and pricing assumptions may change without notice during testing.

## 5. User Responsibilities and Prohibited Uses

You may use the Service only for lawful testing and evaluation. You must have the right and authority to process every document you upload.

You must not:

- Upload content that is unlawful, malicious, or infringes another person's rights.
- Upload confidential third-party information without authorization.
- Upload passwords, API keys, authentication credentials, payment-card data, government identification numbers, detailed health records, or similarly sensitive information.
- Upload malware or attempt to compromise, disrupt, overload, reverse engineer, or bypass limits of the hosted Service.
- Use the Service to harass, deceive, discriminate against, or harm another person.
- Treat an AI-generated answer as a verified statement from the source document without checking the original document.

The hosted Service is intended for personal evaluation. Use of the source code, including commercial use, is governed separately by the repository's license.

## 6. Uploaded Documents and Processing Permission

You retain any rights you hold in documents and questions you submit. You grant the operator a limited permission to process that content only as reasonably necessary to provide and operate the Service, including permission to:

- Temporarily copy and store an uploaded file.
- Extract, clean, divide, and search its text.
- Send relevant excerpts, questions, prompts, and, during fallback, potentially the full extracted text to configured service providers.
- Generate and display answers.
- Produce operational metrics and debugging traces described in the Privacy Policy.

This permission ends when the content is no longer required for these purposes, subject to third-party retention practices described below and in the Privacy Policy.

## 7. File Retention

Uploaded files are copied to an application-specific temporary directory only for extraction and PDF page counting. The application deletes each temporary copy immediately after that processing succeeds or fails. It retains extracted text and an in-memory retrieval index for the active session instead of retaining the uploaded file. On startup, it removes application-created upload files older than one hour that may have survived an interrupted server process.

The footer's "Delete Data" control removes locally stored session history, feedback, and in-memory document state. Temporary uploaded-file copies have already been removed after extraction. The control cannot guarantee deletion of data already retained by third-party providers.

Because extracted text may be sent to configured LLM and observability providers, do not upload confidential or sensitive files unless you understand and accept those providers' policies.

## 8. AI Limitations and Professional Advice

AI-generated answers may be incorrect, incomplete, misleading, outdated, or unsupported by the uploaded document. The Service may:

- Misread scanned or poorly formatted documents.
- Retrieve an irrelevant or incomplete excerpt.
- Omit important clauses, tables, footnotes, or context.
- Produce fabricated statements or citations.
- Fail because of OCR errors, context limits, rate limits, unavailable models, provider errors, network failures, or resource constraints.

Always verify an answer against the original document. The Service does not provide legal, medical, financial, tax, compliance, or other professional advice and must not be used as the sole basis for consequential decisions.

## 9. Third-Party Services and International Processing

The Service may rely on a configured LLM provider, LangSmith for debugging and tracing, IP geolocation for attempted language selection, Google Forms for optional testing feedback, and hosting or infrastructure providers. Depending on the execution path, document excerpts or full extracted document text, questions, answers, and technical metadata may be transmitted to the relevant providers. Only information you enter into the external feedback form is intentionally submitted to Google Forms.

Third-party services operate under their own terms, privacy policies, security measures, locations, and retention practices. The project operator cannot guarantee their availability or independently erase data they retain unless their tools and policies allow it. Processing may occur outside your country of residence.

See the Privacy Policy for the current processing and disclosure details. Do not use the Service if you do not agree to the required third-party processing.

## 10. History, Feedback, Export, and Deletion

- Chat history is intended to be retained locally for up to 30 days.
- Feedback retention and automatic cleanup are still being tested; consult the Privacy Policy for the current status.
- Optional Google Forms responses are held under Google's and the Application operator's retention controls and are not removed by the in-app "Delete Data" control.
- The "Download Data" control in the Privacy & Data Management footer exports locally associated session data in JSON format.
- The "Delete Data" control in that footer removes supported local records and in-memory document state for the current session; third-party copies remain subject to provider controls and retention policies.

The Service does not guarantee recovery of deleted or lost data.

## 11. Intellectual Property

### Your Content

You retain your rights in uploaded documents. You are responsible for ensuring that your use and processing of those documents is authorized.

### Generated Output

Rights in AI-generated output may depend on applicable law and the configured provider's terms. The Service does not guarantee that output is original, non-infringing, or eligible for exclusive ownership.

### Source Code

These Terms govern use of the hosted Service. Use, copying, modification, distribution, and commercial use of the repository's source code are governed by the MIT License in the repository. Third-party libraries, services, and AI models remain subject to their own licenses and terms.

Project names and branding are not separately licensed except where the repository license or applicable law provides otherwise.

## 12. Feedback

If you voluntarily submit feedback, you permit the operator to use it to evaluate and improve the project. Do not include confidential or sensitive personal data in feedback. This permission does not transfer ownership of unrelated material you may mention.

## 13. Suspension and Termination

The operator may limit, suspend, or terminate access, remove locally stored data, or discontinue the Service when reasonably necessary to:

- Protect security, privacy, infrastructure, or third-party services.
- Respond to abuse, unlawful activity, or violations of these Terms.
- Enforce resource or usage limits.
- Maintain, change, or end the experimental project.

Because the Service is experimental and free, advance notice and data recovery cannot be guaranteed.

## 14. Disclaimers

The Service is provided "as is" and "as available." To the maximum extent permitted by applicable law, no warranty is made that it will be accurate, secure, uninterrupted, error-free, suitable for a particular purpose, or compatible with every document or provider.

Nothing in these Terms excludes warranties, consumer protections, or other rights that cannot legally be excluded.

## 15. Limitation of Liability

To the maximum extent permitted by applicable law, the operator is not responsible for indirect, incidental, special, consequential, or punitive loss arising from use of or inability to use the Service, reliance on AI-generated output, loss of data, or third-party services.

The Service is free and experimental. Nothing in these Terms limits liability that cannot legally be limited, including liability arising from fraud, willful misconduct, or any other category protected by applicable law.

## 16. Applicable Law and Disputes

Applicable mandatory consumer, privacy, and data-protection rights remain in effect regardless of these Terms. No specific governing jurisdiction or mandatory arbitration process is asserted by this experimental project.

Before starting a formal dispute, please contact the operator at lazar87andreea@gmail.com and provide a reasonable opportunity to address the concern. This does not restrict your right to contact a court, consumer-protection body, or data-protection authority where applicable.

## 17. Changes to These Terms

These Terms may be updated as the Service changes. The current effective date will be displayed at the top of this document. Material changes should be communicated in the Application where practical. If you do not agree to updated Terms, stop using the Service.

## 18. Severability

If a provision of these Terms is found unenforceable, the remaining provisions will continue to apply to the extent permitted by law.

## 19. Contact

**Operator:** Andreea Nistor

**Email:** lazar87andreea@gmail.com

**GitHub:** https://github.com/lazar87andreea-glitch/AI-DocuSearch

For privacy requests, also consult the Privacy Policy and the Privacy & Data Management controls in the Application footer.

---

By using AI DocuSearch, you acknowledge that you have read and understood these Terms and the Privacy Policy.