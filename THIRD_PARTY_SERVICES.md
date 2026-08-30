# Third-Party Services Used by AI DocuSearch

**Last updated:** August 30, 2026

AI DocuSearch relies on external services for language-model responses, optional diagnostics,
language detection, feedback collection, and hosting. The service used in a particular deployment
depends on the operator's configuration and the feature you choose to use.

Do not upload confidential, regulated, or sensitive documents to a testing deployment unless you
are authorized to share the content with the applicable providers.

## Language Model Provider

AI DocuSearch sends your question, document metadata, and either relevant document excerpts or the
full extracted document text to the configured OpenAI-compatible language-model provider. This is
required to generate an answer.

The provider may be OpenAI, xAI, Groq, or another compatible service selected by the application
operator. Its own privacy, security, retention, and international-transfer terms apply. The active
provider is not currently identified in the user interface, so contact the application operator
before using the service if you need provider-specific information.

## LangSmith

When tracing is enabled by the application operator, LangSmith may receive questions, prompts,
document excerpts or extracted text included in prompts, generated answers, timing and token
metadata, errors, and Helpful/Not helpful ratings associated with a trace.

LangSmith is used for debugging and evaluating application behavior. Users cannot disable tracing
from the interface. Do not use the application if you do not consent to this processing while
tracing is enabled.

- Provider: LangChain, Inc.
- Privacy information: https://www.langchain.com/privacy-policy

## Google Forms

The **Share feedback** button opens an optional Google Form in a new tab. AI DocuSearch does not
automatically send your document, questions, answers, or session identifier to that form. Google
receives the responses you enter and may collect additional technical information under its own
policies.

Do not include document content, confidential information, or unnecessary personal data in the
form. Google Forms responses are not included in the in-app data export and cannot be removed with
the in-app **Delete Data** control.

- Provider: Google LLC
- Privacy information: https://policies.google.com/privacy

## IP Geolocation

AI DocuSearch may contact `ip-api.com` from the application server to infer a country for automatic
language selection. Depending on the hosting environment, the service may receive the server's IP
address rather than the individual user's address. Detection may be unavailable and the application
then defaults to English.

- Provider: ip-api.com
- Privacy information: https://ip-api.com/docs/legal

## Hosting and Infrastructure

The deployed application and its temporary session data are processed by the hosting provider,
such as Streamlit Community Cloud and its infrastructure providers. Hosting logs and operational
metadata are governed by the provider's terms and privacy practices.

- Streamlit privacy information: https://streamlit.io/privacy-policy

## Your Choices

- Using the AI question feature requires sending relevant content to the configured model provider.
- Opening and submitting the Google feedback form is optional.
- LangSmith tracing and IP geolocation are controlled by deployment configuration, not by an
  in-app user setting.
- The application does not sell your data or share it with advertisers.
- See the Privacy Policy for retention, deletion, and data-rights information.

Questions about the active providers or deletion of provider-held data should be directed to the
application operator.
