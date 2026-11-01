# Security Policy

## Supported versions

The project publishes one tag for each week of the program. Only the latest
week tag receives security fixes.

| Version | Supported |
|---|---|
| Latest week tag (currently `week-3`) | Yes |
| Older week tags | No |
| Untagged commits and feature branches | No |

The CHANGELOG lists the releases.

## How to report a vulnerability

Do not open a public issue for a security problem. Send an email to
**awun8191@gmail.com** with these details:

- The version or the commit that shows the problem.
- The steps that reproduce it.
- The effect that an attacker can cause.
- Any proof of concept, sent as an attachment.

You can expect an answer within 72 hours. The maintainer will confirm the
problem, agree on a fix plan with you, and credit you in the release notes when
you agree to it.

## What not to report publicly

Keep these items out of a public issue, a pull request, a discussion, or a chat:

- The steps that exploit a vulnerability.
- A proof of concept or an exploit script.
- Access tokens, passwords, `SECRET_KEY` values, or database connection strings.
- Personal data of any user of a deployment.
- A database dump or a log file with real traffic.
- The address of a deployment that shows the problem.

Send these items by email only. If you already opened a public issue by
mistake, delete the sensitive part and tell the maintainer at once.

## Scope

This policy covers the code in this repository. It does not cover a deployment
that a third party operates. Report a problem in such a deployment to its
operator.
