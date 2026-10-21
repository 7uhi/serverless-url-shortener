# Free Netlify address

Published October 20, 2026: **https://7uhi.netlify.app**. Team `7uhi` was verified on the Free plan with 300 available credits before publication. Project ID: `89e6d75f-526d-43b0-b1d7-9d78e24eb699`. Uploaded deploy: `6ad7fec6ad1615c99fbba7f6`. No AWS resources or permissions were changed.

Netlify serves `backend/static` and forwards `/api/*` and `/r/*` to the existing AWS API. The frontend builds displayed, copied, and recent links from the browser's current origin, so opening the app at its Netlify address produces links on that address. The Lambda API's JSON `short_url` still uses its AWS hostname; API clients should be aware of this distinction. No AWS deployment is needed for the browser flow.

## Deploy from GitHub

Repository: `https://github.com/7uhi/serverless-url-shortener`, production branch: `main`.

Connected and verified October 20, 2026. The first Git-based production deploy published commit `6c05727` as Netlify deploy `6ad800fb222abb670b111c4f`.

Link the existing `7uhi` project under **Project configuration → Developer settings → Continuous deployment → Repository**. Select GitHub and grant the Netlify GitHub App access only to this repository. Configure:

- Production branch: `main`
- Base directory: repository root (leave blank)
- Build command: none (leave blank)
- Publish directory: `backend/static` (also declared in `netlify.toml`)

After linking, Netlify deploys the public frontend files from GitHub whenever a commit is pushed to `main`. You can edit those files on GitHub or push from a local checkout. The existing production URL remains `https://7uhi.netlify.app`; the proxy rules continue forwarding link requests to AWS. This workflow does not deploy Lambda code or the SAM template. AWS backend changes still need a separate reviewed deployment.

Verify the first Git-based deploy reaches Published and shows the expected GitHub commit before considering the connection complete.

## Manual upload fallback

1. Sign in or create an account at <https://app.netlify.com/> and use the Free plan.
2. Generate the upload package:

   ```bash
   .venv/bin/python scripts/package_netlify.py
   ```

3. Use Netlify's manual deploy flow to upload `.local/small-link-netlify.zip`. It contains only `index.html`, `app.js`, `styles.css`, `_redirects`, and `_headers`. Never upload the entire repository, local database, or credentials.
4. Choose an available short project name in Netlify. Its production address will be `https://NAME.netlify.app`. Use that address rather than a deploy-preview URL for links you share.

For a Git-based deployment later, the root `netlify.toml` selects the same public directory. No build command or AWS credentials are needed.

## Verify after publication

1. Open the production Netlify address; confirm the styles and form load.
2. Create a link to `https://www.youtube.com/watch?v=MgB7Oc62MbY`. Confirm the displayed and copied link uses the Netlify hostname.
3. Open that link; confirm it redirects to the destination.
4. Refresh counts; confirm one GET adds one visit. Refreshing statistics must not add another visit.
5. Reload the app; confirm recent links still use the Netlify hostname.
6. Check an unknown code returns 404. Netlify forwards HEAD proxy requests as GET, so HEAD adds a visit on the Netlify address. Direct AWS HEAD requests still do not add a visit. Counts measure redirect requests, including previews and bots, rather than unique human visits.

`_redirects` uses status 200 for proxying, not a browser redirect to AWS. The backend's `Cache-Control: no-store` prevents caching redirect responses and statistics, which is necessary for visit counts. `_headers` also sets no-store and the existing frontend security headers for static files. Netlify's deployed handling of redirect responses and caching must be checked with the steps above.

The live smoke check verifies assets, POST creation, redirect headers, statistics, uncached repeat redirects, the observed HEAD behavior, private destination rejection, and missing codes:

```bash
.venv/bin/python scripts/smoke_test.py https://7uhi.netlify.app \
  --expected-short-url-base https://oe8duuof0f.execute-api.us-east-2.amazonaws.com \
  --head-counts-as-get
```

Each run creates one expiring link and sends two GET redirects and one HEAD. The expected visit count through Netlify is three. Run against the AWS address without either option to verify its original HEAD behavior. The browser was also checked for link creation, displaying the Netlify hostname, and the Copy link button.

The Netlify Free plan has usage limits, and proxied requests still consume AWS usage/credits. Check the selected Netlify team's plan before publishing; do not select a paid plan or upgrade. Existing AWS links continue working. Browser history is stored per origin, so links remembered on the AWS site will not automatically appear in the Netlify site's recent list.

References: [Netlify proxy rules](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/), [Netlify pricing](https://www.netlify.com/pricing/).
