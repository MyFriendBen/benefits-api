# Deployment Setup Checklist

This document outlines the one-time setup required to enable the automated release-based deployment workflow.

## Required GitHub Secrets

The following secrets need to be configured in your GitHub repository settings:

**Location**: `https://github.com/Gary-Community-Ventures/benefits-api/settings/secrets/actions`

### Existing Secrets (verify these are set)
- ✅ `HEROKU_API_KEY` - Heroku authentication token
- ✅ `HEROKU_EMAIL` - Email associated with Heroku account
- ✅ `SLACK_WEBHOOK_URL` - Webhook for deployment notifications

### New Secrets Required
- ⚠️ `HEROKU_STAGING_APP_NAME` - Should be set to: `cobenefits-api-staging`
- ⚠️ `HEROKU_PROD_APP_NAME` - Should be set to: `cobenefits-api`
- ⚠️ `TRANSLATIONS_REPO_TOKEN` - GitHub Personal Access Token with repo permissions for `mfb-translations`

## How to Add Secrets

### Via GitHub UI

1. Go to: `https://github.com/Gary-Community-Ventures/benefits-api/settings/secrets/actions`
2. Click **"New repository secret"**
3. Enter name and value
4. Click **"Add secret"**

### Via GitHub CLI

```bash
# Set Heroku app names
gh secret set HEROKU_STAGING_APP_NAME --body "cobenefits-api-staging"
gh secret set HEROKU_PROD_APP_NAME --body "cobenefits-api"

# Set translations repo token (you'll be prompted to paste the token)
gh secret set TRANSLATIONS_REPO_TOKEN
```

### Verify All Secrets

```bash
gh secret list
```

Expected output should include all of the above secrets.

---

## Creating GitHub Personal Access Token for Translations

The `TRANSLATIONS_REPO_TOKEN` is needed to allow the workflow to push to the `mfb-translations` repository.

### Steps:

1. Go to: `https://github.com/settings/tokens/new`
2. Set **Token name**: `benefits-api-translations-sync`
3. Set **Expiration**: 1 year (or No expiration if allowed by org policy)
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click **"Generate token"**
6. **Copy the token immediately** (you won't see it again)
7. Add it as a secret:
   ```bash
   gh secret set TRANSLATIONS_REPO_TOKEN --body "<paste-token-here>"
   ```

**Note**: Store the token securely in case you need to reference it later.

---

## GitHub Branch Settings

### Change Default Branch

1. Go to: `https://github.com/Gary-Community-Ventures/benefits-api/settings/branches`
2. Under "Default branch", click the **switch icon** (↔️)
3. Select **`main`** as the new default
4. Click **"Update"** and confirm

### Branch Protection Rules

Recommended protection rules for `main`:

1. Go to: `https://github.com/Gary-Community-Ventures/benefits-api/settings/branch_protection_rules`
2. Click **"Add rule"** or edit existing rule for `main`
3. Configure:
   - ✅ Branch name pattern: `main`
   - ✅ Require a pull request before merging
   - ✅ Require approvals: 1
   - ✅ Require status checks to pass before merging
   - ✅ Require conversation resolution before merging
   - Optional: Require linear history (prevents merge commits)
   - Optional: Include administrators
4. Click **"Create"** or **"Save changes"**

---

## Verifying Heroku Configuration

Ensure Heroku apps are properly configured:

```bash
# Check staging app
heroku apps:info -a cobenefits-api-staging

# Check production app
heroku apps:info -a cobenefits-api

# Verify CLI authentication
heroku auth:whoami
```

---

## Migration Checklist

Before going live with the new deployment workflow:

### Pre-Migration
- [ ] All required GitHub secrets are configured
- [ ] Default branch changed to `main`
- [ ] Branch protection rules updated
- [ ] Team notified of upcoming changes
- [ ] Open PRs reviewed (merge or update base branch)

### Sync dev and main
```bash
cd /Users/catonhauer/Repos/benefits-api
git checkout main
git pull origin main
git merge dev
git push origin main
```

### Merge This PR
- [ ] Review deployment workflow changes
- [ ] Merge PR to `dev` (or `main` if already migrated)
- [ ] Deploy to staging to test

### First Production Release
- [ ] Test staging deployment works from `main`
- [ ] Verify all post-deployment scripts work
- [ ] Create first GitHub Release (e.g., `v1.0.0`)
- [ ] Monitor production deployment
- [ ] Verify all automated steps complete successfully

### Post-Migration
- [ ] Archive or delete `dev` branch (optional)
- [ ] Update team documentation
- [ ] Share DEPLOYMENT.md with team
- [ ] Celebrate! 🎉

---

## Troubleshooting Setup

### Secret not found error
```bash
# Verify secret exists
gh secret list | grep HEROKU_PROD_APP_NAME

# Re-add if missing
gh secret set HEROKU_PROD_APP_NAME --body "cobenefits-api"
```

### Translation sync fails
```bash
# Check if token has correct permissions
# Token needs 'repo' scope for mfb-translations repository

# Test token manually
git clone https://x-access-token:YOUR_TOKEN@github.com/Gary-Community-Ventures/mfb-translations.git /tmp/test-clone
```

### Workflow doesn't trigger
```bash
# Check workflow syntax
gh workflow list

# View workflow runs
gh run list --workflow=deploy-production.yml
```

---

## Testing the Workflows

### Test Staging Deployment
1. Create a test branch
2. Make a small change
3. Open PR against `main`
4. Merge PR
5. Watch staging deployment:
   ```bash
   gh run watch
   ```

### Test Production Deployment (Dry Run)
1. After staging deployment succeeds
2. Create a pre-release to test:
   ```bash
   gh release create v0.0.1-test \
     --title "Test Release" \
     --notes "Testing production deployment workflow" \
     --prerelease
   ```
3. Monitor the deployment
4. Delete test release after verification:
   ```bash
   gh release delete v0.0.1-test --yes
   ```

---

## Support

If you encounter issues during setup:

1. Check GitHub Actions logs: `gh run list`
2. Verify all secrets: `gh secret list`
3. Review workflow files for syntax errors
4. Check Heroku app access: `heroku apps:info -a <app-name>`
5. Post in Slack #deployments for team help

---

## Reference

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [Heroku API Authentication](https://devcenter.heroku.com/articles/authentication)
