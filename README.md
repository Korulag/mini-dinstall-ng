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

| Option              | Description                                                         |
| ------------------- | ------------------------------------------------------------------  |
| archivedir          | The root directory of the repository. The only required argument.   |
| incoming            | Directory to listen for incoming files.                             |
| directory           | The subdir. for mini-dinstall files.                                |
| socket_name         | Name of the socket placed in the `directory`                        |
| socket_permission   | Permissions of the unix socket.                                     |
| log_level           | The default log level for each logger.                              |
| log_name            | You want to rename the logger? You can.                             |
| log_format          | The format of the logger. See the [python docs](https://docs.python.org/3/library/logging.html#logrecord-attributes) for more information. |
| rejectdir           | Folder to put the rejected packages to.                             |
| lockfile            | Even the lockfile can be named or moved to another folder.          |
| subdirectory        | The subdirectory in the `archivedir` to store our process files.    |
| incoming            | The folder where mini-dinstall-ng looks for new packages            |
| incoming_permissions| Permissions granted to the incoming folder and its files.           |
| logfile_name        | Name or/and path of the logfile.                                    |
| use_dnotify         | Enable or disable dnotify on package update by saying `yes` or `no`.|
| configfiles         | _WARNING:_ With this option you disable the default config file.    |
| arches              | The architectures which will be included in the repository.         |
| distributions       | You can add default distributions if you don't want to use sections.|


Differences to mini-dinstall
----------------------------
* More options. See [the options section](#general-options) for more information.
* If you want to define architectures in the section DEFAULT
  you have to name the option "arches" and not "architectures"

