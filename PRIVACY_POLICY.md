# Privacy Policy

**Last updated:** June 21, 2026

SnippetVault is a self-hostable code snippet manager. This privacy policy describes how data is collected, stored, and handled when you run the software. Because SnippetVault is designed to be self-hosted, **you control the server and all data on it**. This policy covers the default behavior of the software when run as-is.

---

## 1. Data Controller

SnippetVault is open-source software. The **data controller is the person or organization that hosts the SnippetVault instance**. If you use someone else's hosted instance, their privacy policy applies. If you self-host, you are the data controller for your users' data.

---

## 2. What Data Is Collected

### 2.1 Account Data (stored locally in your database)

When a user registers or logs in, the following data is stored in the SQLite database (`snippets.db`):

| Field | Source | Purpose |
|-------|--------|---------|
| `username` | User-provided or from OAuth provider | Display name, profile URL |
| `email` | User-provided or from OAuth provider | Unique identifier, login |
| `password_hash` | User-provided (email auth only) | Authentication — **never stored in plain text** |
| `avatar_url` | From OAuth provider (optional) | Profile picture |
| `oauth_provider` | From OAuth provider | Identifies which provider was used ("google" or "github") |
| `oauth_id` | From OAuth provider | Links the account to the provider |
| `role` | From `roles.json` or default `"user"` | Authorization level |

### 2.2 Snippet Data (stored locally in your database)

All code snippets, titles, tags, and visibility settings are stored in `snippets.db`. This data is never sent to any third party by the software itself.

### 2.3 Configuration Data (stored locally)

- `data/config.json` — authentication mode and registration preference.
- `data/roles.json` — role assignments (if any).
- `data/.secret_key` — auto-generated session signing key (if not provided via env).

### 2.4 Data NOT Collected

SnippetVault **does not** collect, transmit, or store:

- IP addresses (not logged by the application; your reverse proxy may log them independently).
- Browser fingerprints or device information.
- Usage analytics, telemetry, or crash reports.
- Cookies beyond Flask session cookies (required for login; no tracking cookies).
- Any data on third-party servers.

---

## 3. How Data Is Stored

All data is stored in a **local SQLite database** (`snippets.db`) in the `data/` directory. SQLite is a file-based database — there is no separate database server. Data never leaves your server unless you explicitly transfer it.

### Security measures

- Passwords are hashed using `werkzeug.security.generate_password_hash` (PBKDF2-SHA256 with a random salt). Plain-text passwords are never stored.
- Flask session cookies are signed with `SECRET_KEY`. Without the key, session data cannot be tampered with.
- The Docker container runs as a non-root user (`snippet`, uid 1000) to limit the impact of a potential breach.

---

## 4. OAuth Authentication

When you enable OAuth (Google and/or GitHub), the following applies:

- Users are redirected to the OAuth provider's consent screen. SnippetVault does not see or store the user's password for that provider.
- The OAuth provider returns an email address, name, and (optionally) an avatar URL. These are stored as described in section 2.1.
- OAuth tokens are used only during the authentication flow and are not stored after login completes.
- Each provider's privacy policy applies to the data they collect during authentication:
  - [Google Privacy Policy](https://policies.google.com/privacy)
  - [GitHub Privacy Policy](https://docs.github.com/en/github/site-policy/github-privacy-statement)

---

## 5. Third-Party Services

SnippetVault itself does not use any third-party services. However:

- **OAuth providers** (Google, GitHub): If you enable OAuth, user interactions with those providers are subject to their privacy policies.
- **CDNs**: The default templates load Bootstrap CSS and icons from CDN (`cdn.jsdelivr.net`). This is a client-side request — your browser communicates with the CDN. You can remove CDN references and self-host these assets if desired.
- **Docker image**: The official Docker image is hosted on GitHub Container Registry (`ghcr.io`). Pulling the image is subject to GitHub's privacy policy.

---

## 6. Data Retention

Data is retained until explicitly deleted:

- **Snippets**: Deleted immediately when a user deletes them through the UI.
- **Accounts**: Deleted when the database record is removed (no automated deletion).
- **Logs**: The application does not maintain its own logs. If you use Docker, container logs may contain startup messages but no user data.
- **Backups**: Any backups you create of the `data/` directory are your responsibility.

---

## 7. User Rights

Since you (the hoster) control all data, your users should contact you directly to exercise their rights:

- **Access**: Users can view their own snippets and profile data through the application UI.
- **Correction**: Users can edit their profile information and snippets through the UI.
- **Deletion**: Users can delete individual snippets. Account deletion requires database access by the instance administrator.
- **Data portability**: The SQLite database is a single file — you can export it directly.

---

## 8. Changes to This Policy

If this file is updated, the "Last updated" date at the top changes. Since the software is self-hosted, you should review updates when you pull new versions of the code.

---

## 9. Contact

For questions about this privacy policy, open an issue on the [GitHub repository](https://github.com/vihaanvp/SnippetVault).

---

**TL;DR:** SnippetVault stores only what's needed to function (accounts, snippets). Everything lives in your SQLite database on your server. Nothing is sent to third parties. You are in full control.
