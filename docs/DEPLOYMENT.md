# Deployment Guide

## Overview

We use a **trunk-based development** workflow with automated deployments:

- **All PRs target `main`** - No separate development branch
- **Staging deployments are automatic** - Merging to `main` → Auto-deploy to Staging
- **Production deployments use GitHub Releases** - Create a release → Auto-deploy to Production
- **All deployment steps are automated** - No manual Heroku UI clicks or CLI commands needed

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes & Commit

```bash
# Make your changes
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

### 3. Open Pull Request

```bash
# PRs target main by default
gh pr create --base main --title "Add new feature" --fill

# Or use GitHub UI
```

### 4. Review & Merge

- Get approval from team members
- Merge PR (squash, merge commit, or rebase based on team preference)
- **Automatic deployment to Staging happens immediately**

### 5. Test on Staging

```bash
# Visit staging environment
open https://cobenefits-api-staging.herokuapp.com

# Check deployment logs
gh workflow view "Deploy to Staging"
```

---

## Staging Deployments

**Trigger**: Automatically when code is merged to `main`

**What happens automatically**:
1. Code is deployed to Heroku Staging
2. Database migrations run (`python manage.py migrate`)
3. Configurations are added (`python manage.py add_config --all`)
4. Validations run (`python manage.py validate`)
5. Slack notification sent with deployment status

**Workflow file**: [`.github/workflows/deploy-staging.yml`](../.github/workflows/deploy-staging.yml)

**Monitoring**:
```bash
# View recent staging deployments
gh run list --workflow=deploy-staging.yml --limit 5

# View logs for specific deployment
gh run view <RUN_ID> --log

# Check Heroku
heroku releases -a cobenefits-api-staging
```

---

## Production Deployments

### Creating a Production Release

**When to release**: After testing changes on staging and coordinating with the team

**How to release**:

#### Via GitHub UI 

1. Go to [Releases page](https://github.com/MyFriendBen/benefits-api/releases)
2. Click **"Draft a new release"**
3. Click **"Choose a tag"** → Type new version (e.g., `v1.2.3`)
4. Click **"Create new tag: v1.2.3 on publish"**
5. Set release title: `Release v1.2.3` or descriptive name
6. Click **"Generate release notes"** (auto-generates changelog from PRs)
7. Edit notes as needed, add highlights or important changes
8. Click **"Publish release"**

### What Happens Automatically

When you publish a GitHub Release:

1. **Code deployment** - Exact code from the release tag is deployed to Heroku Production
2. **Database migrations** - `python manage.py migrate`
3. **Configuration updates** - `python manage.py add_config --all`
4. **Pull validations** - `python manage.py pull_validations` from staging
5. **Run validations** - `python manage.py validate`
6. **Sync translations** - Export from production → Save to `mfb-translations` repo → Import to staging
7. **Slack notifications** - Status updates sent to team

**Workflow file**: [`.github/workflows/deploy-production.yml`](../.github/workflows/deploy-production.yml)

### Monitoring Production Deployments

```bash
# Watch the production deployment
gh workflow view "Deploy to Production" --web

# Check workflow status
gh run list --workflow=deploy-production.yml --limit 5

# View logs
gh run view <RUN_ID> --log

# Verify on Heroku
heroku releases -a cobenefits-api
```

---

## Versioning Strategy

We use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

### Version Types

- **MAJOR** (v2.0.0): Breaking changes, API changes, major refactors
  - Example: Removing deprecated endpoints, changing response formats

- **MINOR** (v1.3.0): New features, backward-compatible additions
  - Example: New programs, new API endpoints, enhancements

- **PATCH** (v1.2.4): Bug fixes, small improvements, backward-compatible
  - Example: Fixing calculation errors, updating copy, dependency updates

### Pre-release Tags (Optional)

- `v1.3.0-rc.1` - Release candidate
- `v1.3.0-beta.1` - Beta release
- `v1.3.0-alpha.1` - Alpha release

### Choosing the Next Version

```bash
# Check current production version
gh release list --limit 1

# Examples:
# Current: v1.2.3
# Bug fix → v1.2.4
# New feature → v1.3.0
# Breaking change → v2.0.0
```

---

## Hotfix Workflow

When a critical bug is found in production:

### 1. Create Hotfix Branch

```bash
# Start from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix
```

### 2. Make the Fix

```bash
# Fix the bug
git add .
git commit -m "hotfix: fix critical bug in eligibility calculation"
git push origin hotfix/critical-bug-fix
```

### 3. Create PR and Merge

```bash
# Create PR against main
gh pr create --base main --title "Hotfix: Critical bug in eligibility calculation" --fill

# Get quick review and merge (automatically deploys to staging)
gh pr merge --squash
```

### 4. Test on Staging & Release Immediately

```bash
# Verify fix on staging
open https://cobenefits-api-staging.herokuapp.com

# Create patch release immediately
gh release create v1.2.4 \
  --title "Hotfix v1.2.4" \
  --notes "
## Hotfix
- Fixed critical bug in eligibility calculation

This is a hotfix release to address a critical issue in production.
" \
  --latest
```

---

## Rollback Procedures

If something goes wrong in production, you have multiple rollback options:

### ⚠️ Important: Database Migration Limitations

**Critical**: Heroku rollbacks only roll back application code, **NOT database migrations**.

If your deployment included database migrations:
- The migrations will remain applied even after rollback
- You may need to manually revert schema changes
- Consider the data compatibility when rolling back code
- Test rollback scenarios in staging first

**Migration conflicts cannot be resolved on Heroku** (read-only slug). All migration issues must be fixed locally:
1. Pull the latest code
2. Resolve conflicts with `python manage.py makemigrations --merge`
3. Commit and push changes
4. Deploy through normal workflow

### Option 1: Heroku Rollback (Fastest - ~30 seconds)

```bash
# View recent releases
heroku releases -a cobenefits-api

# Rollback to previous release
heroku rollback -a cobenefits-api

# Or rollback to specific version
heroku rollback v123 -a cobenefits-api
```

**Best for**: Quick rollback when no database migrations were included in the deployment.

### Option 2: Re-deploy Previous Release (Clean - ~5 minutes)

#### Via GitHub UI:
1. Go to [Releases page](https://github.com/MyFriendBen/benefits-api/releases)
2. Find the previous good release (e.g., `v1.2.2`)
3. Click **"Edit release"**
4. Check **"Set as the latest release"**
5. Click **"Update release"**
6. This triggers automatic re-deployment

#### Via CLI:
```bash
# List recent releases
gh release list --limit 5

# Mark previous release as latest
gh release edit v1.2.2 --latest
```

### Option 3: Create Revert Release (Auditable - ~10 minutes)

```bash
# Find the problematic commit
git log --oneline -10

# Create revert commit
git checkout main
git pull origin main
git revert <commit-hash>
git push origin main

# After staging deployment, create new release
gh release create v1.2.4 \
  --title "Release v1.2.4 - Revert problematic changes" \
  --notes "Reverts changes from v1.2.3 due to production issues" \
  --latest
```

---

## Troubleshooting

### Staging Didn't Deploy After Merging

```bash
# Check workflow run status
gh run list --workflow=deploy-staging.yml --limit 3

# View logs for failed run
gh run view <RUN_ID> --log
```

**Common issues**:
- Heroku API key expired
- Migration conflicts
- Syntax errors in code
- Tests failing in CI

### Production Deployment Failed

```bash
# Check production workflow
gh run list --workflow=deploy-production.yml --limit 3
gh run view <RUN_ID> --log

# Quick rollback while investigating
heroku rollback -a cobenefits-api
```

### Migration Conflicts

Migration conflicts **cannot** be resolved on Heroku (read-only slug). You must fix locally:

```bash
# Fix locally
git checkout main
python manage.py makemigrations --merge
git add .
git commit -m "fix: resolve migration conflicts"
git push origin main

# Wait for staging deployment to complete and verify

# Create new patch release
gh release create v1.2.4 --generate-notes --latest
```

### Check Deployment Status

```bash
# Staging status
heroku ps -a cobenefits-api-staging
heroku logs --tail -a cobenefits-api-staging

# Production status
heroku ps -a cobenefits-api
heroku logs --tail -a cobenefits-api

# GitHub Actions status
gh run list --limit 10
```

### Verifying Heroku Configuration

```bash
# Check staging app info
heroku apps:info -a cobenefits-api-staging

# Check production app info
heroku apps:info -a cobenefits-api

# Verify CLI authentication
heroku auth:whoami
```

### Translation Sync Issues

```bash
# Check if token has correct permissions
# Token needs 'repo' scope for mfb-translations repository

# Test token manually
git clone https://x-access-token:YOUR_TOKEN@github.com/Gary-Community-Ventures/mfb-translations.git /tmp/test-clone
```

### Workflow Doesn't Trigger

```bash
# Check workflow syntax
gh workflow list

# View workflow runs
gh run list --workflow=deploy-production.yml

# Re-run failed workflow
gh run rerun <RUN_ID>
```

---

## Required GitHub Secrets

These secrets are configured in the repository settings and used by the deployment workflows:

**Location**: `https://github.com/MyFriendBen/benefits-api/settings/secrets/actions`

### Current Secrets
- `HEROKU_API_KEY` - Heroku authentication token
- `HEROKU_STAGING_APP_NAME` - Set to `cobenefits-api-staging`
- `HEROKU_PROD_APP_NAME` - Set to `cobenefits-api`
- `HEROKU_STAGING_URL` - Set to `https://cobenefits-api-staging.herokuapp.com`
- `HEROKU_EMAIL` - Email associated with Heroku account
- `SLACK_WEBHOOK_URL` - Webhook for deployment notifications
- `TRANSLATIONS_REPO_TOKEN` - GitHub Personal Access Token with repo permissions for `mfb-translations`
- `VALIDATION_SHEET_ID` - Google Sheets ID for validation results (e.g., `1JRsCKm9KeeatVoW3wjsT2YqSy63js53Ib3vivK5NFYY`)

### Verifying Secrets

```bash
# List all secrets
gh secret list

# Add a new secret (if needed)
gh secret set SECRET_NAME --body "secret-value"
```

### Creating GitHub Personal Access Token for Translations

If you need to regenerate the `TRANSLATIONS_REPO_TOKEN`:

1. Go to: `https://github.com/settings/tokens/new`
2. Set **Token name**: `benefits-api-translations-sync`
3. Set **Expiration**: **Minimum 1 year** (recommended for production automation)
   - Shorter expirations require more frequent rotation
   - Set calendar reminder 2 weeks before expiration
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - Required for both read and write access to `mfb-translations` repository
5. Click **"Generate token"**
6. Copy the token immediately (you won't see it again)
7. **Store securely**: Save token in your team's password manager
8. Add it as a secret:
   ```bash
   gh secret set TRANSLATIONS_REPO_TOKEN --body "<paste-token-here>"
   ```

### Token Lifecycle & Rotation

**Expiration Impact:**
- Production deployments will fail if `TRANSLATIONS_REPO_TOKEN` expires
- Translation sync step will error, but deployment will still complete
- Set up monitoring/alerts for token expiration

**Rotation Schedule:**
- Review token annually (or per org security policy)
- Rotate immediately if:
  - Token may have been compromised
  - Team member with access leaves
  - Security audit requires it

**Rotation Process:**
1. Generate new token with same scopes
2. Update GitHub secret with new token
3. Test with a production deployment
4. Delete old token from GitHub
5. Update team password manager

---

## Deployment Checklist

### Before Merging to Main (Staging)
- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] No merge conflicts
- [ ] Migration files reviewed (if any)
- [ ] Dependencies updated (if needed)

### Before Creating Release (Production)
- [ ] All changes tested on staging
- [ ] Team notified of upcoming release
- [ ] Frontend coordinated (if applicable)
- [ ] Release notes prepared
- [ ] Correct semantic version chosen
- [ ] Database migration plan reviewed (if needed)
- [ ] Rollback plan ready

### After Production Deployment
- [ ] Verify app is running: `heroku ps -a cobenefits-api`
- [ ] Check for errors: `heroku logs --tail -a cobenefits-api`
- [ ] Test critical user flows
- [ ] Verify in Sentry/monitoring tools
- [ ] Notify team of successful deployment

---

## Workflow Comparison

| Action | Command/Steps |
|--------|---------------|
| **Deploy to Staging** | Merge PR to `main` (automatic) |
| **Deploy to Production** | Create GitHub Release |
| **Rollback Production** | `heroku rollback -a cobenefits-api` |
| **Check Staging Logs** | `gh run list --workflow=deploy-staging.yml` |
| **Check Production Logs** | `gh run list --workflow=deploy-production.yml` |
| **View Current Version** | `gh release list --limit 1` |

---

## Additional Resources

- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Semantic Versioning](https://semver.org/)
- [Heroku Release Phase](https://devcenter.heroku.com/articles/release-phase)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Heroku CLI Commands](https://devcenter.heroku.com/articles/heroku-cli-commands)

---

## Getting Help

- **GitHub Actions logs**: `gh run list`
- **Heroku logs**: `heroku logs --tail -a cobenefits-api`
- **Team discussion**: Post in Slack #deployments channel
- **File issue**: `gh issue create`
