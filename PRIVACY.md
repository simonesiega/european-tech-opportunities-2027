# Privacy Notice

[← Project README](README.md) · [Documentation hub](docs/README.md) · [Website guide](docs/guides/user-guide/website.md) · [Security policy](SECURITY.md)

Effective: September 24, 2026

This notice explains how the European Tech Opportunities 2027 website handles visitor information. It applies to the public directory at [opportunities2027.simonesiega.com](https://opportunities2027.simonesiega.com/) and its CSV and JSON download routes.

## Controller and contact

For processing controlled by this project, the data controller is **Simone Siega**, the project maintainer and website operator. For privacy questions or requests, email [simonesiega1@gmail.com](mailto:simonesiega1@gmail.com) with the subject `[PRIVACY] Brief request summary`.

Cloudflare, Umami, GitHub, and external websites may control some processing for their own purposes under their respective privacy terms.

## Information the project publishes

The directory publishes public job-listing metadata: LinkedIn job ID, company, title, location, canonical listing URL, technology category, industries, employment type, start date, and first-seen time. It also displays the latest successful collection time. The downloadable CSV and JSON use a smaller field set that excludes timestamps. The opportunity dataset does not publish visitor information.

The website does not provide accounts, application forms, résumé uploads, saved profiles, or a mutation API. Applications take place on third-party websites.

## Processing, purposes, and legal bases

The project limits visitor-data handling to what is needed to operate and understand the service. Depending on the circumstances and applicable law, project-controlled processing relies on the following bases:

| Processing | Purpose | Basis used by the project |
|---|---|---|
| Website delivery, reliability, and security | Serve requests, prevent abuse, diagnose failures, and protect the service | Legitimate interests in operating a secure, reliable public website |
| Aggregate usage analytics | Understand use of the directory and maintain it | Legitimate interests in privacy-conscious service measurement, where permitted |
| Local theme preference | Remember the visitor's chosen theme | No project-controlled personal-data processing; the value remains on the visitor's device and provides the requested preference |
| Privacy correspondence | Answer requests and keep any necessary record of the response | Compliance with applicable legal obligations and legitimate interests in handling and documenting requests |

These bases describe the project's current operation and may be limited or supplemented by local law.

### Hosting and security

The production site uses Cloudflare in front of the application. As with ordinary web delivery, Cloudflare and the hosting infrastructure may process request information such as IP address, requested URL, timestamp, browser or user-agent information, and security or routing data to deliver and protect the service.

See [Cloudflare's Privacy Policy](https://www.cloudflare.com/privacypolicy/) for its processing and retention terms.

### Privacy-focused analytics

The canonical production site loads Umami Cloud analytics only on the production domain. Umami reports aggregate usage such as page views, referrer URLs, browser, operating system, device type, and country of origin. The project uses these metrics to understand directory usage and maintain the service.

The project does not configure advertising or cross-site tracking. According to Umami's documentation, its tracker uses no cookies, stores no personally identifiable information, anonymizes collected data, and does not track visitors across websites. Analytics processing is subject to [Umami's Privacy Policy](https://umami.is/privacy) and [analytics FAQ](https://docs.umami.is/docs/faq).

Browser or network privacy tools may prevent the analytics script from loading without preventing normal directory use.

### Local browser preference

The site uses browser local storage under the key `opportunities-theme` to remember a light or dark theme choice; without a saved choice, it follows the system preference. A saved value remains on the device until the browser or user removes it. It is not sent to the project, used for advertising, or included in project state.

## Service providers, recipients, and transfers

Cloudflare provides edge delivery and security services, while Umami provides hosted aggregate analytics. They process information needed to provide those services and may also process information for purposes described in their own privacy notices. The hosting infrastructure necessarily receives ordinary web requests.

These providers may process information outside the visitor's country or the European Economic Area, depending on their infrastructure and service configuration. International transfers are governed by the providers' applicable transfer mechanisms and privacy terms.

CSV and JSON downloads are served by the project and contain only the documented public listing fields. Following a LinkedIn, GitHub, maintainer, or other external link sends a request to that third party, whose privacy terms then apply.

Listing suggestions and issue reports are submitted through GitHub. Information posted in a public GitHub issue is public; do not include credentials, private HTML, database contents, or unnecessary personal information. GitHub handles account and request information under its own [Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

## Retention

The project does not retain account, application, résumé, or profile data because the website does not collect it. The local theme preference remains until it is cleared in the browser.

Infrastructure request data and analytics records are retained according to the applicable service configuration and provider terms, and should be kept no longer than needed for security, reliability, and aggregate service measurement. Privacy correspondence is retained only as long as needed to answer the request, meet applicable obligations, and maintain a necessary record of the response. No fixed period is stated where the project does not control or cannot accurately determine it.

## Your choices and rights

You can block the analytics script with browser or network privacy controls without preventing normal directory use, clear the theme preference through browser storage controls, and avoid posting personal information in public issues.

Subject to applicable law, you may request access to, correction of, or deletion of personal data associated with you, and may have rights to restrict or object to processing and to data portability where relevant. You may also lodge a complaint with the competent data-protection supervisory authority. In Italy, this is the [Garante per la protezione dei dati personali](https://www.garanteprivacy.it/); visitors elsewhere may contact their local authority.

Anonymous or aggregate analytics may not be reasonably linkable to an individual, which can limit the project's ability to identify, access, correct, or delete a particular visitor's data. Provider-controlled data may require a request to the relevant provider.

Send requests to the privacy contact above. Do not send credentials, cookies, or identity documents unless they are specifically and securely requested.

## Changes to this notice

Material changes will update the effective date above and be committed to the public repository. The current repository version is authoritative.
