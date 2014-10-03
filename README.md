mini-dinstall-ng
================

mini-dinstall written from scratch.


Differences to mini-dinstall
----------------------------

* If you want to define architectures in the section DEFAULT
  you have to name the option "arches" and not "architectures"

New Options

| Option             | Description                             |
| ------------------ | --------------------------------------- |
| incoming           | Directory to listen for incoming files. |
| directory          | The subdir. for mini-dinstall files.    |
| socket_name        | Name of the FIFO (named pipe) file.     |
| socket_permission  | Permissions of the unix socket.         |
