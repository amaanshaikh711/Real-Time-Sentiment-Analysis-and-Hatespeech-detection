# Deploying HateSense AI to Render

This guide explains how to deploy the HateSense AI application to Render.com using the generated Docker configuration.

## Prerequisites

1.  A [Render](https://render.com) account.
2.  A [GitHub](https://github.com) account.
3.  The project pushed to a GitHub repository.

## Deployment Steps

### Method 1: using `render.yaml` (Blueprint)

This is the easiest way as it automatically configures the service.

1.  Push this code to your GitHub repository.
2.  Go to the [Render Dashboard](https://dashboard.render.com/).
3.  Click **New +** and select **Blueprint**.
4.  Connect your GitHub account and select your repository.
5.  Render will detect the `render.yaml` file.
6.  You will be prompted to enter the values for the environment variables:
    *   `SECRET_KEY` (Generate a random string)
    *   `SUPABASE_URL`
    *   `SUPABASE_KEY`
    *   `SUPABASE_SERVICE_KEY`
    *   `APIFY_TOKEN`
    *   `YOUTUBE_API_KEY`
7.  Click **Apply**. Render will start building and deploying your app.

### Method 2: Manual Setup

1.  Push this code to your GitHub repository.
2.  Go to the [Render Dashboard](https://dashboard.render.com/).
3.  Click **New +** and select **Web Service**.
4.  Connect your GitHub repository.
5.  Choose the following settings:
    *   **Name**: `hatesense-ai` (or any name you prefer)
    *   **Runtime**: `Docker`
    *   **Region**: Any
    *   **Branch**: `main` (or your default branch)
6.  **Environment Variables**:
    *   Add the environment variables listed in Method 1 manually.
7.  Click **Create Web Service**.

## Troubleshooting

*   **Build Failures**: Check the logs. If `pip` fails, ensure `requirements.txt` packages are compatible with Python 3.10.
*   **Application Errors**: Check the "Logs" tab in Render.
*   **Port**: The application listens on port `10000`. This is configured in the `Dockerfile` and `render.yaml`.

## Docker Configuration

The included `Dockerfile` performs the following:
1.  Uses `python:3.10-slim`.
2.  Installs system dependencies (`build-essential`).
3.  Installs Python dependencies from `requirements.txt`.
4.  Downloads NLTK `stopwords` data.
5.  Runs the application using `gunicorn`.
