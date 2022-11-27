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

        repo = self.get_repo(full_name)
        self._uncached_calls += 1
        commit_activity = repo.get_stats_commit_activity()
        self.cache[full_name] = {
            **self.cache[full_name],
            "commit_activity": commit_activity
        }
        return commit_activity

    def get_contents(self, full_name: str, path: str):
        if full_name in self.cache:
            if "contents" in self.cache[full_name]:
                if path in self.cache[full_name]["contents"]:
                    self._cached_calls += 1
                    return self.cache[full_name]["contents"][path]
                repo = self.get_repo(full_name)
                self._uncached_calls += 1
                contents = repo.get_contents(path)
                self.cache[full_name]["contents"] = {
                    **self.cache[full_name]["contents"],
                    path: contents
                }
                return contents
        
        repo = self.get_repo(full_name)
        self._uncached_calls += 1
        contents = repo.get_contents(path)
        self.cache[full_name] = {
            **self.cache[full_name],
            "contents": {path: contents}
        }

        return contents

    @property
    def uncached_calls(self):
        return self._uncached_calls

    @property
    def cached_calls(self):
        return self._cached_calls