# Single sign-on

Enterprise accounts can require single sign-on through any SAML 2.0 identity provider, such as Okta, Microsoft Entra ID or Google Workspace. Configure it from Settings, Security, Single sign-on by uploading the provider's metadata file.

Once SSO is enforced, members can no longer log in with a password. New members are created automatically on their first login (just-in-time provisioning) and removed when the identity provider deprovisions them.

Keep at least one owner able to log in without SSO as a recovery account, in case the identity provider is unavailable.
