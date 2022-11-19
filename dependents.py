from github import Github
import os

import ghtopdep
import filters

def per_package(repo):
    github = Github(login_or_token=os.environ.get("GH_TOKEN"))

    package_filter = list(repo["packages"])
    name = repo["name"]
    org = repo["org"]
    repo_url = "https://github.com/{0}/{1}".format(org, name)
    dependent_repos = ghtopdep.get_dependents(repo_url, True,  package_filter, 0)
    dependent_packages = ghtopdep.get_dependents(repo_url, False, package_filter, 0)

    #Fuse repos and package dependents and create dictionary out of it
    dependents_per_package = []
    for index in range(len(dependent_repos)):
        dependent_repo = dependent_repos[index]
        dependent_package = dependent_packages[index]

        dependents = {dependent['url'][19:]: {"stars": dependent['stars'], "dependent_type": "repository"} for dependent in dependent_repo["dependents"]}
        dependents.update({dependent['url'][19:]: {"stars": dependent['stars'], "dependent_type": "package"} for dependent in dependent_package["dependents"]})

        dependents_per_package.append({
            "name": dependent_repo["name"],
            "id": dependent_repo["id"],
            "dependents": dependents
        })

    # Clean up dependents
    print("Dependents which aren't forks of other dependents:")
    for package in dependents_per_package:
        dependents = {name: info for (name, info) in package["dependents"].items() if filters.filter_forks(github, name, package["dependents"])}
        print(package["name"], ": ", len(dependents), "/", len(package["dependents"]))

        package["filtered_dependents"] = dependents

    # Get commit activity of all dependencies
    for package in dependents_per_package:
        for name, info in package["filtered_dependents"].items():
            repo = github.get_repo(name)
            info["commit_activity"] = repo.get_stats_commit_activity()

    # Filter active repos
    print("Active dependents:")
    for package in dependents_per_package:
        dependents = list(filter(filters.filter_active_repos, package["filtered_dependents"].items()))
        print(package["name"], ": ", len(dependents), "/", len(package["filtered_dependents"]))

        package["active_dependents"] = dependents

    return dependents_per_package



