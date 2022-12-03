import os
import re
import tomllib

def has_same_path(path1, path2):
    return os.path.split(path1)[0] == os.path.split(path2)[0]

def get_matching_files(cache, full_name: str, pattern):
    files = []
    contents = list(cache.get_contents(full_name, ""))
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(list(cache.get_contents(full_name, file_content.path)))
        else:
            if pattern in file_content.path:
                files.append(file_content)

    def sort_content_files(file):
        return file.path 
    
    files.sort(key=sort_content_files)
    return files

def get_rust_lib_version(cache, full_name: str, package_name):
    files = get_matching_files(cache, full_name, 'Cargo.toml')
    versions = []
    root_lock_dependent = None
    index = 0
    while index < len(files):
        current_index = index
        index += 1

        file = files[current_index]
        split_file = file.path.split('/')

        split_file[-1] = 'Cargo.lock'
        lock_file_path = '/'.join(split_file) 
        lock_file = cache.get_content(full_name, lock_file_path)

        lock_dependent = {}
        if lock_file:
            lock_file_dict = tomllib.loads(
                lock_file.decoded_content.decode()
            )
            lock_file_dependent = next(
                (package for package in lock_file_dict.get('package') if package.get("name") == package_name), 
                {}
            )

            if bool(lock_file_dependent):
                lock_dependent['version'] = lock_file_dependent.get('version')
                if lock_file_dependent.get('source').startswith('git'):
                    match_dict = re.search(
                        r'(?:\?|\&)(?:\=|\&?)((rev=)+?(?P<rev>[\w|\d]+)|(branch=)+?(?P<branch>[\w|\d]+))#*(?P<commit>[\w|\d]+){0,}', 
                        lock_file_dependent.get('source')).groupdict() if (lock_dependent) else {}
                    lock_dependent['rev'] = match_dict['rev'] if match_dict.get('rev') else match_dict.get('commit')
                    lock_dependent['branch'] = match_dict['branch']

        if len(split_file) == 1:
            root_lock_dependent = lock_dependent

        manifest_dependent = {}
        manifest_file = None
        if files[current_index].path.endswith(".toml"):
            manifest_file = files[current_index]
            if not lock_file:
                lock_dependent = root_lock_dependent

        if current_index+1 < len(files) and has_same_path(files[current_index].path, files[current_index+1].path):
            index += 1
            manifest_file = files[current_index+1]
        
        if manifest_file:
            manifest = tomllib.loads(manifest_file.decoded_content.decode())
            if 'dependencies' in manifest and package_name in manifest['dependencies']:
                manifest_dependent = manifest['dependencies'][package_name]

        if not manifest_dependent and not lock_dependent:
            continue

        versions.append({
            'version': manifest_dependent.get('version'),
            'rev': manifest_dependent.get('rev'),
            'branch': manifest_dependent.get('branch'),
            'locked_version': lock_dependent.get('version'),
            'locked_rev': lock_dependent.get('rev'),
            'locked_branch': lock_dependent.get('branch'),
        })

    return versions
