# Direct Con Edison account connection

Research date: October 26, 2026. Investigation only: no account login, registration, outreach, or integration performed.

**Conclusion:** Con Edison supports an official direct connection through Green Button Connect / Share My Data. It could supply this optimizer with authorized usage and account information. However, the published process is for approved third-party companies, not a documented personal API-key feature. A strictly offline CLI with no reachable web endpoints does not fit the published integration requirements. Individual self-use approval remains unverified.

## Verified access and onboarding

Con Edison describes recurring customer-authorized access and company registration on its [provider onboarding page](https://www.coned.com/en/accounts-billing/share-energy-usage-data/become-a-third-party). Its [registration form](https://www.coned.com/en/accounts-billing/share-energy-usage-data/become-a-third-party/registration-form) asks for company name and contact details; it does not publish an individual-developer/self-use option. This does **not** establish that individuals are prohibited; it means eligibility cannot be promised from the public documentation.

The [vendor FAQ](https://www.coned.com/-/media/files/coned/documents/accountandbilling/share-my-data/faq.pdf) confirms: registration, Data Security Agreement and terms, technical registration, customer-authorization testing, and API testing. Client credentials follow technical registration. Share My Data itself has no charge; infrastructure, certificate, compliance, or agreement-related costs are not established by that statement. Active electric/gas accounts can authorize access; permissions include billing, interval consumption, and retail-customer data. History extends up to two years, subject to available records. Consent can be ongoing, date-limited, or one-time for 24 hours, and customers can revoke it. Unused authorization lapses after 365 days. Typical electric resolution is 5 or 15 minutes; historical availability is 80–90% within 24 hours, 99% within three days, and 99.8% within seven days. These are availability targets, not evidence that a recently opened account gains earlier occupants' detailed usage.

## Technical fit and account details

The linked [technical onboarding document v4.4, updated May 7, 2026](https://www.coned.com/-/media/files/coned/documents/accountandbilling/share-my-data/onboarding-doc.pdf), sections 3.1–3.6 and 5, specifies:

- All registered URLs must be reachable from Con Edison's network and support TLS 1.2+. No localhost, loopback, native-app, PKCE, or personal-app exception is documented.
- OAuth authorization-code flow uses registered redirects and client credentials. Codes expire in one minute; access tokens last one hour. Refresh tokens expire after a year of nonuse. Batch downloads notify a registered endpoint.
- Residential AMI history uses 15-minute intervals. Provisional electricity readings cover the last 24 hours with approximately 45-minute latency; they are not billing-quality readings.
- Scopes cover consumption, monthly usage summaries with costs, billing account, agreement, service location, and meter information. RetailCustomer includes account number and service address. Billing summaries include ESCO charges where applicable.
- Test onboarding precedes production approval; anticipated onboarding is 30–60 days.

**Not verified:** whether every bill line item, supplier identity, current SC1 sub-rate/rider, historical tariff changes, or switching eligibility is populated sufficiently for precise reconstruction. Scope names alone do not prove those fields exist or are complete. Inspect actual authorized API responses against bills before replacing manual inputs.

Adapter implication: the guide identifies historical quality code `17` as validated, while the current importer's conservative generic-quality policy rejects it. A future connector needs an explicit Con Edison source-specific quality policy and selection among multiple ReadingTypes; current ingestion behavior was not changed during this investigation.

## Certification, DPS registration, and self-use

The reviewed Con Edison onboarding materials require utility onboarding/testing and a Data Security Agreement; they do **not explicitly require** a separately purchased Green Button Alliance certification or blanket NY DPS registration for every API applicant. Do not present either as a verified universal prerequisite. Additional obligations may appear in the actual agreement or approval process, which has not been undertaken.

Personal self-use eligibility and any additional business-registration obligations must be confirmed with Con Edison for this specific application; the public technical documents do not resolve them.

## Practical route for this project

**Engineering assessment:** keep the existing file-import workflow usable now. A later authorized connector could fetch into local files while retaining all calculations locally, but it would need approved application credentials and reachable TLS authorization/notification endpoints under the currently documented process. This changes the original no-backend deployment constraint. Each open-source installation cannot safely reuse a client secret committed to GitHub.

Before committing to that work, the unresolved factual questions are whether Con Edison accepts an individual connecting only their own account, what agreement/security obligations apply to that applicant, and whether any approved callback arrangement avoids a continuously hosted service. There is no evidence here that supplying an account number or password to this optimizer alone enables the official connection. No outreach or registration has been initiated.

