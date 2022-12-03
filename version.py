import json
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
                        lock_file_dependent.get('source')
                    ).groupdict() if (lock_dependent) else {}
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

def get_js_lib_version(cache, full_name: str, package_name):
    files = get_matching_files(cache, full_name, 'package.json')
    versions = []
    root_lock_dependent = None
    index = 0
    while index < len(files):
        current_index = index
        index += 1

        file = files[current_index]
        split_file = file.path.split('/')

        split_file[-1] = 'package-lock.json'
        lock_file_path = '/'.join(split_file) 
        npm_lock_file = cache.get_content(full_name, lock_file_path)

        lock_dependent = {}
        if npm_lock_file:
            lock_file_dict = json.loads(
                npm_lock_file.decoded_content.decode()
            )
            dependent = lock_file_dict['dependencies'].get(package_name)
            if dependent:
                if dependent.get('version').startswith('git'):
                    regex = '(?:.(?!#).)+$'
                    lock_dependent['rev'] = re.search(regex, dependent.get('version')).group()
                    lock_dependent['branch'] = re.search(regex, dependent.get('from')).group()
                else:
                    lock_dependent['version'] = dependent.get('version')

        split_file[-1] = 'yarn.lock'
        lock_file_path = '/'.join(split_file) 
        yarn_lock_file = cache.get_content(full_name, lock_file_path)
        if yarn_lock_file:
            dependent = parse_yarn(yarn_lock_file.decoded_content.decode(), package_name)

            lock_dependent['rev'] = re.search(r'(?:#commit=)([a-z,0-9]+)', dependent['resolution']).group(1)
            lock_dependent['version'] = dependent['version']
            
        if len(split_file) == 1:
            root_lock_dependent = lock_dependent

        manifest_dependent = {}
        manifest_file = None
        if files[current_index].path.endswith("package.json"):
            manifest_file = files[current_index]
            if not npm_lock_file and not yarn_lock_file:
                lock_dependent = root_lock_dependent

        if current_index+1 < len(files) and has_same_path(files[current_index].path, files[current_index+1].path):
            index += 1
            manifest_file = files[current_index+1]
        
        if manifest_file:
            manifest = json.loads(manifest_file.decoded_content.decode())
            manifest_version = None
            manifest_branch = None
            if 'dependencies' in manifest and package_name in manifest['dependencies']:
                manifest_version = manifest['dependencies'][package_name]
            if 'devDependencies' in manifest and package_name in manifest['devDependencies']:
                manifest_version = manifest['devDependencies'][package_name]
            
            if manifest_version:
                if '/' in manifest_version:
                    manifest_branch = re.search(r'(?:#)((?:.(?!#))+$)', manifest_version).group(1)
                    manifest_version = None
                
                manifest_dependent = {
                    'version': manifest_version,
                    'branch': manifest_branch
                }    

        if not bool(manifest_dependent) and not bool(lock_dependent):
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

def parse_yarn(content, package_name):
    dependent = {}

    lines = re.finditer(r'.*\n', content)
    for line in lines:
        line = line.group(0)
        if line.startswith('"' + package_name):
            for line in lines:
                if not re.match(r'\s', line.group(0)): break
                else:
                    line = line.group(0)
                    if 'version: ' in line:
                        dependent['version'] = line.split('version: ')[1].strip()
                    if 'resolution: ' in line:
                        dependent['resolution'] = line.split('resolution: ')[1].strip()

    return dependent
