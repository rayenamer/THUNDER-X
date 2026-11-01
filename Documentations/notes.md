
notes

edge case failute

The XPath was right: it matched exactly the element Laya picked. That element just can't be hovered, because it has no visible box on the page. browser-use's hover() scrolls to the element, asks for its box, gets none, and stops with "Element is not visible or has no bounding box".


One limit: a past session shows each step's latest run. Older runs are in LogsDb (and in GET /logs/sessions/{id}), but there's no way to browse them in the UI yet.

when direct matcher fails -> pipeline fails , incorrect

hover fails -> incorrect , it finds elemnts but if element have no visible box , it fails

The program that runs the notebook is the environment's own jupyter, so the Python, the packages and the kernel are all the lab's by construction. There's no list to search and no cache to refresh.

Why VS Code didn't find it: VS Code doesn't run your environments' Jupyter. It looks for environments and kernels itself, through its Python and Jupyter extensions, and that search has limits:
- it looks in usual places: the workspace's root .venv, conda, pyenv, and a few others. labs/.venv is one folder deep, so it may never get scanned;
- the first environment was labs/.lab, a hidden folder with an unusual name, which it skips;
- it caches what it found, so a kernel registered after VS Code started often doesn't show up until a reload, and sometimes not even then.
