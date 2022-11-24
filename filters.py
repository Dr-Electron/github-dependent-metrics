def filter_forks(github, dependent, dependents):
    repo = github.get_repo(dependent)
    if repo.source:
        if (repo.source.full_name in dependents) or ("iotaledger" in repo.source.full_name):
            return False
        return True
    else:
        return True

def filter_active_repos(dependent):
    commits_last_six_months = sum(stat.total for stat in dependent[1]["commit_activity"][26:])
    return commits_last_six_months > 0