#!/usr/bin/env python3
"""
Todoist API Client for Flomo GTD Processor

Simple client for creating tasks and projects in Todoist.

Usage:
    python todoist_client.py add-task --content "Task title" --description "Details"
    python todoist_client.py add-project --name "Project name"
    python todoist_client.py list-projects
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


class TodoistClient:
    """Simple Todoist REST API client."""

    BASE_URL = "https://api.todoist.com/rest/v2"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get("TODOIST_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Todoist API token required. Set TODOIST_API_TOKEN environment variable "
                "or pass api_token parameter."
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, data: Optional[dict] = None):
        """Make API request."""
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(
            method,
            url,
            headers=self.headers,
            json=data if data else None,
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        return

    def get_projects(self) -> list[dict]:
        """Get all projects."""
        return self._request("GET", "projects")

    def create_project(self, name: str, parent_id: Optional[str] = None) -> dict:
        """Create a new project."""
        data = {"name": name}
        if parent_id:
            data["parent_id"] = parent_id
        return self._request("POST", "projects", data)

    def get_project_by_name(self, name: str) -> Optional[dict]:
        """Find project by name."""
        projects = self.get_projects()
        for project in projects:
            if project["name"].lower() == name.lower():
                return project
        return None

    def create_task(
        self,
        content: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        priority: int = 1,
        due_string: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Create a new task."""
        data = {
            "content": content,
            "priority": priority,
        }

        if description:
            data["description"] = description

        if project_id:
            data["project_id"] = project_id
        elif project_name:
            project = self.get_project_by_name(project_name)
            if project:
                data["project_id"] = project["id"]

        if due_string:
            data["due_string"] = due_string

        if labels:
            data["labels"] = labels

        return self._request("POST", "tasks", data)

    def get_tasks(self, project_id: Optional[str] = None) -> list[dict]:
        """Get tasks, optionally filtered by project."""
        endpoint = "tasks"
        if project_id:
            endpoint = f"tasks?project_id={project_id}"
        return self._request("GET", endpoint)


def main():
    parser = argparse.ArgumentParser(description="Todoist API Client")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add-task command
    task_parser = subparsers.add_parser("add-task", help="Create a new task")
    task_parser.add_argument("--content", "-c", required=True, help="Task content/title")
    task_parser.add_argument("--description", "-d", help="Task description")
    task_parser.add_argument("--project", "-p", help="Project name")
    task_parser.add_argument("--project-id", help="Project ID")
    task_parser.add_argument("--priority", type=int, default=1, choices=[1, 2, 3, 4],
                            help="Priority (1=normal, 4=urgent)")
    task_parser.add_argument("--due", help="Due date string (e.g., 'tomorrow', 'next monday')")
    task_parser.add_argument("--labels", nargs="+", help="Labels to add")

    # add-project command
    project_parser = subparsers.add_parser("add-project", help="Create a new project")
    project_parser.add_argument("--name", "-n", required=True, help="Project name")
    project_parser.add_argument("--parent-id", help="Parent project ID")

    # list-projects command
    subparsers.add_parser("list-projects", help="List all projects")

    # list-tasks command
    tasks_parser = subparsers.add_parser("list-tasks", help="List tasks")
    tasks_parser.add_argument("--project", "-p", help="Filter by project name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        client = TodoistClient()

        if args.command == "add-task":
            result = client.create_task(
                content=args.content,
                description=args.description,
                project_name=args.project,
                project_id=args.project_id,
                priority=args.priority,
                due_string=args.due,
                labels=args.labels,
            )
            print(json.dumps(result, indent=2))
            print(f"\nTask created: {result.get('url', 'N/A')}", file=sys.stderr)

        elif args.command == "add-project":
            result = client.create_project(
                name=args.name,
                parent_id=args.parent_id,
            )
            print(json.dumps(result, indent=2))
            print(f"\nProject created: {result.get('name')}", file=sys.stderr)

        elif args.command == "list-projects":
            projects = client.get_projects()
            print(json.dumps(projects, indent=2))
            print(f"\nTotal projects: {len(projects)}", file=sys.stderr)

        elif args.command == "list-tasks":
            project_id = None
            if args.project:
                project = client.get_project_by_name(args.project)
                if project:
                    project_id = project["id"]
            tasks = client.get_tasks(project_id)
            print(json.dumps(tasks, indent=2))
            print(f"\nTotal tasks: {len(tasks)}", file=sys.stderr)

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"API error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text if e.response else 'N/A'}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
