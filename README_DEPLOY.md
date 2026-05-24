# Clayton Alpha Dashboard Deployment

This document explains how to run and deploy the public-safe version of Global_QDII_Risk_Monitor.

## Local Run

```bash
pip install -r requirements.txt
python main.py
python -m streamlit run app.py
```

Local private mode reads `config/portfolio.yaml` and may show real holding amounts.

## Public Mode

Before showing the dashboard to others or deploying it online, force public mode:

```bash
APP_MODE=public python -m streamlit run app.py
```

On Streamlit Community Cloud, the app also attempts to detect the hosted environment and default to public mode. Public mode reads `config/portfolio_public.yaml` when available.

Public mode hides:

- real holding amounts
- total asset amount
- tactical cash amount
- local file paths
- config file paths
- edit pages
- execution review records
- debug details

## Streamlit Community Cloud

1. Push the deployable files to GitHub.
2. Create a Streamlit Community Cloud app.
3. Set the main file to `app.py`.
4. Add `APP_MODE="public"` in Streamlit Cloud secrets, or set environment variable `APP_MODE=public` if your hosting layer supports environment variables.
5. Confirm the sidebar shows `当前模式：public`.
6. Open `部署健康检查` and verify all public checks pass.

## Secrets

Do not commit `.streamlit/secrets.toml`.

Recommended Streamlit secret:

```toml
APP_MODE = "public"
```

If more secrets are needed later, configure them in Streamlit Cloud's secrets manager. This project currently does not require brokerage credentials and must not store account passwords.

## Do Not Upload

Do not upload private or generated local files:

- `.env`
- `*.env`
- `.streamlit/secrets.toml`
- `data/fund_nav_cache.csv`
- `data/fund_manual_nav.csv`
- `reports/execution_review.csv`
- `config/portfolio.yaml`
- `config/dca_policy.yaml`
- `backups/`
- `*.log`
- local private screenshots or account exports

## Investment Disclaimer

This dashboard is only for research observation, risk monitoring, and DCA assistance. It is not investment advice, does not connect to brokerage accounts, and does not place trades.
