# mini-dinstall-ng

An unofficial mini-dinstall replacement with focus on the following things:

 * Object oriented
 * Clean
 * Stable
 * Extendable

It's not like I dislike the current mini-dinstall but I think it's easier 
to keep control over the code if we keep it clean and understandable.

## Configuration

### General Options

| Option             | Description                                                   |
| ------------------ | ------------------------------------------------------------- | 
| incoming           | Directory to listen for incoming files.                       |
| directory          | The subdir. for mini-dinstall files.                          |
| socket_name        | Name of the socket placed in the `directory`                  |
| socket_permission  | Permissions of the unix socket.                               |



Differences to mini-dinstall
----------------------------
* More options. See [the options section](#general-options) for more information.
* If you want to define architectures in the section DEFAULT
  you have to name the option "arches" and not "architectures"

