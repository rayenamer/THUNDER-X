
notes

edge case failute

The XPath was right: it matched exactly the element Laya picked. That element just can't be hovered, because it has no visible box on the page. browser-use's hover() scrolls to the element, asks for its box, gets none, and stops with "Element is not visible or has no bounding box".


One limit: a past session shows each step's latest run. Older runs are in LogsDb (and in GET /logs/sessions/{id}), but there's no way to browse them in the UI yet.

when direct matcher fails -> pipeline fails , incorrect

hover fails -> incorrect , it finds elemnts but if element have no visible box , it fails