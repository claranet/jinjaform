import os
import shutil

from jinjaform.config import env, jinjaform_root, project_root, terraform_dir


def setup():
    """
    Sets up the terraform root link, module cache and plugin cache.

    """

    os.makedirs(terraform_dir, exist_ok=True)

    # Create a .terraform/root symlink to the project root directory
    # so that Terraform code can access it using a relative path.
    root_link = os.path.join(terraform_dir, 'root')
    if os.path.exists(root_link):
        os.remove(root_link)
    os.symlink(project_root, root_link)

    # Create a shared modules directory in the root directory.
    module_link = os.path.join(terraform_dir, 'modules')
    module_cache_dir = os.path.join(jinjaform_root, 'modules')
    os.makedirs(module_cache_dir, exist_ok=True)
    if os.path.islink(module_link):
        os.remove(module_link)
    elif os.path.exists(module_link):
        shutil.rmtree(module_link)
    os.symlink(module_cache_dir, module_link)

    # Create a shared plugin cache directory in the root directory.
    plugin_cache_dir = os.path.join(jinjaform_root, 'plugins')
    os.makedirs(plugin_cache_dir, exist_ok=True)
    env['TF_PLUGIN_CACHE_DIR'] = plugin_cache_dir
