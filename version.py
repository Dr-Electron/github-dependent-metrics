import os
import re
import tomllib

regex = r'(?:\?|\&)(?:\=|\&?)((rev=)+?(?P<revison>[\w|\d]+)|(branch=)+?(?P<branch>[\w|\d]+))*(?P<commit>#(\w|\d)+){0,}'

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
    files = get_matching_files(cache, full_name, ['Cargo.toml', 'Cargo.lock'])
    versions = []
    index = 0
    while index < len(files):
        current_index = index
        index += 1

        lock_dependent = {}
        if files[current_index].path.endswith(".lock"):
            lock_file_dict = tomllib.loads(
                files[current_index].decoded_content.decode()
            )
            lock_dependent = next(
                (package for package in lock_file_dict.get('package') if package.get("name") == package_name), 
                {}
            )

        manifest_dependent = {}
        manifest_file = None
        if files[current_index].path.endswith(".toml"):
            manifest_file = files[current_index]

        if current_index+1 < len(files) and has_same_path(files[current_index].path, files[current_index+1].path):
            index += 1
            manifest_file = files[current_index+1]
        
        if manifest_file:
            manifest = tomllib.loads(manifest_file.decoded_content.decode())
            if 'dependencies' in manifest and package_name in manifest['dependencies']:
                manifest_dependent = manifest['dependencies'][package_name]

        if not manifest_dependent and not lock_dependent:
            continue

        match_dict = {}
        if lock_dependent.get('source').startswith('git'):
            match_dict = re.search(regex, lock_dependent.get('source')).groupdict() if (lock_dependent) else {}

        versions.append({
            'version': manifest_dependent.get('version'),
            'rev': manifest_dependent.get('rev'),
            'branch': manifest_dependent.get('branch'),
            'locked_version': lock_dependent.get('version'),
            'locked_rev': match_dict.get('revison'),
            'locked_branch': match_dict.get('branch'),
        })

    return versions
