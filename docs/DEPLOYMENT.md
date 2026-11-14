# Deployment

Forge 100K is deployed as a static site using the repository's GitHub Actions workflow at `.github/workflows/deploy-pages.yml`.

## One-time repository setup

1. Open repository Settings → Pages.
2. Set **Source** to **GitHub Actions**.
3. The workflow builds the repository root as a Pages artifact and deploys it.
4. Verify the deployment in Actions and confirm the environment URL before sharing the site.

The site uses the project URL:
`https://mrprashant9339-crypto.github.io/forge-100k/`

A successful CI run is not proof of a successful Pages deployment. Confirm the deployment workflow and published URL independently.
