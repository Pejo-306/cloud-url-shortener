# Identity Platform stack

Terraform configures [Identity Platform](https://cloud.google.com/identity-platform) email/password sign-in and a browser API key for the client SDK.

## Password policy (Cognito parity)

AWS Cognito in this repo uses a **minimum password length of 6** with no required character classes.

The Terraform resource `google_identity_platform_config` does **not** expose fine-grained password policy fields (unlike Cognito). Identity Platform’s defaults are already in the same spirit (minimum length 6, optional complexity). To tighten or verify policy explicitly, use **Google Cloud console → Identity Platform → Settings → Password policy** after apply.

If Terraform later adds full password-policy blocks to `google_identity_platform_config`, extend [`main.tf`](main.tf) here.
