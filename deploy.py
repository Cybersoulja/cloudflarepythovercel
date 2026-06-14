#!/usr/bin/env python3
"""Deploy and manage a Cloudflare Pages site using the Python SDK.

Usage:
    # Set your credentials
    export CLOUDFLARE_API_TOKEN="your-api-token"
    export CLOUDFLARE_ACCOUNT_ID="your-account-id"

    # Deploy (uses wrangler under the hood for file upload)
    python deploy.py deploy

    # List projects
    python deploy.py list

    # Check deployment status
    python deploy.py status

    # List deployments
    python deploy.py deployments

    # Rollback to previous deployment
    python deploy.py rollback

    # Delete project
    python deploy.py delete
"""

import os
import sys
import subprocess

import cloudflare

PROJECT_NAME = "cybersoulja-portfolio"
SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")


def get_client():
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("Error: Set CLOUDFLARE_API_TOKEN environment variable")
        sys.exit(1)
    return cloudflare.Cloudflare(api_token=token)


def get_account_id():
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not account_id:
        print("Error: Set CLOUDFLARE_ACCOUNT_ID environment variable")
        sys.exit(1)
    return account_id


def deploy():
    """Deploy the site directory to Cloudflare Pages via wrangler."""
    print(f"Deploying {SITE_DIR} to Cloudflare Pages project '{PROJECT_NAME}'...")
    result = subprocess.run(
        ["npx", "wrangler", "pages", "deploy", SITE_DIR, "--project-name", PROJECT_NAME],
        check=False,
    )
    if result.returncode == 0:
        print(f"\nSite deployed! Check: https://{PROJECT_NAME}.pages.dev")
    else:
        print("\nDeploy failed. Make sure wrangler is available (npm i -g wrangler) and you're logged in (wrangler login).")
    sys.exit(result.returncode)


def list_projects():
    """List all Pages projects in the account."""
    client = get_client()
    account_id = get_account_id()
    projects = client.pages.projects.list(account_id=account_id)
    if not projects.result:
        print("No Pages projects found.")
        return
    for p in projects.result:
        url = f"https://{p.subdomain}" if hasattr(p, "subdomain") and p.subdomain else "n/a"
        print(f"  {p.name}  —  {url}")


def status():
    """Show status of the current project."""
    client = get_client()
    account_id = get_account_id()
    try:
        project = client.pages.projects.get(project_name=PROJECT_NAME, account_id=account_id)
        print(f"Project: {project.name}")
        if hasattr(project, "subdomain") and project.subdomain:
            print(f"URL:     https://{project.subdomain}")
        if project.canonical_deployment:
            d = project.canonical_deployment
            print(f"Latest:  {d.id}")
            if hasattr(d, "url") and d.url:
                print(f"Deploy:  {d.url}")
    except cloudflare.NotFoundError:
        print(f"Project '{PROJECT_NAME}' not found. Run: python deploy.py deploy")


def list_deployments():
    """List recent deployments for the project."""
    client = get_client()
    account_id = get_account_id()
    deployments = client.pages.projects.deployments.list(
        project_name=PROJECT_NAME, account_id=account_id
    )
    if not deployments.result:
        print("No deployments found.")
        return
    for d in deployments.result:
        env = getattr(d, "environment", "unknown")
        url = getattr(d, "url", "")
        created = getattr(d, "created_on", "")
        print(f"  {d.id[:12]}  {env:<12}  {created}  {url}")


def rollback():
    """Rollback to the previous production deployment."""
    client = get_client()
    account_id = get_account_id()
    deployments = client.pages.projects.deployments.list(
        project_name=PROJECT_NAME, account_id=account_id, env="production"
    )
    if not deployments.result or len(deployments.result) < 2:
        print("Not enough deployments to rollback.")
        return
    prev = deployments.result[1]
    print(f"Rolling back to deployment {prev.id[:12]}...")
    client.pages.projects.deployments.rollback(
        deployment_id=prev.id,
        project_name=PROJECT_NAME,
        account_id=account_id,
        body={},
    )
    print("Rollback triggered.")


def delete_project():
    """Delete the Pages project."""
    confirm = input(f"Delete project '{PROJECT_NAME}'? This cannot be undone. (y/N): ")
    if confirm.lower() != "y":
        print("Cancelled.")
        return
    client = get_client()
    account_id = get_account_id()
    client.pages.projects.delete(project_name=PROJECT_NAME, account_id=account_id)
    print(f"Deleted project '{PROJECT_NAME}'.")


COMMANDS = {
    "deploy": deploy,
    "list": list_projects,
    "status": status,
    "deployments": list_deployments,
    "rollback": rollback,
    "delete": delete_project,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python deploy.py <command>")
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
