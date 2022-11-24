from github import Github

class GithubAPI:
    def __init__(self, login_or_token):
        self.github = Github(login_or_token=login_or_token)
        self.cache = {}
        self._uncached_calls = self._cached_calls = 0

    def get_repo(self, full_name: str):
        if full_name in self.cache:
            if "repo" in self.cache[full_name]:
                self._cached_calls += 1
                return self.cache[full_name]["repo"]
        
        self._uncached_calls += 1
        repo = self.github.get_repo(full_name)
        self.cache[full_name] = {
            "repo": repo
        }
        return repo

    def get_stats_commit_activity(self, full_name: str):
        if full_name in self.cache:
            if "commit_activity" in self.cache[full_name]:
                self._cached_calls += 1
                return self.cache[full_name]["commit_activity"]
            else:
                self._uncached_calls += 1
                repo = self.get_repo(full_name)
                commit_activity = repo.get_stats_commit_activity()
                self.cache[full_name]["commit_activity"] = commit_activity
                return commit_activity
        
        self._uncached_calls += 1
        repo = self.get_repo(full_name)
        commit_activity = repo.get_stats_commit_activity()
        self.cache[full_name] = {
            "commit_activity": commit_activity
        }
        return commit_activity

    @property
    def uncached_calls(self):
        return self._uncached_calls

    @property
    def cached_calls(self):
        return self._cached_calls