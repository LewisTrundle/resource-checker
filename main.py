import os
import subprocess
import requests
from glob import glob
from bs4 import BeautifulSoup

from config.settings import SYSTEM_PLATFORM, RESOURCES, STANDARD_INSTALL_DIRS


# Log the environment variables that are important
def log_environment_variables():
    """Log environment variables."""
    env_vars = {
        "PATH": os.environ.get("PATH", "Not Set"),
        "JAVA_HOME": os.environ.get("JAVA_HOME", "Not Set"),
        "PYTHON_HOME": os.environ.get("PYTHON_HOME", "Not Set"),
    }
    return env_vars


def is_executable(file_path):
    """Check if a file is executable."""
    if SYSTEM_PLATFORM == "Windows":
        return os.path.isfile(file_path) and file_path.endswith(('.exe', '.cmd', '.bat'))
    else:
        return os.access(file_path, os.X_OK)
    

def run_command(cmd):
    """Run a shell command and return its output as a list of lines."""
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True).strip()
        return output.splitlines()
    except subprocess.CalledProcessError:
        return []
    

def search_in_standard_dirs(resource):
    """Search for the resource in standard installation directories."""
    matches = []
    for dir_pattern in STANDARD_INSTALL_DIRS:
        for path in glob(os.path.join(dir_pattern, "**", resource), recursive=True):
            if os.access(path, os.X_OK):  # Check if it's executable
                matches.append(path)
    return matches


def list_uncovered_path_dirs(covered_dirs):
    """List directories in PATH that were not scanned."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    uncovered_dirs = [d for d in path_dirs if d and d not in covered_dirs]
    return uncovered_dirs


def find_executable_paths(command):
    """Find all paths to a given command."""
    if SYSTEM_PLATFORM == "Windows":
        cmd = f"where {command}"
    else:
        cmd = f"which -a {command}"
    return run_command(cmd)


def get_version(command, version_args="--version"):
    """Get the version of a given path."""
    try:
        output = subprocess.check_output(
            [command] + [version_args], stderr=subprocess.STDOUT, text=True
        ).strip()
        return output.splitlines()[0]  # First line often contains the version
    except Exception as e:
        return f"Error: {e}"
    

def get_latest_version(url):
    """Fetch the latest version of a resource from its official website."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            if "nodejs" in url:
                response = requests.get("https://nodejs.org/dist/index.json")
                response_data = response.json()[0]
                version = response_data.get('version', 'Unknown version')
                date = response_data.get('date', 'Unknown version')
                return f"{version} ({date})"
            if "python" in url:
                # Python example: looks for the latest version on the Python homepage
                start = response.text.find('<span class="release-number">') + len('<span class="release-number">')
                soup = BeautifulSoup(response.text, 'html.parser')
                #print(soup)
                end = response.text.find('</span>', start)
                return response.text[start:end].strip()
            if "npmjs" in url:
                response = requests.get("https://registry.npmjs.org/npm/latest")
                return response.json().get('version', 'Unknown version')
            return "Latest version info not found"
        else:
            return f"Failed to fetch version from {url}"
    except requests.RequestException as e:
        return f"Error fetching data: {e}"
    


def get_path_details(path, version_args):
    executable = is_executable(path)
    version = get_version(path, version_args) if executable else None
    return (executable, version)


def get_resources(search_standard_dirs=False):
    resource_results = {}
    covered_dirs = set()

    for resource, details in RESOURCES.items():
        version_args, url = details
        lv = get_latest_version(url)
        paths = find_executable_paths(resource)
        extra_paths = []
        if search_standard_dirs: 
            extra_paths = search_in_standard_dirs(resource)
        resource_results[resource] = {'online_details': {'latest_version': lv, 'url': url}, 'paths': {}}

        for path in paths:
            executable, version = get_path_details(path, version_args)
            resource_results[resource]['paths'][path] = {"Executable": executable, "Version": version, "InPath": True}
        for path in extra_paths:
            executable, version = get_path_details(path, version_args)
            resource_results[resource]['paths'][path] = {"Executable": executable, "Version": version, "InPath": False}
            covered_dirs.update(os.path.dirname(path))

    return resource_results, covered_dirs



def print_hierarchy(report, current, path_counts, indent=2):
    """
    Recursively prints a hierarchy of directories and the number of paths at each level.

    :param report: List to append hierarchy lines.
    :param current: Current level of the hierarchy.
    :param path_counts: Dictionary mapping directory paths to their respective counts.
    :param indent: Current indentation level.
    """
    for key, subdir in sorted(current.items()):
        path = "\\".join([key] + list(subdir.keys()))
        count = path_counts.get(path, 0)
        report.append(f"{' ' * indent}{key} ({count})\\")
        print_hierarchy(report, subdir, path_counts, indent + 2)


def build_path_counts(resource_results):
    """
    Build a dictionary of path counts for each directory level.

    :param resource_results: The resources and their respective paths.
    :return: Dictionary with path counts for each directory.
    """
    path_counts = {}
    for resource_details in resource_results.values():
        for path in resource_details['paths']:
            parts = path.split("\\")
            for i in range(1, len(parts) + 1):
                sub_path = "\\".join(parts[:i])
                path_counts[sub_path] = path_counts.get(sub_path, 0) + 1
    return path_counts


def generate_report(resource_results, covered_dirs):
    report = []
    path_counts = build_path_counts(resource_results)

    for resource, resource_details in resource_results.items():
        report.append(f"{resource}: {'No paths found' if len(resource_details['paths']) == 0 else ''}")
        report.append(f"\tLatest Available Version: {resource_details['online_details']['latest_version']}  -  {resource_details['online_details']['url']}")
        hierarchy = {}
        for path, details in resource_details['paths'].items():
            if details['Executable'] == True:
                report.append(f"\tPath: {path}")
                report.append(f"\t\t\tExecutable: {details['Executable']}")
                report.append(f"\t\t\tVersion: {details['Version']}")
                report.append(f"\t\t\tIn-Path Variable: {details['InPath']}")
            if details['InPath'] == False:
                parts = path.split('\\')
                current = hierarchy
                for part in parts:
                    current = current.setdefault(part, {})

        print_hierarchy(report, hierarchy, path_counts)
        report.append("")

    uncovered_dirs = list_uncovered_path_dirs(covered_dirs)
    if uncovered_dirs:
        report.append("Uncovered PATH Directories:")
        report.extend(f"  {d}" for d in uncovered_dirs)
    report.append("")

    env_vars = log_environment_variables()
    report.append("Environment Variables:")
    for var, value in env_vars.items():
        report.append(f"  {var}: {value}")
 
    return report


def prompt_for_update(resource_name):
    """Prompt the user for automatic update based on the resource."""
    update = input(f"Would you like to update {resource_name}? (y/n): ")
    if update.lower() == 'y':
        if resource_name.lower() == "node":
            subprocess.run(["npm", "install", "-g", "npm"], check=True)
        elif resource_name.lower() == "python":
            subprocess.run(["python", "-m", "pip", "install", "--upgrade", "pip"], check=True)
        elif resource_name.lower() == "git":
            subprocess.run(["git", "self-update"], check=True)
        elif resource_name.lower() == "npm":
            subprocess.run(["npm", "install", "-g", "npm"], check=True)
        print(f"{resource_name} has been updated successfully.")
    else:
        print(f"{resource_name} update skipped.")
    

def save_report(report, filename="resource_report.txt"):
    """Save the report to a file."""
    report_path = os.path.join(os.getcwd(), filename)
    with open(report_path, "w") as f:
        f.write("\n".join(report))
    return report_path


def main():
    resource_results, covered_dirs = get_resources()
    report = generate_report(resource_results, covered_dirs)
    report_path = save_report(report)
    print(f"Report generated: {report_path}")

    # Ask user if they want to update each resource
    #for resource in RESOURCES.keys():
        #prompt_for_update(resource)


if __name__ == "__main__":
    main()