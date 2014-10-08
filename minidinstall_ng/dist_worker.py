import threading
import subprocess
import minidinstall_ng.hasher as hasher

class DirHandler(object):
    
    def _run_script(self, changefilename, script, dir=None):
        if not script:
            raise TypeError('Script needed')
        if not os.path.is_file(script) or not os.access(script, os.X_OK):
            raise DinstallException("Script %s doesn't exist" % script)
        script = os.path.expanduser(script)
        cmd = script + ' ' + changefilename
        self.logger.info('Running script \"%s\"' % cmd)
        if not no_act:
            pid = os.fork()
            if pid == 0:
                if not dir is None:
                    os.chdir(dir)
                os.execlp(script, script, changefilename)
                sys.exit(1)
            (pid, status) = os.waitpid(pid, 0)
            if not (status is None or (os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0)):
                self.logger.error("script \"%s\" exited with error code %d" % (cmd, os.WEXITSTATUS(status)))
                return True
        return False

class ArchiveDirIndexer(DirHandler, threading.Thread):
    '''
    Basically calls apt-ftparchive on the distribution directory to create
    the "Packages" and "Sources" files.
    '''

    hashes = [ 'md5', 'sha1', 'sha256' ]

    def __init__(self, dir, logger, config, use_dnotify=0, batch_mode=1):
        self.name = os.path.basename(os.path.abspath(dir))
        threading.Thread.__init__(self, name=self.name)
        self.directory = dir
        self.logger = logger
        self._eventqueue = Queue.Queue()
        do_mkdir(dir)
        self.use_dnotify = use_dnotify
        self.batch_mode = batch_mode
        self.wait = self.join

    def _abspath(self, *args):
        return os.path.abspath(os.path.join(self.directory, *args))

    def _relpath(self, *args):
        return os.path.join(self.name, *args)

    def _make_indexfile(self, directory, typ, name):
        # if nodb_mode:
        cmdline = ['apt-ftparchive', typ, directory]
        # else:
        #     cmdline = ['apt-ftparchive', typ, directory, '--db', '%s.db' %directory]

        self.logger.debug("Running: " + string.join(cmdline, ' '))
        if no_act:
            return
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
        packagesfilename = os.path.join(directory, name)        
        
        files = []
        for ext, ftype in (('','.gz','.bz2'),(open, gzip.GzipFile, bz2.BZ2File)):   
            filename = packagesfilename+'.new'
            files.append(filename, ftype(filename, 'w'))
        
        for line in iter(proc.stdout.readline, ''):
            for file_, filename in files:
                file_.write(line)

        out, err = proc.communicate()
        if out != '':
            raise RuntimeError('Printed after reading: %r' % out)
        status = proc.wait()
        map(lambda x: x.close(), files)
        if status != 0:
            raise DinstallException("apt-ftparchive exited with status code %d" % status)

        for file_, filename in files:
            # move from file.new to file
            shutil.move(filename, filename[:-4])

    def _make_packagesfile(self, directory):
        self._make_indexfile(directory, 'packages', 'Packages')

    def _make_sourcesfile(self, directory):
        self._make_indexfile(directory, 'sources', 'Sources')

    def _sign_releasefile(self, name, dir):
        '''
        Uses the configuration "release_signscript". If this script is set
        it executes is from withing the directory.
        '''
        if self.config.release_signscript:
            try:
                self.logger.debug("Running Release signing script: " + self.config.release_signscript)
                if self._run_script(name, self.config.release_signscript, dir=dir):
                    return None
            except:
                self.logger.exception("failure while running Release signing script")
                return None
        return True

    def _write_codename(filename):
        suite = self.config.release_suite
            if not suite:
                suite = self.name
            f.write('Suite: ' + suite + '\n')
            codename = self.config.release_codename
            if not codename:
                codename = suite
            f.write('Codename: ' + '%s/%s\n' % (codename, arch))
    
    def _write_releasefile(filename):
        '''
        Writes the release file to filename.
        '''
        with open(filename, 'w') as f:
            f.write('Origin: ' + self.config.release_origin + '\n')
            f.write('Label: ' + self.config.release_label + '\n')
            suite = self.config.release_suite
            if not suite:
                suite = self.name
            f.write('Suite: ' + suite + '\n')
            codename = self.config.release_codename
            if not codename:
                codename = suite
            f.write('Codename: ' + '%s/%s\n' % (codename, arch))
            if self._experimental_release:
                f.write('NotAutomatic: yes\n')
            f.write('Date: ' + time.strftime("%a, %d %b %Y %H:%M:%S UTC", time.gmtime()) + '\n')
            f.write('Architectures: ' + arch + '\n')
            if self._release_description:
                f.write('Description: ' + self._release_description + '\n')
            self._hash_files_to(indexfiles, f)


    def _hash_files_to(self, indexfiles, f):
        '''
        write hash digest into filehandle
        :param indexfiles: system architectures
        :param f: file handle
        '''        
        for hash_ in self.hashes:
            f.write("%s%s:\n" % (hash_.upper() + ('Sum' if hash_ == 'md5' else '')))
            for filename in indexfiles:
                filename = self._abspath(filename)
                hexhash = hasher.hash_file(filename, hash_)
                size = os.stat(filename).st_size
                filename = os.path.basename(filename)
                f.write(' %s% 16d %s\n' % (hexhash, size, filename))             
    
    def _index_all(self, force=False):
        self._index(self.config.arches + ['source'], force=force)

    def _gen_release_all(self, force=False):
        self._gen_release(self.config.arches, force)

    def run(self):
        self.logger.info('Created new thread (%s) for archive indexer %s' % (self.getName(), self.name,))
        self.logger.info('Entering batch mode...')
        try:
            self._index_all(force=True)
            self._gen_release_all(force=True)
            if not self.batch_mode:
                # never returns
                self._daemonize()
        except Exception as e:
            self.logger.exception("Unhandled exception; shutting down")
            self.die_event.set()
        self.logger.info('Thread \"%s\" exiting' % (self.getName(),))

    def _daemon_event_ispending(self):
        return self.die_event.isSet() or (not self._eventqueue.empty())
    
    def _daemonize(self):
        self.logger.info('Entering daemon mode...')
        if self._dynamic_reindex:
            self._dnotify = DirectoryNotifierFactory().create(self._get_dnotify_dirs(), use_dnotify=self.use_dnotify, poll_time=self._poll_time, cancel_event=die_event)

            self._async_dnotify = DirectoryNotifierAsyncWrapper(self._dnotify, self._eventqueue, self.logger=self.logger, name=self.name + " Indexer")
            self._async_dnotify.start()

        # The main daemon loop
        while 1:

            # Wait until we have a pending event
            while not self._daemon_event_ispending():
                time.sleep(1)

            if die_event.isSet():
                break

            self.logger.debug('Reading from event queue')
            setevent = None
            dir = None
            obj = self._eventqueue.get()
            if type(obj) == str:
                self.logger.debug('got dir change')
                dir = obj
            elif obj is None:
                self.logger.debug('got general event')
                setevent = None
            elif type(obj) == threading._Event:
                self.logger.debug('got wait_reprocess event')
                setevent = obj
            else:
                self.logger.error("unknown object %s in event queue" % obj)
                assert None

            # This is to protect against both lots of activity, and to
            # prevent race conditions, so we can rely on timestamps.
            time.sleep(1)
            if not self._reindex_needed():
                if not setevent is None:
                    self.logger.debug('setting wait_reprocess event')
                    setevent.set()
                continue
            if dir is None:
                self.logger.debug('Got general change')
                self._index_all(force=True)
                self._gen_release_all(True)
            else:
                self.logger.debug('Got change in %s' % dir)
                self._index([os.path.basename(os.path.abspath(dir))])
                self._gen_release([os.path.basename(os.path.abspath(dir))])
            if setevent:
                self.logger.debug('setting wait_reprocess event')
                setevent.set()

    def _reindex_needed(self):
        reindex_needed = False
        if os.access(self._abspath('Release.gpg'), os.R_OK):
            gpg_mtime = os.stat(self._abspath('Release.gpg'))[stat.ST_MTIME]
            for dir in self._get_dnotify_dirs():
                dir_mtime = os.stat(self._abspath(dir))[stat.ST_MTIME]
                if dir_mtime > gpg_mtime:
                    reindex_needed = True
        else:
            reindex_needed = True
        return reindex_needed

    def _index(self, arches, force=None):
        self._index_impl(arches, force=force)

    def _gen_release(self, arches, force=False):
        self._gen_release_impl(self.config.arches, force)

    def wait_reprocess(self):
        e = threading.Event()
        self._eventqueue.put(e)
        self.logger.debug('waiting on reprocess')
        while not (e.isSet() or die_event.isSet()):
            time.sleep(0.5)
        self.logger.debug('done waiting on reprocess')

    def notify(self):
        self._eventqueue.put(None)

class ArchiveDir(DirHandler):

    indexer_class = ArchiveDirIndexer

    def __init__(self, dir, logger, config, batch_mode=0):
        self.directory = dir
        self.name = os.path.basename(os.path.abspath(dir))
        self.logger = logger
        for key in config.keys():
            self.logger.debug("Setting \"%s\" => \"%s\" in archive \"%s\"" % ('_'+key, config[key], self.name))
            self.__dict__['_' + key] = config[key]
        do_mkdir(dir)
        self.batch_mode = batch_mode
        # if self.config.mail_on_success:
        #     self._successlogger = logging.self.logger("mini-dinstall." + self.name)
        #     self._successlogger.setLevel(logging.DEBUG)
        #     mailHandler = SubjectSpecifyingLoggingSMTPHandler(mail_server, 'Mini-Dinstall <%s@%s>' % (getpass.getuser(), socket.getfqdn()), [mail_to])
        #     mailHandler.setLevel(logging.DEBUG)
        #     self._successlogger.addHandler(mailHandler)
        self._clean_targets = []

    def _abspath(self, *args):
        return os.path.abspath(self.directory, *args)

    def _relpath(self, *args):
        return os.path.join(self.name, *args)

    def install(self, changefilename, changefile):
        success = False
        try:
            success = self._install_run_scripts(changefilename, changefile)
        except Exception:
            self.logger.exception("Unhandled exception during installation")
        if not success:
            self.logger.info('Failed to install "%s"' % changefilename)

    def reject(self, changefilename, changefile, reason):
        self._reject_changefile(changefilename, changefile, reason)

    def _install_run_scripts(self, changefilename, changefile):
        self.logger.info('Preparing to install \"%s\" in archive %s' % (changefilename, self.name,))
        sourcename = changefile['source']
        version = changefile['version']
        if self.config.verify_sigs:
            self.logger.info('Verifying signature on "%s"' % changefilename)
            try:
                if self.config.keyrings:
                    verifier = DebianSigVerifier(keyrings=self.config.keyrings)
                else:
                    verifier = DebianSigVerifier(extra_keyrings=self.config.extra_keyrings)
                output = verifier.verify(changefilename)
                self.logger.debug(output)
                self.logger.info('Good signature on "%s"' % changefilename)
            except GPGSigVerificationFailure as e:
                msg = "Failed to verify signature on \"%s\": %s\n" % (changefilename, e)
                msg += string.join(e.getOutput(), '')
                self.logger.error(msg)
                self._reject_changefile(changefilename, changefile, e)
                return False
        else:
            self.logger.debug('Skipping signature verification on "%s"' % changefilename)
        if self.config.pre_install_script:
            try:
                self.logger.debug("Running pre-installation script: " + self.config.pre_install_script)
                if self._run_script(os.path.abspath(changefilename), self.config.pre_install_script):
                    return False
            except:
                self.logger.exception("failure while running pre-installation script")
                return False
        try:
            self._install_changefile_internal(changefilename, changefile)
        except Exception as e:
            self.logger.exception('Failed to process "%s"' % changefilename)
            self._reject_changefile(changefilename, changefile, e)
            return False
        if self._chown_changes_files:
            do_chmod(changefilename, 0600)
        target = os.path.join(self.directory, os.path.basename(changefilename))
        # the final step
        do_rename(changefilename, target)
        self.logger.info('Successfully installed %s %s to %s' % (sourcename, version, self.name))
        if self._mail_on_success:
            done = False
            missing_fields = []
            if changefile.has_key('changes'):
                changefile ['changes_without_dot'] = misc.format_changes(changefile['changes'])
            while not done:
                try:
                    mail_subject = mail_subject_template % changefile
                    mail_body = mail_body_template % changefile
                except KeyError as exc:
                    key = exc.args[0]
                    changefile[key] = ''
                    missing_fields.append(key)
                else:
                    done = True
            if missing_fields:
                mail_body = mail_body + "\n\nMissing changefile fields: %s" % missing_fields
            minidinstall.mail.send(mail_server, 'Mini-Dinstall <%s@%s>' % (getpass.getuser(),socket.getfqdn()), mail_to, mail_body, mail_subject)

        if self.config.tweet_on_success:
            done = False
            missing_fields = []
            if changefile.has_key('changes'):
                changefile ['changes_without_dot'] = misc.format_changes(changefile['changes'])
            while not done:
                try:
                    tweet_body = tweet_template % changefile
                except KeyError as exc:
                    key = exc.args[0]
                    changefile[key] = ''
                    missing_fields.append(key)
                else:
                    done = True
            if missing_fields:
                tweet_body = tweet_body + "\n\n(errs: %s)" % missing_fields
            minidinstall.tweet.send(tweet_body, tweet_server, tweet_user, tweet_password)

        if self.config.post_install_script:
            try:
                self.logger.debug("Running post-installation script: " + self.config.post_install_script)
                self._run_script(target, self.config.post_install_script)
            except:
                self.logger.exception("failure while running post-installation script")
                return False
        return True

    def _install_changefile_internal(self, changefilename, changefile):
        sourcename = changefile['source']
        version = changefile['version']
        incomingdir = os.path.dirname(changefilename)
        newfiles = []
        is_native = not native_version_re.match(version)
        if is_native:
            (ignored, newdebianver) = parse_versions(version)
        else:
            (newupstreamver, newdebianver) = parse_versions(version)
        is_sourceful = 0
        for file in map(lambda x: x[2], changefile.getFiles()):
            match = debpackage_re.search(file)
            if match:
                arch = match.group(3)
                if not arch in self.config.arches:
                    raise DinstallException("Unknown architecture: %s" % (arch))
                target = self._arch_target(arch, file)
                newfiles.append((os.path.join(incomingdir, file), target, match.group(1), arch))
                continue
            match = debsrc_diff_re.search(file)
            if match:
                is_sourceful = 1
                target = self._source_target(file)
                newfiles.append((os.path.join(incomingdir, file), target, match.group(1), 'source'))
                continue
            match = debsrc_orig_re.search(file)
            if match:
                is_sourceful = 1
                target = self._source_target(file)
                newfiles.append((os.path.join(incomingdir, file), target, match.group(1), 'source'))
                continue
            match = debsrc_native_re.search(file)
            if match:
                is_sourceful = 1
                target = self._source_target(file)
                newfiles.append((os.path.join(incomingdir, file), target, match.group(1), 'source'))
                continue
            match = debsrc_dsc_re.search(file) or debsrc_orig_re.search(file)
            if match:
                is_sourceful = 1
                target = self._source_target(file)
                newfiles.append((os.path.join(incomingdir, file), target, match.group(1), 'source'))
                continue

        all_arches = {}
        for arch in map(lambda x: x[3], newfiles):
            all_arches[arch] = 1
        completed = []
        oldfiles = []
        if not self._keep_old:
            found_old_bins = 0
            for (oldversion, oldarch) in map(lambda x: x[1:], self._get_package_versions()):
                if not all_arches.has_key(oldarch) and apt_pkg.version_compare(oldversion, version) < 0:
                    found_old_bins = 1
            for (pkgname, arch) in map(lambda x: x[2:], newfiles):
                if arch == 'source' and found_old_bins:
                    continue
                self.logger.debug('Scanning for old files')
                for file in self._read_arch_dir(arch):
                    match = debpackage_re.search(file)
                    if not match:
                        continue
                    oldpkgname = match.group(1)
                    oldarch = match.group(3)
                    file = self._arch_target(arch, file)
                    if not file in map(lambda x: x[0], oldfiles):
                        target = file + tmp_old_suffix
                        if oldpkgname == pkgname and oldarch == arch:
                            oldfiles.append((file, target))
            self.logger.debug('Scanning "%s" for old files' % (self._abspath('source')))
            for file in self._read_source_dir():
                file = self._source_target(file)
                if not file in map(lambda x: x[0], oldfiles):
                    target = file + tmp_old_suffix
                    match = debchanges_re.search(file)
                    if not match and is_sourceful:
                        match = debsrc_dsc_re.search(file) or debsrc_diff_re.search(file)
                    if match and match.group(1) == sourcename:
                        oldfiles.append((file, target))
                        continue
                    # We skip the rest of this if it wasn't a
                    # sourceful upload; really all we do if it isn't
                    # is clean out old .changes files.
                    if not is_sourceful:
                        continue
                    match = debsrc_orig_re.search(file)
                    if match and match.group(1) == sourcename:
                        if not is_native:
                            (oldupstreamver, olddebianver) = parse_versions(match.group(2))
                            if apt_pkg.version_compare(oldupstreamver, newupstreamver) < 0:
                                self.logger.debug('old upstream tarball "%s" version %s < %s, tagging for deletion' % (file, oldupstreamver, newupstreamver))
                                oldfiles.append((file, target))
                                continue
                            else:
                                self.logger.debug('keeping upstream tarball "%s" version %s' % (file, oldupstreamver))
                                continue
                        else:
                            self.logger.debug('old native tarball "%s", tagging for deletion'  % file)
                            oldfiles.append((file, target))
                            continue
                    match = debsrc_native_re.search(file)
                    if match and match.group(1) in map(lambda x: x[2], newfiles):
                        oldfiles.append((file, target))
                        continue

        self._clean_targets = [x[1] for x in oldfiles]
        allrenames = oldfiles + [x[:2] for x in newfiles]
        try:
            while not allrenames == []:
                (oldname, newname) = allrenames[0]
                do_rename(oldname, newname)
                completed.append(allrenames[0])
                allrenames = allrenames[1:]
        except OSError, e:
            self.logger.exception("Failed to do rename (%s); attempting rollback" % (e.strerror,))
            try:
                self.logger.error(traceback.format_tb(sys.exc_traceback))
            except:
                pass
            # Unwind to previous state
            for (newname, oldname) in completed:
                do_rename(oldname, newname)
            raise
            self._clean_targets = []
        # remove old files
        self.clean()

    def _reject_changefile(self, changefilename, changefile, exception):
        sourcename = changefile['source']
        version = changefile['version']
        incomingdir = os.path.dirname(changefilename)
        try:
            f = open(os.path.join(rejectdir, "%s_%s.reason" % (sourcename, version)), 'w')
            if type(exception) is str:
                f.write(exception)
            else:
                traceback.print_exception(Exception, exception, None, None, f)
            f.close()
            for file in map(lambda x: x[2], changefile.getFiles()):
                if os.access(os.path.join(incomingdir, file), os.R_OK):
                    file = os.path.join(incomingdir, file)
                else:
                    file = self._abspath(file)
                target = os.path.join(rejectdir, os.path.basename(file))
                do_rename(file, target)
            do_rename(changefilename, os.path.join(rejectdir, os.path.basename(changefilename)))
            self.logger.info('Rejecting "%s": %s' % (changefilename, `exception`))
        except Exception:
            self.logger.error("Unhandled exception while rejecting %s; archive may be in inconsistent state" % changefilename)
            raise

    def clean(self):
        self.logger.debug('Removing old files')
        for file in self._clean_targets:
            self.logger.debug('Deleting "%s"' % file)
                os.unlink(file)
