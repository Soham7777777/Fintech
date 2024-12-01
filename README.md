## Flaskinit : Startup template to create distributable flask webapp
---

### Features:
- Custom Unix compliant CLI script, run `appcli` after installing the project, see `appcli --help` page.
- Fully installable and distributable to a package index like PyPi, so no need to do `git clone ...` the webapp just do `pip install ...`.
- Constrained with all best practices e.g. configuration as `.toml` files.

### How to use this template:
- Clone this repository, insatll requirements. Write the flask code, edit `pyproject.toml` to give more details about project and edit other information that suits your needs. Install in editable mode `pip install -e .` to test your cli.
- When its ready to deploy, build the package using `python3 -m build`. Upload the server app to public repository store like PyPi or to your private server, see `packaging.python.org` on how to implement your private package repository store.
- After uploading, install your app just like any other python package: `pip install <package-name>` or provide index-url if you are using private server: `pip install -i <url-of-private-repo-store> <package-name>`.
- After install run the cli command `appcli --help` or other command if you've customized it like `ecomserver --help`.
- It'll ask you to provide toml file as configuration at instance directory, just run the command to see the path.
- After providing configuration, you can optionally provide environment variables with a `.flaskenv` placed at CWD(copy from here). this will help to set the profile(e.g. development, deployment or testing) and provide respective configuration, also it can set host and port and other enviroment variable that your app needs.
- Finally `appcli run` to see running your app in development server provided by flask (not for deployment).
- In order to deploy the app import it in a file like `wsgi.py` and write `from app import make_app; app = make_app()`. Then packages like gunicorn can take this app variable and run in prod server.
- That's it no docker, no github just pure python!