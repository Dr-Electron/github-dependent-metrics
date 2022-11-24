def filter_forks(github_cache, dependent, dependents):
    try:
        repo = github_cache.get_repo(dependent)
    except Exception: 
        return False
    if repo.source:
        if (repo.source.full_name in dependents) or ("iotaledger" in repo.source.full_name):
            return False
        return True
    else:
        return True

def filter_active_repos(dependent):
    commits_last_six_months = sum(stat.total for stat in dependent[1]["commit_activity"][26:])
    return commits_last_six_months > 0